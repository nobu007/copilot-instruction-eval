"""Browser launching, driver connection, log polling."""
from __future__ import annotations

import json
import logging
import socket
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from .config import (
    CHROME_LOG_FILE,
    DEFAULT_CHROME_PATH,
    DEFAULT_USER_DATA_DIR,
    DEBUG_PORT,
)
from .js_scripts import JS_EVENT_LISTENER_SCRIPT, JS_REMOVE_LISTENERS_SCRIPT

_LOG = logging.getLogger(__name__)


class Browser:
    """Manages the Chrome browser instance and WebDriver connection."""

    def __init__(
        self,
        start_url: str | None = None,
        port: int = DEBUG_PORT,
        user_data_dir: str = DEFAULT_USER_DATA_DIR,
        launch_timeout: int = 15,  # seconds
    ):
        self.port = port
        self.user_data_dir = user_data_dir
        self.proc: subprocess.Popen | None = None
        self.driver: webdriver.Chrome | None = None

        # Install or get the cached path for the driver ONCE.
        _LOG.info("Getting ChromeDriver path from webdriver-manager...")
        try:
            self.driver_path = ChromeDriverManager().install()
            _LOG.info(f"Using ChromeDriver at: {self.driver_path}")
        except Exception as e:
            _LOG.error(f"Failed to get ChromeDriver: {e}", exc_info=True)
            raise  # Re-raise the exception as we can't proceed.

        # Try to connect to an existing instance first
        if self._is_port_in_use():
            _LOG.info("Port %d is in use, attempting to connect...", self.port)
            self.driver = self._connect_driver()

        # If no existing instance, or failed to connect, launch a new one
        if not self.driver:
            _LOG.info("Could not connect to existing instance. Launching a new Chrome process...")
            self.proc, _ = self._launch_chrome()

            # Wait for the port to become available
            _LOG.info(f"Waiting up to {launch_timeout}s for port {self.port} to become active...")
            end_time = time.time() + launch_timeout
            port_ready = False
            while time.time() < end_time:
                if self._is_port_in_use():
                    port_ready = True
                    _LOG.info(f"Port {self.port} is now active.")
                    break
                time.sleep(0.5)

            if port_ready:
                # Port is open, now try to connect the driver
                _LOG.info("Attempting to connect WebDriver...")
                self.driver = self._connect_driver()

        # Final check
        if not self.driver:
            self.close()  # Cleanup any spawned processes
            raise WebDriverException(
                f"Failed to connect to Chrome on port {self.port} after {launch_timeout} seconds."
            )

        _LOG.info("Browser is ready and connected.")
        if start_url:
            self.driver.get(start_url)
            _LOG.info(f"Navigated to {start_url}")

    def _launch_chrome(self) -> tuple[subprocess.Popen, Path]:
        cmd_list = [
            DEFAULT_CHROME_PATH,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
        ]
        _LOG.info("Launching Chrome: %s", " ".join(cmd_list))
        _LOG.info("Chrome process logs will be saved to: %s", CHROME_LOG_FILE)
        log_file_handle = open(CHROME_LOG_FILE, "w")
        proc = subprocess.Popen(
            cmd_list, stdout=log_file_handle, stderr=log_file_handle
        )
        return proc, CHROME_LOG_FILE

    def _is_port_in_use(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def _connect_driver(self) -> webdriver.Chrome | None:
        """Attempts to connect to the Chrome debugger address using the pre-fetched driver path."""
        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")

        try:
            service = Service(self.driver_path)
            _LOG.info("Initializing WebDriver with service and options...")
            driver = webdriver.Chrome(service=service, options=opts)

            _LOG.info("Verifying WebDriver connection by getting title...")
            _ = driver.title  # This call verifies the connection is live.
            _LOG.info("WebDriver connection successful.")
            return driver
        except WebDriverException:
            _LOG.warning(
                "WebDriver connection failed. This is expected if browser is not ready.",
                exc_info=False,
            )
            return None

    def send_enter_key(self):
        """Sends an 'Enter' key press using JavaScript to ensure it's captured by listeners."""
        if not self.driver:
            _LOG.error("Driver not available, cannot send Enter key.")
            return
        try:
            _LOG.info("Sending 'Enter' key via JavaScript event dispatch.")
            # JavaScript to dispatch a keyboard event
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
            self.driver.execute_script(script)
            _LOG.info("Enter key sent successfully via JavaScript.")
        except Exception as e:
            _LOG.error(f"Failed to send Enter key via JavaScript: {e}", exc_info=True)

    def close(self):
        """Closes the WebDriver and terminates the Chrome process."""
        _LOG.info("Closing browser resources...")
        if self.driver:
            try:
                self.driver.quit()
                _LOG.info("WebDriver session closed.")
            except Exception as e:
                _LOG.error("Error closing WebDriver: %s", e)
            self.driver = None
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
                _LOG.info("Chrome process terminated.")
            except Exception as e:
                _LOG.error("Error terminating Chrome process: %s", e)
            self.proc = None


# Standalone functions for recorder logic
def inject_listeners(driver: webdriver.Chrome):
    driver.execute_script(JS_EVENT_LISTENER_SCRIPT)


def remove_listeners(driver: webdriver.Chrome):
    driver.execute_script(JS_REMOVE_LISTENERS_SCRIPT)
