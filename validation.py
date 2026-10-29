"""Reusable validation functions for user input and app configuration."""

import logging
import math
from urllib.parse import urlsplit


logger = logging.getLogger(__name__)


def validate_search_title(title):
    """Trim and require a non-empty TV show search title."""
    if not isinstance(title, str):
        message = "Search title must be text."
        logger.warning(
            "Search title validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)

    title = title.strip()
    if not title:
        message = "Please enter a TV show title."
        logger.warning(
            "Search title validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return title


def validate_search_mode(mode):
    """Require one of the application's supported search modes."""
    if mode not in ("title", "rating", "genre"):
        message = "Choose title, minimum-rating, or genre search."
        logger.warning(
            "Search mode validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return mode


def validate_genre(genre, valid_genres):
    """Return the canonical genre spelling if it is in the allowed choices."""
    if not isinstance(genre, str):
        message = "Choose a genre from the list."
        logger.warning(
            "Genre validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)

    genre = genre.strip()
    matched_genre = next(
        (option for option in valid_genres if option.casefold() == genre.casefold()),
        None,
    )
    if matched_genre is None:
        message = "Choose a genre from the list."
        logger.warning(
            "Genre validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return matched_genre


def validate_positive_integer(value, setting_name):
    """Require a strictly positive integer for timeouts and dimensions."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        message = f"{setting_name} must be a positive whole number."
        logger.warning(
            "Integer validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return value


def validate_http_url(value, setting_name):
    """Require an absolute HTTP or HTTPS URL and return its trimmed value."""
    if not isinstance(value, str):
        message = f"{setting_name} must be a valid HTTP or HTTPS URL."
        logger.warning(
            "URL validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)

    parsed = urlsplit(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        message = f"{setting_name} must be a valid HTTP or HTTPS URL."
        logger.warning(
            "URL validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return value.strip()


def validate_rating(value, setting_name="Minimum rating"):
    """Require a finite, non-boolean number in the inclusive 0-10 range."""
    if (
        # bool is an int subclass, but True/False should not pass rating checks.
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 10
    ):
        message = f"{setting_name} must be between 0 and 10."
        logger.warning(
            "Rating validation failed",
            extra={"event": "validation_failure", "error": message},
        )
        raise ValueError(message)
    return value
