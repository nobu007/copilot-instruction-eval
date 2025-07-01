"""
A dedicated, fully automated test harness for the Cascade Recorder.

This application launches the recorder, performs a predefined action (sending an
'Enter' key press), and then verifies that the action was correctly recorded in
the output JSON file. The result (PASS/FAIL) is displayed in the GUI.

The test runs automatically on launch and the application closes after a short
delay, requiring no user interaction.
"""
from __future__ import annotations

import json
import os
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from .browser import Browser
from .config import _LOG, AGENT_VERSION, RECORDED_ACTIONS_JSON_PATH, setup_logging
from .recorder import Recorder


class TestHarnessApp:
    """A Tkinter GUI application for running automated recorder tests."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Cascade Test Harness v{AGENT_VERSION}")
        self.root.geometry("800x600")

        self.browser: Browser | None = None
        self.recorder: Recorder | None = None
        self.poll_start_time: float = 0.0

        self._build_widgets()
        # Automatically start the test on launch after the GUI is ready.
        self.root.after(100, self.start_test_sequence)

    def _build_widgets(self):
        """Create the main widgets for the test harness."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(
            controls_frame, text="Status: Initializing...", font=("Helvetica", 12, "bold")
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_output = ScrolledText(log_frame, wrap=tk.WORD, state="disabled")
        self.log_output.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def log(self, message: str):
        """Log a message to the GUI's text widget."""
        def _update_widget():
            self.log_output.config(state="normal")
            self.log_output.insert(tk.END, message + "\n")
            self.log_output.see(tk.END)
            self.log_output.config(state="disabled")
        # Ensure GUI updates happen on the main thread.
        self.root.after(0, _update_widget)

    def update_status(self, text: str, color: str = "black"):
        """Update the status label with a given color."""
        def _update_widget():
            self.status_label.config(text=f"Status: {text}", foreground=color)
        self.root.after(0, _update_widget)

    def start_test_sequence(self):
        """Starts the automated test sequence."""
        self.log("--- Test Started ---")
        self.update_status("Initializing...", color="orange")

        # Clean up previous test artifacts.
        if RECORDED_ACTIONS_JSON_PATH.exists():
            RECORDED_ACTIONS_JSON_PATH.unlink()
            self.log(f"Cleaned up old test file: {RECORDED_ACTIONS_JSON_PATH}")

        try:
            self.browser = Browser(start_url="https://example.com")
            self.recorder = Recorder(self.browser.driver)
        except Exception as e:
            _LOG.error(f"Failed to initialize Browser or Recorder: {e}", exc_info=True)
            self.update_status("FAIL: Initialization failed", color="red")
            self.log(f"ERROR: Initialization failed: {e}")
            self.root.after(4000, self.on_close)
            return

        self.recorder.start()
        self.update_status("REC: Recording started.", color="blue")
        self.log("Recording started. Sending Enter key in 2s...")

        # Schedule the key press, which will then schedule the check.
        self.root.after(2000, self.send_enter_key_and_schedule_check)

    def send_enter_key_and_schedule_check(self):
        """Sends the key and then schedules the verification step."""
        self.send_enter_key()
        self.log("Enter key sent. Verifying result in 5s...")
        # Wait for a few seconds to ensure the event is processed and written.
        self.root.after(5000, self.check_recorded_action)

    def send_enter_key(self):
        """Sends an 'Enter' key press to the browser active element."""
        if self.browser and self.browser.driver:
            self.log("Sending 'Enter' key via ActionChains.")
            try:
                driver = self.browser.driver
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                _LOG.info("Enter key sent successfully.")
            except Exception as e:
                _LOG.error(f"Failed to send Enter key: {e}", exc_info=True)
                self.update_status("FAIL: Send key failed", color="red")
                self.log(f"ERROR: Failed to send 'Enter' key: {e}")

    def check_recorded_action(self):
        """Stops recording and checks the output file for the recorded action."""
        if self.recorder:
            self.recorder.stop()
        self.update_status("Verifying...", color="orange")
        self.log("Recording stopped. Checking for recorded action...")

        # Start polling
        self.poll_start_time = time.time()
        self.poll_for_action()

    def poll_for_action(self):
        """Polls the action file for the expected content."""
        timeout = 10  # seconds
        test_passed = False

        try:
            if (
                RECORDED_ACTIONS_JSON_PATH.exists()
                and RECORDED_ACTIONS_JSON_PATH.stat().st_size > 0
            ):
                with open(RECORDED_ACTIONS_JSON_PATH, "r") as f:
                    actions = json.load(f)

                if any(
                    action.get("action_type") == "key_press" and action.get("key_pressed") == "Enter"
                    for action in actions
                ):
                    self.log(f"Found matching action in file: {actions}")
                    test_passed = True
        except (json.JSONDecodeError, FileNotFoundError):
            # File not ready yet, continue polling.
            pass

        if test_passed:
            self.update_status("PASS", color="green")
            self.log("--- Test Passed ---")
            self.log("'Enter' key press was recorded successfully.")
            _LOG.info("PASS: 'Enter' key press was recorded successfully.")
            self.root.after(4000, self.on_close)
            return

        if time.time() - self.poll_start_time > timeout:
            self.update_status("FAIL", color="red")
            self.log("--- Test Failed ---")
            self.log("'Enter' key press was not recorded in time.")
            _LOG.error("FAIL: 'Enter' key press was not recorded in time.")
            self.root.after(4000, self.on_close)
            return

        # Schedule the next poll
        self.root.after(500, self.poll_for_action)

    def on_close(self):
        """Handles application cleanup and exit."""
        _LOG.info("Closing browser resources...")
        self.update_status("Closing...", color="gray")
        if self.recorder:
            self.recorder.stop()  # Ensure it's stopped
        if self.browser:
            self.browser.close()
        _LOG.info("Test Harness application terminated.")
        self.root.destroy()


def main():
    """Main entry point for the test harness application."""
    # Setup logging first.
    setup_logging()

    _LOG.info("Starting Test Harness application.")
    root = tk.Tk()
    app = TestHarnessApp(root)
    # The test sequence is started automatically by the App's __init__.
    root.mainloop()
    _LOG.info("Test Harness application terminated.")


if __name__ == "__main__":
    main()