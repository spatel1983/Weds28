import os
import sys
import queue
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

from tvmaze_search import search_show


class TVMazeSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TV Show Search")
        self.root.minsize(420, 320)

        self.results = queue.Queue()

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="TV Show Search", font=("", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )
        ttk.Label(main, text="Enter a show title:").pack(anchor="w")

        search_row = ttk.Frame(main)
        search_row.pack(fill="x", pady=(4, 12))

        self.title_entry = ttk.Entry(search_row)
        self.title_entry.pack(side="left", fill="x", expand=True)
        self.title_entry.bind("<Return>", self.start_search)

        self.search_button = ttk.Button(
            search_row, text="Search", command=self.start_search
        )
        self.search_button.pack(side="left", padx=(8, 0))

        self.status = ttk.Label(main, text=" ")
        self.status.pack(anchor="w", pady=(0, 6))

        self.output = tk.Text(main, height=9, wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True)
        self.title_entry.focus()
        self.root.after(100, self.check_results)

    def start_search(self, _event=None):
        title = self.title_entry.get().strip()
        if not title:
            self.show_output("Please enter a TV show title.")
            self.status.config(text="")
            self.title_entry.focus()
            return

        self.search_button.config(state="disabled")
        self.status.config(text="Searching...")
        self.show_output("")
        threading.Thread(
            target=self.search_in_background, args=(title,), daemon=True
        ).start()

    def search_in_background(self, title):
        try:
            show = search_show(title)
            self.results.put((title, show, None))
        except RuntimeError as error:
            self.results.put((title, None, str(error)))

    def check_results(self):
        try:
            title, show, error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.search_button.config(state="normal")
            if error:
                self.status.config(text="Search failed.")
                self.show_output(error)
            elif show is None:
                self.status.config(text="No results found.")
                self.show_output(f"No shows found for {title!r}.")
            else:
                self.status.config(text="Search complete.")
                self.show_output(format_show(show))
        finally:
            self.root.after(100, self.check_results)

    def show_output(self, text):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.config(state="disabled")


def format_show(show):
    network = show.get("network") or show.get("webChannel")
    network_name = network.get("name", "Not listed") if network else "Not listed"
    genres = ", ".join(show.get("genres") or []) or "Not listed"

    return (
        f"Show: {show.get('name', 'Not listed')}\n"
        f"Network/streaming service: {network_name}\n"
        f"Genres: {genres}\n"
        f"Premiere date: {show.get('premiered') or 'Not listed'}\n"
        f"End date: {show.get('ended') or 'Not listed'}"
    )


def main():
    root = tk.Tk()
    TVMazeSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
