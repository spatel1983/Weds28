import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


TVMAZE_SEARCH_URL = "https://api.tvmaze.com/search/shows"


def search_show(title):
    query = urlencode({"q": title})
    try:
        with urlopen(f"{TVMAZE_SEARCH_URL}?{query}", timeout=10) as response:
            results = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not retrieve show information: {error}") from error

    if not results:
        return None

    return results[0]["show"]


def display_show(show):
    network = show.get("network") or show.get("webChannel")
    network_name = network.get("name", "Not listed") if network else "Not listed"
    genres = ", ".join(show.get("genres") or []) or "Not listed"

    print(f"\nShow: {show.get('name', 'Not listed')}")
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
        print(f"No shows found for {title!r}.")
        return

    display_show(show)


if __name__ == "__main__":
    main()
