"""CLI entry‑point."""
from __future__ import annotations
import argparse
import subprocess
import sys
import threading
import time
import logging
from selenium import webdriver

from selenium.webdriver.support.ui import WebDriverWait

from .config import (
    DEFAULT_PORT,
    DEFAULT_CHROME_PATH,
    DEFAULT_USER_DATA_DIR,
)
from .browser import Browser # Import the Browser class
from .recorder import Recorder
from .gui import RecorderGUI
from .config import setup_logging

_LOG = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cascade Recorder POC (refactored)")
    p.add_argument("--url", default="https://example.com", help="Target URL to open")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Chrome debug port")
    p.add_argument("--chrome-path", default=DEFAULT_CHROME_PATH, help="Chrome executable path")
    p.add_argument("--user-data-dir", default=str(DEFAULT_USER_DATA_DIR), help="Chrome user‑profile dir")
    return p.parse_args()


def _shutdown_on_exception(root_window, exc_info):
    """Logs unhandled exceptions and triggers a graceful shutdown."""
    _LOG.critical("Unhandled exception detected. Initiating shutdown.", exc_info=exc_info)
    if root_window and root_window.winfo_exists():
        # This will cause mainloop to exit, allowing the finally block to run.
        root_window.destroy()

def main():
    args = _parse_args()
    browser_instance = None # Renamed from 'driver' to avoid confusion with selenium driver object
    root = None
    exit_code = 0
    try:
        setup_logging()

        # Use the Browser class directly
        browser_instance = Browser(
            start_url=args.url,
            port=args.port,
            user_data_dir=args.user_data_dir
        )
        driver = browser_instance.driver # Get the selenium driver object from the Browser instance

        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

        recorder = Recorder(driver)

        import tkinter as tk
        root = tk.Tk()

        # --- Set up global exception handling ---
        # For Tkinter event loop exceptions
        root.report_callback_exception = lambda et, ev, tb: _shutdown_on_exception(root, (et, ev, tb))
        # For exceptions in other threads
        threading.excepthook = lambda args: _shutdown_on_exception(root, (args.exc_type, args.exc_value, args.exc_traceback))

        gui = RecorderGUI(root, recorder, auto_test=False)
        root.mainloop()

    except Exception:
        _LOG.critical("A fatal error occurred during initialization. The application will now terminate.", exc_info=True)
        exit_code = 1

    finally:
        # cleanup
        try:
            # The root window might already be destroyed by the exception handler, so check.
            if root and root.winfo_exists():
                root.destroy()
        except tk.TclError:
            # This can happen if the root window is already gone.
            _LOG.debug("Tkinter window already destroyed, skipping cleanup.")
        if browser_instance: # Use browser_instance for cleanup
            browser_instance.close()
        _LOG.info("Application terminated.")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()