"""CLI entry‑point."""
from __future__ import annotations
import argparse
import subprocess
import sys
import threading
import time
import logging
from selenium import webdriver
from selenium import webdriver

from selenium.webdriver.support.ui import WebDriverWait

from .config import (
    DEFAULT_PORT,
    DEFAULT_CHROME_PATH,
    DEFAULT_USER_DATA_DIR,
)
from .browser import connect_driver, launch_chrome_for_debugging
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


def _ensure_driver(args) -> tuple[webdriver.Chrome, subprocess.Popen | None]:
    # Attempt to connect to an existing instance first.
    driver = connect_driver(args.port)
    if driver:
        return driver, None

    # If connection fails, launch a new Chrome instance.
    _LOG.info(f"Could not connect. Launching Chrome on port {args.port}...")
    proc, chrome_log_file = launch_chrome_for_debugging(args.port, args.user_data_dir, args.chrome_path)
    time.sleep(5)  # Wait for Chrome to start.

    # Retry connecting to the new instance.
    driver = connect_driver(args.port)
    if not driver:
        proc.terminate()
        raise RuntimeError(f"Failed to setup WebDriver after launching a new Chrome instance. "
                         f"Check Chrome process logs at: {chrome_log_file}")
    
    _LOG.info("Successfully connected to the new Chrome instance.")
    return driver, proc


def _shutdown_on_exception(root_window, exc_info):
    """Logs unhandled exceptions and triggers a graceful shutdown."""
    _LOG.critical("Unhandled exception detected. Initiating shutdown.", exc_info=exc_info)
    if root_window and root_window.winfo_exists():
        # This will cause mainloop to exit, allowing the finally block to run.
        root_window.destroy()

def main():
    args = _parse_args()
    proc = None
    driver = None
    root = None
    exit_code = 0
    try:
        setup_logging()

        driver, proc = _ensure_driver(args)
        driver.get(args.url)
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

        recorder = Recorder(driver)

        import tkinter as tk
        root = tk.Tk()

        # --- Set up global exception handling ---
        # For Tkinter event loop exceptions
        root.report_callback_exception = lambda et, ev, tb: _shutdown_on_exception(root, (et, ev, tb))
        # For exceptions in other threads
        threading.excepthook = lambda args: _shutdown_on_exception(root, (args.exc_type, args.exc_value, args.exc_traceback))

        gui = RecorderGUI(root, recorder, auto_test=True)
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
        if driver and driver.service.is_connectable():
            driver.quit()
        if proc:
            proc.terminate()
        _LOG.info("Application terminated.")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
