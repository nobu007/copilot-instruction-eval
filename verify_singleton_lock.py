#!/usr/bin/env python3
"""
VSCode Extension Singleton Lock Verification Script

This script verifies that the singleton lock mechanism within the VSCode extension
works as expected. It uses the VSCodeProcessManager to launch an initial instance
and then attempts to launch a second instance directly to test the lock.
"""

import time
import psutil
import subprocess
import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from workspace.src.vscode_process_manager import VSCodeProcessManager

# --- Configuration ---
WORKSPACE_PATH = "/home/jinno/copilot-instruction-eval"
LOG_DIR = Path("evaluation_logs")
LOG_DIR.mkdir(exist_ok=True)

# --- Logging Setup ---
log_file_path = LOG_DIR / f"verify_singleton_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove all existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create file handler
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(file_handler)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


def count_vscode_processes_for_workspace(workspace_path: str) -> int:
    """Counts the number of VSCode main processes for a given workspace."""
    count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if not (cmdline and proc.info.get('name') and 'code' in proc.info['name'].lower()):
                continue
            if any(arg.startswith('--type=') for arg in cmdline):
                continue
            if workspace_path in ' '.join(cmdline):
                logger.info(f"Found active VSCode process for workspace: PID={proc.pid}")
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return count


def main():
    """Main test execution logic."""
    logger.info("--- Starting VSCode Singleton Lock Verification ---")
    manager = VSCodeProcessManager(workspace_path=WORKSPACE_PATH)

    try:
        # --- Step 1: Ensure no VSCode instance is running for the workspace ---
        logger.info("Step 1: Shutting down any existing VSCode instances to ensure a clean state...")
        manager.shutdown_singleton()
        time.sleep(5) # Give time for processes to terminate

        # --- Step 2: Launch the first, legitimate VSCode instance ---
        logger.info("Step 2: Launching the first VSCode instance via Process Manager...")
        manager.ensure_singleton_running() # This will wait 20s for stabilization
        logger.info("First instance is assumed to be running and holding the lock.")
        time.sleep(5) # Extra wait for full activation

        # --- Step 3: Attempt to launch a second, duplicate instance ---
        logger.info("Step 3: Attempting to launch a duplicate VSCode instance directly...")
        # We bypass the manager's singleton check to directly test the extension's lock
        try:
            subprocess.Popen([manager.vscode_executable, WORKSPACE_PATH, "--new-window"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Duplicate instance launched. The extension should now detect the lock and self-terminate.")
        except Exception as e:
            logger.error(f"Failed to launch duplicate instance: {e}")
            raise

        # --- Step 4: Verify the outcome ---
        logger.info("Step 4: Waiting 15 seconds for the duplicate instance to self-terminate...")
        time.sleep(15)

        logger.info("Checking the number of running VSCode processes for the workspace...")
        final_process_count = count_vscode_processes_for_workspace(WORKSPACE_PATH)
        logger.info(f"Final process count: {final_process_count}")

        if final_process_count == 1:
            logger.info("✅ SUCCESS: Exactly one VSCode instance is running. The singleton lock works.")
            logger.info("\n--- VERIFICATION SUCCEEDED ---")
        else:
            logger.error(f"❌ FAILURE: Expected 1 process, but found {final_process_count}. The singleton lock failed.")
            logger.error("\n--- VERIFICATION FAILED ---")

    except Exception as e:
        logger.critical(f"An unexpected error occurred during verification: {e}")
        logger.critical("\n--- VERIFICATION FAILED DUE TO AN ERROR ---")
    finally:
        # --- Step 5: Cleanup ---
        logger.info("Step 5: Cleaning up by shutting down the remaining VSCode instance...")
        manager.shutdown_singleton()
        logger.info("--- Verification complete. ---")

if __name__ == "__main__":
    main()
