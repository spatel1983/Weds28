from configparser import ConfigParser, Error as ConfigError
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("config.ini")
_config = ConfigParser()

try:
    loaded_files = _config.read(CONFIG_PATH, encoding="utf-8")
except ConfigError as error:
    raise ValueError(f"Could not read configuration file {CONFIG_PATH}: {error}") from error

if not loaded_files:
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

try:
    TVMAZE_SEARCH_URL = _config.get("api", "search_url")
    REQUEST_TIMEOUT_SECONDS = _config.getint("api", "timeout_seconds")
    WINDOW_TITLE = _config.get("gui", "title")
    WINDOW_MIN_WIDTH = _config.getint("gui", "min_width")
    WINDOW_MIN_HEIGHT = _config.getint("gui", "min_height")
except (ConfigError, ValueError) as error:
    raise ValueError(f"Invalid configuration in {CONFIG_PATH}: {error}") from error

if not TVMAZE_SEARCH_URL.strip():
    raise ValueError(f"The API search URL is empty in {CONFIG_PATH}")
if REQUEST_TIMEOUT_SECONDS <= 0 or WINDOW_MIN_WIDTH <= 0 or WINDOW_MIN_HEIGHT <= 0:
    raise ValueError(f"Timeout and window dimensions must be positive in {CONFIG_PATH}")
