"""Configure JSON-formatted application logging to the project log file."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = Path(__file__).with_name("logs") / "application.log"


class JsonFormatter(logging.Formatter):
    """Serialize standard log fields and selected structured event fields."""

    def format(self, record):
        """Return one JSON object per log record."""
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "event",
            "query",
            "url",
            "page",
            "match_count",
            "status_code",
            "error",
        ):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging():
    """Install one UTF-8 file handler without duplicating it on reconfiguration."""
    root_logger = logging.getLogger()
    if any(
        getattr(handler, "_application_handler", False)
        for handler in root_logger.handlers
    ):
        return

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler._application_handler = True
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
