"""Double-click entry point: prepare local data, start the app, open its page."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

from .catalogue import DEFAULT_DATA, sync
from .market import sync_market

URL = "http://127.0.0.1:8765"


def running():
    try:
        with urlopen(URL + "/api/health", timeout=1) as response:
            return json.load(response).get("app") == "CitizenSolver"
    except (OSError, ValueError):
        return False


def prepare():
    if running():
        return
    if not (DEFAULT_DATA / "manifest.json").exists():
        sync()
    if not (DEFAULT_DATA / "market.json").exists():
        try:
            sync_market()
        except (OSError, ValueError, KeyError):
            pass  # The workbench can refresh these optional records later.
    DEFAULT_DATA.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    with (DEFAULT_DATA / "server.log").open("a", encoding="utf-8") as log:
        executable = Path(sys.executable)
        if executable.name.lower() == "pythonw.exe":
            executable = executable.with_name("python.exe")
        process = subprocess.Popen([str(executable), "-m", "citizensolver", "serve"],
            cwd=Path(__file__).resolve().parent.parent, env=environment, stdout=log, stderr=log,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if running():
            return
        if process.poll() is not None:
            raise RuntimeError("CitizenSolver could not start. Port 8765 may be in use. See data/server.log in the project folder.")
        time.sleep(.25)
    raise RuntimeError("CitizenSolver is still starting. Try opening it again shortly. Details are in data/server.log.")


def main():
    import tkinter as tk
    from tkinter import messagebox, ttk
    from threading import Thread
    from queue import Queue

    root = tk.Tk()
    root.title("CitizenSolver")
    root.geometry("420x135")
    root.resizable(False, False)
    tk.Label(root, text="Opening your flight workbench…", font=("Segoe UI", 12)).pack(pady=(20, 5))
    tk.Label(root, text="First launch downloads the game catalogue.", font=("Segoe UI", 9)).pack()
    progress = ttk.Progressbar(root, mode="indeterminate", length=350)
    progress.pack(pady=15)
    progress.start()
    result = Queue()

    def worker():
        try:
            prepare()
            result.put(None)
        except Exception as exc:
            result.put(str(exc))

    def complete():
        if result.empty():
            root.after(100, complete)
            return
        error = result.get()
        if error:
            messagebox.showerror("CitizenSolver", error)
        else:
            webbrowser.open(URL)
        root.destroy()

    Thread(target=worker, daemon=True).start()
    root.after(100, complete)
    root.mainloop()


if __name__ == "__main__":
    main()
