"""Unit tests for reusable search input and configuration validation."""

import unittest

from validation import (
    validate_http_url,
    validate_genre,
    validate_positive_integer,
    validate_rating,
    validate_search_mode,
    validate_search_title,
)


class ValidationTests(unittest.TestCase):
    """Check accepted values and representative invalid inputs."""

    def test_search_title_is_trimmed(self):
        self.assertEqual(validate_search_title("  The Office  "), "The Office")

    def test_search_title_rejects_empty_or_non_text(self):
        for value in ("", "  ", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_search_title(value)

    def test_search_mode_accepts_title_and_rating(self):
        self.assertEqual(validate_search_mode("title"), "title")
        self.assertEqual(validate_search_mode("rating"), "rating")
        self.assertEqual(validate_search_mode("genre"), "genre")

    def test_search_mode_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            validate_search_mode("network")

    def test_genre_validation_is_case_insensitive(self):
        genres = ("Comedy", "Drama")
        self.assertEqual(validate_genre("comedy", genres), "Comedy")
        with self.assertRaises(ValueError):
            validate_genre("Unknown", genres)

    def test_rating_accepts_inclusive_zero_to_ten(self):
        for value in (0, 5.5, 10):
            with self.subTest(value=value):
                self.assertEqual(validate_rating(value), value)

    def test_rating_rejects_invalid_values(self):
        for value in (-0.1, 10.1, float("nan"), float("inf"), True, "8"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rating(value)

    def test_positive_integer_validation(self):
        self.assertEqual(validate_positive_integer(10, "Timeout"), 10)
        for value in (0, -1, 1.5, True, "5"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_positive_integer(value, "Timeout")

    def test_http_url_validation(self):
        self.assertEqual(
            validate_http_url(" https://api.tvmaze.com/shows ", "Endpoint"),
            "https://api.tvmaze.com/shows",
        )
        for value in ("", "ftp://example.com", "https://", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_http_url(value, "Endpoint")


if __name__ == "__main__":
    unittest.main()
