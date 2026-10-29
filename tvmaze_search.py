"""TVMaze API searches, result filtering, and command-line interface."""

import json
import logging
import math
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from app_config import (
    MINIMUM_RATING,
    REQUEST_TIMEOUT_SECONDS,
    TVMAZE_GENRES,
    TVMAZE_SEARCH_URL,
    TVMAZE_SHOWS_URL,
)
from validation import (
    validate_genre,
    validate_rating,
    validate_search_mode,
    validate_search_title,
)


logger = logging.getLogger(__name__)


def _show_rating(show):
    """Return a finite numeric rating, or None when the API omitted it."""
    rating_info = show.get("rating")
    if not isinstance(rating_info, dict):
        return None
    rating = rating_info.get("average")
    if (
        # bool is an int subclass, but it is not a valid show rating.
        isinstance(rating, bool)
        or not isinstance(rating, (int, float))
        or not math.isfinite(rating)
    ):
        return None
    return rating


def _show_has_genre(show, genre):
    """Check a show's genre list without case-sensitive mismatches."""
    genres = show.get("genres")
    if not isinstance(genres, list):
        return False
    return any(
        isinstance(item, str) and item.casefold() == genre.casefold()
        for item in genres
    )


def search_shows(title):
    """Search TVMaze by title and retain results meeting the configured rating."""
    title = validate_search_title(title)
    logger.info(
        "TV show search requested",
        extra={"event": "user_search", "query": title},
    )
    query = urlencode({"q": title})
    logger.debug(
        "Sending TVMaze API request",
        extra={"event": "api_request", "url": TVMAZE_SEARCH_URL},
    )

    try:
        with urlopen(
            f"{TVMAZE_SEARCH_URL}?{query}",
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            results = json.load(response)
    except HTTPError as error:
        logger.error(
            "TVMaze API returned an HTTP error",
            extra={
                "event": "api_error",
                "url": TVMAZE_SEARCH_URL,
                "status_code": error.code,
                "error": str(error.reason),
            },
        )
        raise RuntimeError(
            f"TVMaze returned HTTP {error.code} ({error.reason})."
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        logger.error(
            "TVMaze API request failed",
            extra={
                "event": "api_error",
                "url": TVMAZE_SEARCH_URL,
                "error": type(error).__name__,
            },
        )
        raise RuntimeError(f"Could not retrieve show information: {error}") from error

    if not isinstance(results, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("show"), dict)
        for item in results
    ):
        logger.error(
            "TVMaze returned an unexpected search response",
            extra={"event": "api_error"},
        )
        raise RuntimeError("TVMaze returned an unexpected show-search response.")

    matching_shows = []
    below_minimum_rating = None
    for result in results:
        show = result["show"]
        rating = _show_rating(show)
        if rating is not None and rating >= MINIMUM_RATING:
            matching_shows.append(show)
        if rating is not None and below_minimum_rating is None:
            below_minimum_rating = rating

    if not matching_shows and below_minimum_rating is not None:
        logger.warning(
            "Matching TV shows did not meet the minimum rating",
            extra={
                "event": "rating_below_minimum",
                "query": title,
                "error": f"rating={below_minimum_rating:g}, minimum={MINIMUM_RATING:g}",
            },
        )
        raise RuntimeError(
            f"Show rating {below_minimum_rating:g} is below the minimum "
            f"rating of {MINIMUM_RATING:g}."
        )
    return matching_shows


def search_show(title):
    """Return the first qualifying show for callers that need a single result."""
    shows = search_shows(title)
    return shows[0] if shows else None


def _scan_show_index(matches_show, search_description, progress_callback=None):
    """Apply a predicate to every paginated TVMaze show with rate-limit pacing."""
    logger.info(
        "TVMaze show-index search requested",
        extra={"event": "index_search", "query": search_description},
    )
    matches = []
    page = 0
    while True:
        if page:
            # TVMaze rate-limits API calls, so pace requests when scanning pages.
            time.sleep(0.55)
        logger.debug(
            "Sending TVMaze show-index API request",
            extra={"event": "api_request", "url": TVMAZE_SHOWS_URL, "page": page},
        )
        try:
            with urlopen(
                f"{TVMAZE_SHOWS_URL}?{urlencode({'page': page})}",
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                shows = json.load(response)
        except HTTPError as error:
            # The show index signals its final page with a 404 response.
            if error.code == 404 and page > 0:
                logger.info(
                    "Reached the end of the TVMaze show index",
                    extra={
                        "event": "rating_search_complete",
                        "page": page,
                        "match_count": len(matches),
                    },
                )
                break
            logger.error(
                "TVMaze show-index API returned an HTTP error",
                extra={
                    "event": "api_error",
                    "url": TVMAZE_SHOWS_URL,
                    "page": page,
                    "status_code": error.code,
                    "error": str(error.reason),
                },
            )
            raise RuntimeError(
                f"TVMaze returned HTTP {error.code} ({error.reason}) "
                f"while reading page {page}."
            ) from error
        except (OSError, json.JSONDecodeError) as error:
            logger.error(
                "TVMaze show-index request failed",
                extra={
                    "event": "api_error",
                    "url": TVMAZE_SHOWS_URL,
                    "page": page,
                    "error": type(error).__name__,
                },
            )
            raise RuntimeError(
                f"Could not retrieve TVMaze show page {page}: {error}"
            ) from error

        if not isinstance(shows, list) or any(
            not isinstance(show, dict) for show in shows
        ):
            logger.error(
                "TVMaze returned an invalid show-index page",
                extra={"event": "api_error", "page": page},
            )
            raise RuntimeError(
                f"TVMaze returned an invalid response for show page {page}."
            )

        for show in shows:
            if matches_show(show):
                matches.append(show)

        if progress_callback:
            progress_callback(page + 1, len(matches))
        page += 1

    return matches


def search_shows_by_rating(minimum_rating, progress_callback=None):
    """Return indexed shows with a valid rating at or above the threshold."""
    minimum_rating = validate_rating(minimum_rating, "Search rating")
    logger.info(
        "TVMaze rating search requested",
        extra={"event": "rating_search", "query": f">={minimum_rating:g}"},
    )
    return _scan_show_index(
        lambda show: (
            (rating := _show_rating(show)) is not None
            and rating >= minimum_rating
        ),
        f"rating >= {minimum_rating:g}",
        progress_callback,
    )


def search_shows_by_genre(genre, progress_callback=None):
    """Return shows in a selected genre that meet the configured minimum rating."""
    genre = validate_genre(genre, TVMAZE_GENRES)
    logger.info(
        "TVMaze genre search requested",
        extra={"event": "genre_search", "query": genre},
    )
    return _scan_show_index(
        lambda show: (
            _show_has_genre(show, genre)
            and (
                (rating := _show_rating(show)) is not None
                and rating >= MINIMUM_RATING
            )
        ),
        f"genre={genre}, rating >= {MINIMUM_RATING:g}",
        progress_callback,
    )


def display_show(show):
    """Print the details shown in the command-line application."""
    network = show.get("network") or show.get("webChannel")
    network_name = network.get("name", "Not listed") if network else "Not listed"
    genres = ", ".join(show.get("genres") or []) or "Not listed"
    rating = (show.get("rating") or {}).get("average")

    print(f"\nShow: {show.get('name', 'Not listed')}")
    print(f"Rating: {rating if rating is not None else 'Not listed'}")
    print(f"Network/streaming service: {network_name}")
    print(f"Genres: {genres}")
    print(f"Premiere date: {show.get('premiered') or 'Not listed'}")
    print(f"End date: {show.get('ended') or 'Not listed'}")


def main():
    """Run the interactive command-line title, rating, or genre search."""
    logger.info(
        "TV show search application started",
        extra={"event": "application_startup"},
    )
    try:
        mode = input(
            "Search by (1) title, (2) minimum rating, or (3) genre? [1/2/3]: "
        ).strip()
        mode = validate_search_mode(
            {"1": "title", "2": "rating", "3": "genre"}.get(mode)
        )
        if mode == "rating":
            minimum_rating = validate_rating(
                float(input("Enter minimum rating (0-10): ")),
                "Search rating",
            )
            print("Searching the full TVMaze index; this may take a while.")

            def show_progress(page, count):
                print(
                    f"\rScanned {page} pages; found {count} qualifying shows...",
                    end="",
                    flush=True,
                )

            shows = search_shows_by_rating(minimum_rating, show_progress)
            print()
            title = f"rating >= {minimum_rating:g}"
        elif mode == "genre":
            genre = validate_genre(input("Enter a TVMaze genre: "), TVMAZE_GENRES)
            print("Searching the full TVMaze index; this may take a while.")

            def show_progress(page, count):
                print(
                    f"\rScanned {page} pages; found {count} qualifying shows...",
                    end="",
                    flush=True,
                )

            shows = search_shows_by_genre(genre, show_progress)
            print()
            title = f"genre {genre}"
        else:
            title = validate_search_title(input("Enter a TV show title: "))
            shows = search_shows(title)
    except ValueError as error:
        print(error)
        return
    except RuntimeError as error:
        print(error)
        return
    except Exception:
        logger.critical(
            "Unexpected exception in command-line application",
            extra={"event": "unexpected_exception"},
            exc_info=True,
        )
        print("An unexpected error occurred. See logs/application.log for details.")
        return

    if not shows:
        logger.info(
            "No matching TV show found",
            extra={"event": "search_no_results", "query": title},
        )
        print(f"No shows found for {title!r}.")
        return
    try:
        print(f"Found {len(shows)} matching show(s):")
        for show in shows:
            display_show(show)
    except Exception:
        logger.critical(
            "Unexpected exception while displaying show results",
            extra={"event": "unexpected_exception", "query": title},
            exc_info=True,
        )
        print("An unexpected error occurred. See logs/application.log for details.")


if __name__ == "__main__":
    main()
