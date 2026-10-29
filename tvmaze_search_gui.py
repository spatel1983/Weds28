"""Tkinter interface for searching TVMaze by title, rating, or genre."""

import logging
import os
import queue
import sys
import threading

for library_variable, library_directory in (
    ("TCL_LIBRARY", os.path.join(sys.base_prefix, "tcl", "tcl8.6")),
    ("TK_LIBRARY", os.path.join(sys.base_prefix, "tcl", "tk8.6")),
):
    configured_directory = os.environ.get(library_variable)
    if os.path.isdir(library_directory) and not (
        configured_directory and os.path.isdir(configured_directory)
    ):
        os.environ[library_variable] = library_directory

import tkinter as tk
from tkinter import ttk

from app_config import (
    MINIMUM_RATING,
    TVMAZE_GENRES,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
)
from tvmaze_search import (
    search_shows,
    search_shows_by_genre,
    search_shows_by_rating,
)
from validation import (
    validate_genre,
    validate_rating,
    validate_search_mode,
    validate_search_title,
)


logger = logging.getLogger(__name__)


class TVMazeSearchApp:
    """Build the GUI and coordinate background searches with Tk's event loop."""

    def __init__(self, root):
        """Create controls, result display, and scrolling behavior."""
        self.root = root
        self.root.report_callback_exception = self.report_callback_exception
        self.root.title(WINDOW_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self.results = queue.Queue()

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="TV Show Search", font=("", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )
        mode_row = ttk.Frame(main)
        mode_row.pack(anchor="w")
        self.search_mode = tk.StringVar(value="title")
        ttk.Radiobutton(
            mode_row,
            text="Search by title",
            variable=self.search_mode,
            value="title",
            command=self.update_search_mode,
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            mode_row,
            text="Search by minimum rating",
            variable=self.search_mode,
            value="rating",
            command=self.update_search_mode,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_row,
            text="Search by genre",
            variable=self.search_mode,
            value="genre",
            command=self.update_search_mode,
        ).pack(side="left", padx=(12, 0))

        search_row = ttk.Frame(main)
        search_row.pack(fill="x", pady=(4, 12))

        self.title_entry = ttk.Entry(search_row)
        self.title_entry.pack(side="left", fill="x", expand=True)
        self.title_entry.bind("<Return>", self.start_search)

        self.rating_var = tk.StringVar(value=f"{MINIMUM_RATING:g}")
        self.rating_input = ttk.Spinbox(
            search_row,
            from_=0,
            to=10,
            increment=0.1,
            textvariable=self.rating_var,
            width=8,
            state="readonly",
        )
        self.rating_input.bind("<Return>", self.start_search)

        self.genre_var = tk.StringVar(value=TVMAZE_GENRES[0])
        self.genre_input = ttk.Combobox(
            search_row,
            textvariable=self.genre_var,
            values=TVMAZE_GENRES,
            state="readonly",
            width=20,
        )
        self.genre_input.bind("<Return>", self.start_search)

        self.search_button = ttk.Button(
            search_row, text="Search", command=self.start_search
        )
        self.search_button.pack(side="right", padx=(8, 0))

        self.status = ttk.Label(main, text=" ")
        self.status.pack(anchor="w", pady=(0, 6))

        output_frame = ttk.Frame(main)
        output_frame.pack(fill="both", expand=True)
        self.output = tk.Text(output_frame, height=9, wrap="none", state="disabled")
        vertical_scrollbar = ttk.Scrollbar(
            output_frame, orient="vertical", command=self.output.yview
        )
        horizontal_scrollbar = ttk.Scrollbar(
            output_frame, orient="horizontal", command=self.output.xview
        )
        self.output.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.output.bind("<MouseWheel>", self.scroll_vertical)
        self.output.bind("<Shift-MouseWheel>", self.scroll_horizontal)
        self.output.bind("<Button-4>", self.scroll_linux_vertical)
        self.output.bind("<Button-5>", self.scroll_linux_vertical)
        self.output.bind("<Shift-Button-4>", self.scroll_linux_horizontal)
        self.output.bind("<Shift-Button-5>", self.scroll_linux_horizontal)
        self.title_entry.focus()
        self.root.after(100, self.check_results)

    def update_search_mode(self):
        """Show only the input control needed by the selected search mode."""
        self.title_entry.pack_forget()
        self.rating_input.pack_forget()
        self.genre_input.pack_forget()
        if self.search_mode.get() == "rating":
            self.rating_input.pack(side="left")
        elif self.search_mode.get() == "genre":
            self.genre_input.pack(side="left", fill="x", expand=True)
        else:
            self.title_entry.pack(side="left", fill="x", expand=True)

    def start_search(self, _event=None):
        """Validate current inputs and start a worker thread for the search."""
        try:
            mode = validate_search_mode(self.search_mode.get())
        except ValueError as error:
            self.show_output(str(error))
            self.status.config(text="")
            return

        minimum_rating = None
        genre = None
        if mode == "rating":
            try:
                minimum_rating = validate_rating(
                    float(self.rating_var.get()), "Search rating"
                )
            except (ValueError, TypeError) as error:
                self.show_output(str(error) or "Enter a rating between 0 and 10.")
                self.status.config(text="")
                return
            query = f"rating >= {minimum_rating:g}"
        elif mode == "genre":
            try:
                genre = validate_genre(self.genre_var.get(), TVMAZE_GENRES)
            except ValueError as error:
                self.show_output(str(error))
                self.status.config(text="")
                return
            query = f"genre {genre}"
        else:
            try:
                query = validate_search_title(self.title_entry.get())
            except ValueError as error:
                self.show_output(str(error))
                self.status.config(text="")
                self.title_entry.focus()
                return

        self.search_button.config(state="disabled")
        if mode in ("rating", "genre"):
            self.status.config(
                text="Scanning TVmaze show index; this may take a while..."
            )
        else:
            self.status.config(text="Searching...")
        self.show_output("")
        threading.Thread(
            target=self.search_in_background,
            args=(mode, query, minimum_rating, genre),
            daemon=True,
        ).start()

    def search_in_background(
        self, mode, query, minimum_rating=None, genre=None
    ):
        """Run API work off the UI thread and queue results for the event loop."""
        try:
            if mode == "rating":
                shows = search_shows_by_rating(
                    minimum_rating,
                    # Send progress through a queue; Tk widgets must only be
                    # updated by the main GUI thread.
                    progress_callback=lambda page, count: self.results.put(
                        ("progress", mode, query, (page, count), None)
                    ),
                )
            elif mode == "genre":
                shows = search_shows_by_genre(
                    genre,
                    progress_callback=lambda page, count: self.results.put(
                        ("progress", mode, query, (page, count), None)
                    ),
                )
            else:
                shows = search_shows(query)
            self.results.put(("complete", mode, query, shows, None))
        except RuntimeError as error:
            self.results.put(("complete", mode, query, None, str(error)))
        except Exception as error:
            logger.critical(
                "Unexpected exception during TVMaze search",
                extra={
                    "event": "unexpected_exception",
                    "query": query,
                    "error": str(error),
                },
                exc_info=True,
            )
            self.results.put(
                (
                    "complete",
                    mode,
                    query,
                    None,
                    f"Unexpected error while searching: {error}",
                )
            )

    def check_results(self):
        """Apply queued progress and results updates on Tk's main thread."""
        try:
            event, mode, query, payload, error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            if event == "progress":
                page, match_count = payload
                self.status.config(
                    text=f"Scanned {page} pages; found {match_count} qualifying shows..."
                )
            else:
                self.search_button.config(state="normal")
                if error:
                    self.status.config(text="Search failed.")
                    self.show_output(error)
                elif not payload:
                    self.status.config(text="No shows found.")
                    logger.info(
                        "No matching TV show found",
                        extra={"event": "search_no_results", "query": query},
                    )
                    self.show_output(f"No TV shows found for {query!r}.")
                else:
                    self.status.config(text=f"Found {len(payload)} matching show(s).")
                    self.show_output(format_shows(payload))
        finally:
            self.root.after(100, self.check_results)

    def show_output(self, text):
        """Replace the read-only result text and reset both scroll positions."""
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.yview_moveto(0)
        self.output.xview_moveto(0)
        self.output.config(state="disabled")

    def scroll_vertical(self, event):
        """Scroll the results vertically using a mouse-wheel event."""
        self.output.yview_scroll(self.wheel_units(event), "units")
        return "break"

    def scroll_horizontal(self, event):
        """Scroll long result rows horizontally using a mouse-wheel event."""
        self.output.xview_scroll(self.wheel_units(event), "units")
        return "break"

    @staticmethod
    def wheel_units(event):
        """Convert platform-specific wheel deltas into Tk text-widget units."""
        if event.delta:
            return -max(1, abs(event.delta) // 120) * (1 if event.delta > 0 else -1)
        return -1 if event.num == 4 else 1

    def scroll_linux_vertical(self, event):
        """Handle Linux wheel-button events for vertical scrolling."""
        self.output.yview_scroll(-1 if event.num == 4 else 1, "units")
        return "break"

    def scroll_linux_horizontal(self, event):
        """Handle Linux Shift+wheel-button events for horizontal scrolling."""
        self.output.xview_scroll(-1 if event.num == 4 else 1, "units")
        return "break"

    def report_callback_exception(self, exception_type, exception, traceback):
        """Log Tk callback failures and show a useful message in the GUI."""
        logger.critical(
            "Unexpected exception in graphical event handler",
            extra={
                "event": "unexpected_exception",
                "error": str(exception),
            },
            exc_info=(exception_type, exception, traceback),
        )
        self.status.config(text="An unexpected error occurred.")
        self.show_output("See logs/application.log for details.")


def format_show(show):
    """Format one show's fields as readable multiline details."""
    network = show.get("network") or show.get("webChannel")
    network_name = network.get("name", "Not listed") if network else "Not listed"
    genres = ", ".join(show.get("genres") or []) or "Not listed"
    rating = (show.get("rating") or {}).get("average")

    return (
        f"Show: {show.get('name', 'Not listed')}\n"
        f"Rating: {rating if rating is not None else 'Not listed'}\n"
        f"Network/streaming service: {network_name}\n"
        f"Genres: {genres}\n"
        f"Premiere date: {show.get('premiered') or 'Not listed'}\n"
        f"End date: {show.get('ended') or 'Not listed'}"
    )


def format_shows(shows):
    """Format each show's details as one row for the results text box."""
    rows = []
    for index, show in enumerate(shows, start=1):
        rating = (show.get("rating") or {}).get("average")
        network = show.get("network") or show.get("webChannel")
        network_name = network.get("name", "Not listed") if network else "Not listed"
        genres = ", ".join(show.get("genres") or []) or "Not listed"
        rows.append(
            " | ".join(
                (
                    f"{index}. {show.get('name') or 'Untitled show'}",
                    f"Rating: {rating if rating is not None else 'Not listed'}",
                    f"Network: {network_name}",
                    f"Genres: {genres}",
                    f"Premiered: {show.get('premiered') or 'Not listed'}",
                    f"Ended: {show.get('ended') or 'Not listed'}",
                )
            )
        )
    return "\n".join(rows)


def main():
    """Create the root window and start the Tk event loop."""
    logger.info(
        "TV show search application started",
        extra={"event": "application_startup"},
    )
    try:
        root = tk.Tk()
        TVMazeSearchApp(root)
        root.mainloop()
    except Exception:
        logger.critical(
            "Unexpected exception in graphical application",
            extra={"event": "unexpected_exception"},
            exc_info=True,
        )
        raise


if __name__ == "__main__":
    main()
