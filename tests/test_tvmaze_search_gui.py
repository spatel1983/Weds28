"""Unit tests for formatting TVMaze details in the GUI results box."""

import unittest

from tvmaze_search_gui import format_show, format_shows


class ShowFormattingTests(unittest.TestCase):
    """Ensure show details and one-row-per-result layout remain consistent."""

    def test_formats_show_details_with_network(self):
        show = {
            "name": "Example",
            "rating": {"average": 8.5},
            "network": {"name": "Example Network"},
            "genres": ["Drama", "Mystery"],
            "premiered": "2020-01-01",
            "ended": "2022-01-01",
        }

        formatted = format_show(show)

        for expected in (
            "Example",
            "8.5",
            "Example Network",
            "Drama, Mystery",
            "2020-01-01",
            "2022-01-01",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, formatted)

    def test_formats_streaming_service_and_missing_fields(self):
        formatted = format_show(
            {"name": "Web Show", "webChannel": {"name": "Stream"}, "genres": []}
        )

        self.assertIn("Network/streaming service: Stream", formatted)
        self.assertIn("Rating: Not listed", formatted)
        self.assertIn("Genres: Not listed", formatted)
        self.assertIn("End date: Not listed", formatted)

    def test_formats_every_show_as_one_row(self):
        shows = [
            {"name": "First", "rating": {"average": 8}},
            {"name": "Second", "rating": {"average": 7}},
        ]

        rows = format_shows(shows).splitlines()

        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].startswith("1. First | "))
        self.assertTrue(rows[1].startswith("2. Second | "))
        self.assertIn("Rating: 8", rows[0])
        self.assertIn("Rating: 7", rows[1])


if __name__ == "__main__":
    unittest.main()
