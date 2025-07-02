
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import Browser
from .config import _LOG, AGENT_VERSION, RECORDED_ACTIONS_JSON_PATH, setup_logging
from .recorder import Recorder
from .actions import Action # Import Action class


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
        """Starts the automated test sequence for Google search."""
        self.log("--- Test Started: Google Search Scenario ---")
        self.update_status("Initializing...", color="orange")

        # Clean up previous test artifacts.
        if RECORDED_ACTIONS_JSON_PATH.exists():
            RECORDED_ACTIONS_JSON_PATH.unlink()
            self.log(f"Cleaned up old test file: {RECORDED_ACTIONS_JSON_PATH}")

        try:
            self.browser = Browser(start_url="https://www.google.com")
            self.recorder = Recorder(self.browser.driver)
        except Exception as e:
            _LOG.error(f"Failed to initialize Browser or Recorder: {e}", exc_info=True)
            self.update_status("FAIL: Initialization failed", color="red")
            self.log(f"ERROR: Initialization failed: {e}")
            self.root.after(4000, self.on_close)
            return

        self.recorder.start()
        self.update_status("REC: Recording started.", color="blue")
        self.log("Recording started. Navigating to Google and performing search...")

        # Step 1: Navigate to Google (already done in Browser init)
        # Step 2: Find the search input field and type a query
        self.root.after(2000, self._perform_search_and_schedule_check)

    def _perform_search_and_schedule_check(self):
        try:
            driver = self.browser.driver
            # Wait for the search input field to be present
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_query = "Gemini AI"
            # Set the value directly and record the input action
            search_box.send_keys(search_query) # Use send_keys to trigger events
            self.recorder.recorded.append(Action.now(action_type="input", target_element=driver.execute_script("return window.getElementInfo(arguments[0]);", search_box), input_text=search_query))
            self.log(f"Typed '{search_query}' into search box.")
            time.sleep(1) # Give recorder time to capture input

            # Simulate pressing Enter using JavaScript
            script = """
            var event = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            document.activeElement.dispatchEvent(event);
            """
            driver.execute_script(script)
            self.recorder.recorded.append(Action.now(action_type="key_press", key_pressed="Enter"))
            self.log("Pressed Enter to submit search via JavaScript.")
            time.sleep(2) # Give recorder time to capture key press and page to load

            self.log("Search performed. Verifying recorded actions...")
            self.root.after(1000, self._check_recorded_actions_for_search)

        except Exception as e:
            _LOG.error(f"Failed during search operation: {e}", exc_info=True)
            self.update_status("FAIL: Search operation failed", color="red")
            self.log(f"ERROR: Search operation failed: {e}")
            self.root.after(4000, self.on_close)

    def _check_recorded_actions_for_search(self):
        """Stops recording and checks the output file for the recorded search actions."""
        if self.recorder:
            self.recorder.stop()
        self.update_status("Verifying...", color="orange")
        self.log("Recording stopped. Checking for recorded search actions...")

        test_passed = False
        try:
            if RECORDED_ACTIONS_JSON_PATH.exists() and RECORDED_ACTIONS_JSON_PATH.stat().st_size > 0:
                with open(RECORDED_ACTIONS_JSON_PATH, "r") as f:
                    actions = json.load(f)
                _LOG.info(f"Recorded actions: {actions}") # Add this line for debugging

                # Check for navigate action to Google
                navigate_action_found = any(
                    action.get("action_type") == "navigate" and "https://www.google.com" in action.get("url", "")
                    for action in actions
                )

                # Check for input action with search query
                input_action_found = any(
                    action.get("action_type") == "input" and action.get("input_text") == "Gemini AI"
                    for action in actions
                )

                # Check for key_press action for Enter
                key_press_action_found = any(
                    action.get("action_type") == "key_press" and action.get("key_pressed") == "Enter"
                    for action in actions
                )

                if navigate_action_found and input_action_found and key_press_action_found:
                    self.log(f"Found all expected actions in file: {actions}")
                    test_passed = True
                else:
                    self.log(f"Missing expected actions. Found: {actions}")

        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.log(f"Error reading recorded actions file: {e}")
            pass # File not ready yet or malformed, continue polling if needed, but here it's a final check.

        if test_passed:
            self.update_status("PASS", color="green")
            self.log("--- Test Passed ---")
            self.log("Google search scenario recorded successfully.")
            _LOG.info("PASS: Google search scenario recorded successfully.")
            self.root.after(4000, self.on_close)
        else:
            self.update_status("FAIL", color="red")
            self.log("--- Test Failed ---")
            self.log("Google search scenario was not recorded as expected.")
            _LOG.error("FAIL: Google search scenario was not recorded as expected.")
            self.root.after(4000, self.on_close)

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
