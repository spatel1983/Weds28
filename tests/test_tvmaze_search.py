"""Unit tests for TVMaze title and paginated index searches."""

import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

import tvmaze_search


class MockResponse(io.BytesIO):
    """Provide the context-manager interface expected from urlopen."""

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.close()


def response_with(payload):
    """Encode a Python payload as a mocked JSON HTTP response."""
    return MockResponse(json.dumps(payload).encode("utf-8"))


def search_result(name, rating, **fields):
    """Build one item in the TVMaze show-search response format."""
    show = {"name": name, "rating": {"average": rating}}
    show.update(fields)
    return {"score": 1, "show": show}


class TitleSearchTests(unittest.TestCase):
    """Cover title query construction, filtering, and API error handling."""

    @patch("tvmaze_search.urlopen")
    def test_search_returns_all_shows_at_or_above_configured_rating(self, urlopen):
        urlopen.return_value = response_with(
            [
                search_result("High", 9.0),
                search_result("Boundary", tvmaze_search.MINIMUM_RATING),
                search_result("Low", 2.0),
                search_result("Unrated", None),
            ]
        )

        shows = tvmaze_search.search_shows("The Office")

        self.assertEqual([show["name"] for show in shows], ["High", "Boundary"])
        self.assertIn("q=The+Office", urlopen.call_args.args[0])

    @patch("tvmaze_search.urlopen")
    def test_search_returns_empty_list_when_there_are_no_results(self, urlopen):
        urlopen.return_value = response_with([])
        self.assertEqual(tvmaze_search.search_shows("Unknown"), [])

    @patch("tvmaze_search.urlopen")
    def test_search_rejects_invalid_api_payload(self, urlopen):
        urlopen.return_value = response_with({"unexpected": []})
        with self.assertRaisesRegex(RuntimeError, "unexpected show-search response"):
            tvmaze_search.search_shows("Example")

    @patch("tvmaze_search.urlopen")
    def test_search_reports_http_errors(self, urlopen):
        urlopen.side_effect = HTTPError(
            "https://api.tvmaze.com/search/shows", 503, "Unavailable", None, None
        )
        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            tvmaze_search.search_shows("Example")

    @patch("tvmaze_search.urlopen")
    def test_search_rejects_blank_title_before_request(self, urlopen):
        with self.assertRaises(ValueError):
            tvmaze_search.search_shows(" ")
        urlopen.assert_not_called()

    @patch("tvmaze_search.search_shows", return_value=[{"name": "First"}])
    def test_search_show_returns_first_result(self, search_shows):
        self.assertEqual(tvmaze_search.search_show("Example"), {"name": "First"})

    @patch("tvmaze_search.search_shows", return_value=[])
    def test_search_show_returns_none_when_no_result(self, _search_shows):
        self.assertIsNone(tvmaze_search.search_show("Unknown"))


class RatingSearchTests(unittest.TestCase):
    """Cover index pagination, rating/genre filters, and progress callbacks."""

    @patch("tvmaze_search.time.sleep")
    @patch("tvmaze_search.urlopen")
    def test_rating_search_scans_pages_and_reports_progress(
        self, urlopen, sleep
    ):
        page_zero = [
            {"id": 1, "name": "High", "rating": {"average": 9.0}},
            {"id": 2, "name": "Low", "rating": {"average": 4.0}},
        ]
        page_one = [
            {"id": 3, "name": "Boundary", "rating": {"average": 7.5}},
            {"id": 4, "name": "Unrated", "rating": None},
        ]

        def api_request(url, timeout):
            if "page=0" in url:
                return response_with(page_zero)
            if "page=1" in url:
                return response_with(page_one)
            raise HTTPError(url, 404, "Not Found", None, None)

        urlopen.side_effect = api_request
        progress = []

        shows = tvmaze_search.search_shows_by_rating(
            7.5, lambda page, count: progress.append((page, count))
        )

        self.assertEqual([show["name"] for show in shows], ["High", "Boundary"])
        self.assertEqual(progress, [(1, 1), (2, 2)])
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("tvmaze_search.urlopen")
    def test_rating_search_raises_on_first_page_not_found(self, urlopen):
        urlopen.side_effect = HTTPError(
            "https://api.tvmaze.com/shows?page=0", 404, "Not Found", None, None
        )
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            tvmaze_search.search_shows_by_rating(8)

    @patch("tvmaze_search.urlopen")
    def test_rating_search_rejects_invalid_page_data(self, urlopen):
        urlopen.return_value = response_with({"not": "a list"})
        with self.assertRaisesRegex(RuntimeError, "invalid response"):
            tvmaze_search.search_shows_by_rating(8)

    @patch("tvmaze_search.urlopen")
    def test_rating_search_validates_threshold_before_request(self, urlopen):
        with self.assertRaises(ValueError):
            tvmaze_search.search_shows_by_rating(11)
        urlopen.assert_not_called()

    @patch("tvmaze_search.time.sleep")
    @patch("tvmaze_search.urlopen")
    def test_genre_search_filters_genre_and_minimum_rating(self, urlopen, _sleep):
        shows_page = [
            {"id": 1, "name": "Drama hit", "genres": ["Drama"], "rating": {"average": 9}},
            {"id": 2, "name": "Comedy hit", "genres": ["Comedy"], "rating": {"average": 9}},
            {"id": 3, "name": "Low drama", "genres": ["Drama"], "rating": {"average": 2}},
            {"id": 4, "name": "Unrated drama", "genres": ["Drama"], "rating": None},
        ]

        def api_request(url, timeout):
            if "page=0" in url:
                return response_with(shows_page)
            raise HTTPError(url, 404, "Not Found", None, None)

        urlopen.side_effect = api_request
        progress = []

        found = tvmaze_search.search_shows_by_genre(
            "dRaMa", lambda page, count: progress.append((page, count))
        )

        self.assertEqual([show["name"] for show in found], ["Drama hit"])
        self.assertEqual(progress, [(1, 1)])

    @patch("tvmaze_search.urlopen")
    def test_genre_search_rejects_unknown_genre_before_request(self, urlopen):
        with self.assertRaises(ValueError):
            tvmaze_search.search_shows_by_genre("Unknown Genre")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
