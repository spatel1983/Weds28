# Project Handover

## Overview

This is a Python 3 TV-show search application using TVMaze's public API. It
provides a Tkinter GUI and an interactive command-line interface. No API key
or third-party Python packages are needed; internet access is required.

Search options:

- **Title:** Uses TVmaze's show-search endpoint and returns all results meeting
  the configured minimum rating.
- **Minimum rating:** Scans the paginated show index and returns rated shows
  at or above the user-selected threshold.
- **Genre:** Scans the same index and returns shows in the selected configured
  genre that also meet the minimum rating in `config.ini`.

Rating and genre searches scan the full index. Requests are paced to respect
TVmaze's rate limit, and the GUI displays scan progress. These searches can
take a while.

## Run the application

From the project directory:

```powershell
python tvmaze_search_gui.py
```

For the command-line interface:

```powershell
python tvmaze_search.py
```

`movie_search_gui.py` and `movie_search.py` are compatibility launchers for the
TVmaze GUI and CLI, respectively.

## Configuration

`config.ini` is loaded from the project directory beside `app_config.py`.

- `[api] search_url` is used for title searches.
- `[api] shows_url` is the paginated show index used for rating and genre
  searches.
- `[api] timeout_seconds` sets the HTTP timeout.
- `[api] genres` provides the GUI dropdown choices and accepted genre values.
- `[search] minimum_rating` filters title and genre results; it must be from
  0 through 10.
- `[gui]` configures the window title and minimum size.

The configured search endpoints must be HTTP or HTTPS URLs. Timeout and window
dimensions must be positive integers. Settings are validated at startup.

## Code map

| File | Responsibility |
| --- | --- |
| `tvmaze_search.py` | TVmaze HTTP requests, title/rating/genre filtering, CLI |
| `tvmaze_search_gui.py` | Tkinter interface, asynchronous search, result formatting and scrolling |
| `app_config.py` | Loads and validates `config.ini` |
| `validation.py` | Reusable input and configuration validation |
| `logging_config.py` | JSON logging setup and formatting |
| `config.ini` | API endpoints, genres, rating threshold, GUI settings |
| `movie_search.py` | Compatibility launcher for the TVmaze CLI |
| `movie_search_gui.py` | Compatibility launcher for the TVmaze GUI |
| `tests/` | Unit tests for search, validation, and GUI formatting |

The GUI runs network requests in a worker thread. Worker results and progress
are sent through a queue so Tk widgets are updated only by the GUI event loop.
The results text box displays each show and its details on one row, with
vertical and horizontal scrollbars and mouse-wheel support.

## Logging and tests

Structured JSON log events are written to `logs/application.log`. The `logs`
directory is created on startup, and the generated log file is git-ignored.

Run the unit tests with:

```powershell
python -m unittest discover -s tests -v
```

The tests mock HTTP calls and do not require network access.

## Operational notes

- TVmaze uses HTTP 404 from the show-index endpoint to indicate the final page.
- If TVmaze changes that pagination behavior or rate limits, update
  `_scan_show_index` in `tvmaze_search.py` and its pagination tests.
- Genre choices are maintained in `config.ini`; genre matching is
  case-insensitive.
- Search results without a numeric rating are excluded from rating and genre
  searches.
