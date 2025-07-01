from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

# Enable verbose logging for webdriver-manager to diagnose hangs.
os.environ['WDM_LOG_LEVEL'] = '0'

# --- Version ---
AGENT_VERSION: str = "1.2.0-POC"

# --- Paths ---
PACKAGE_DIR: Path = Path(__file__).resolve().parent
LOG_DIR: Path = PACKAGE_DIR / "logs"
DEFAULT_USER_DATA_DIR: Path = Path.home() / "Chrome_dev_session_poc"

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

# File Paths
LOG_FILE: Path = LOG_DIR / "recorder_debug.log"
CHROME_LOG_FILE: Path = LOG_DIR / "chrome_process.log"
RECORDED_ACTIONS_JSON_PATH: Path = PACKAGE_DIR / "recorded_actions.json"  # Renamed for clarity

# --- Browser/Driver Settings ---
DEFAULT_CHROME_PATH: str = "google-chrome"
DEFAULT_PORT: int = 9222
DEBUG_PORT: int = DEFAULT_PORT  # Alias for clarity


# --- Logging Setup ---
_LOG = logging.getLogger()

def setup_logging(level: int = logging.INFO):
    """Configure root logger for file + console output."""
    logger = logging.getLogger()  # Get root logger
    logger.setLevel(logging.DEBUG)  # Capture everything

    # Purge duplicate handlers to avoid multiple log entries
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File handler (DEBUG) ---
    # Overwrite the log file on each run for cleanliness
    file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    # --- Console handler (INFO+) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    logger.info("Logging initialised → %s", LOG_FILE)
