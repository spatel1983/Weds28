import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app_config import MINIMUM_RATING, REQUEST_TIMEOUT_SECONDS, TVMAZE_SEARCH_URL


def search_show(title):
    query = urlencode({"q": title})
    try:
        with urlopen(
            f"{TVMAZE_SEARCH_URL}?{query}", timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            results = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not retrieve show information: {error}") from error

    below_minimum_rating = None
    for result in results:
        show = result["show"]
        rating = (show.get("rating") or {}).get("average")
        if isinstance(rating, (int, float)) and rating >= MINIMUM_RATING:
            return show
        if isinstance(rating, (int, float)) and below_minimum_rating is None:
            below_minimum_rating = rating

    if below_minimum_rating is not None:
        raise RuntimeError(
            f"Rating {below_minimum_rating:g} is below the minimum rating "
            f"of {MINIMUM_RATING:g}."
        )
    return None


def display_show(show):
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
    title = input("Enter a TV show title: ").strip()
    if not title:
        print("Please enter a TV show title.")
        return

    try:
        show = search_show(title)
    except RuntimeError as error:
        print(error)
        return

    if show is None:
        print(
            f"No shows found for {title!r} with a rating of "
            f"{MINIMUM_RATING:g} or higher."
        )
        return

    display_show(show)


if __name__ == "__main__":
    main()
