"""Load, validate, and expose settings from the project's config.ini file."""

import logging
from configparser import ConfigParser, Error as ConfigError
from pathlib import Path

from logging_config import configure_logging
from validation import (
    validate_http_url,
    validate_positive_integer,
    validate_rating,
)


configure_logging()
logger = logging.getLogger(__name__)

# Resolve configuration relative to this module so launch-directory changes
# do not silently select a different settings file.
CONFIG_PATH = Path(__file__).with_name("config.ini")
_config = ConfigParser()

logger.info(
    "Loading application configuration",
    extra={"event": "configuration_load"},
)
try:
    loaded_files = _config.read(CONFIG_PATH, encoding="utf-8")
except ConfigError as error:
    logger.exception(
        "Could not read application configuration",
        extra={"event": "configuration_load", "error": str(error)},
    )
    raise ValueError(f"Could not read configuration file {CONFIG_PATH}: {error}") from error

if not loaded_files:
    logger.error(
        "Configuration file was not found",
        extra={"event": "configuration_load", "error": str(CONFIG_PATH)},
    )
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

try:
    TVMAZE_SEARCH_URL = _config.get("api", "search_url")
    TVMAZE_SHOWS_URL = _config.get("api", "shows_url")
    REQUEST_TIMEOUT_SECONDS = _config.getint("api", "timeout_seconds")
    # Keep genre choices configurable without requiring a separate API call.
    TVMAZE_GENRES = tuple(
        genre.strip()
        for genre in _config.get("api", "genres").split(",")
        if genre.strip()
    )
    MINIMUM_RATING = _config.getfloat("search", "minimum_rating")
    WINDOW_TITLE = _config.get("gui", "title")
    WINDOW_MIN_WIDTH = _config.getint("gui", "min_width")
    WINDOW_MIN_HEIGHT = _config.getint("gui", "min_height")
except (ConfigError, ValueError) as error:
    logger.exception(
        "Invalid application configuration",
        extra={"event": "configuration_load", "error": str(error)},
    )
    raise ValueError(f"Invalid configuration in {CONFIG_PATH}: {error}") from error

# Validate settings once at import so both GUI and CLI fail early and clearly.
try:
    TVMAZE_SEARCH_URL = validate_http_url(TVMAZE_SEARCH_URL, "TVMaze search URL")
    TVMAZE_SHOWS_URL = validate_http_url(TVMAZE_SHOWS_URL, "TVMaze show-index URL")
    validate_rating(MINIMUM_RATING)
    validate_positive_integer(REQUEST_TIMEOUT_SECONDS, "Request timeout")
    validate_positive_integer(WINDOW_MIN_WIDTH, "Minimum window width")
    validate_positive_integer(WINDOW_MIN_HEIGHT, "Minimum window height")
    normalized_genres = {genre.casefold() for genre in TVMAZE_GENRES}
    if not TVMAZE_GENRES or len(normalized_genres) != len(TVMAZE_GENRES):
        raise ValueError("TVMaze genres must be a non-empty list of unique values.")
except ValueError as error:
    logger.error(
        "Configuration validation failed",
        extra={"event": "configuration_validation", "error": str(error)},
    )
    raise ValueError(f"Invalid setting in {CONFIG_PATH}: {error}") from error

logger.info(
    "Application configuration loaded",
    extra={"event": "configuration_loaded"},
)
