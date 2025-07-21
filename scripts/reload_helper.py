#!/usr/bin/env python3
"""
VSCode Singleton Reload Helper

This script centralizes the logic for safely reloading the VSCode singleton process.
It's designed to be called from the Makefile to ensure that all process lifecycle
events are managed by the VSCodeProcessManager.
"""

import os
import sys
import logging
import time

# Determine the project root directory dynamically from the script's location
# scripts -> project_root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the workspace/src directory to Python's path to allow importing the manager
SRC_PATH = os.path.join(ROOT_DIR, 'workspace', 'src')
sys.path.append(SRC_PATH)

from vscode_process_manager import VSCodeProcessManager

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('reload_helper')

def main():
    """Main function to run the safe reload process.
    This script now unconditionally calls the reload_singleton() method to ensure
    a consistent and robust restart cycle every time.
    """
    logger.info("🚀 Starting unconditional safe reload for VSCode singleton...")

    try:
        manager = VSCodeProcessManager(workspace_path=ROOT_DIR)
    except RuntimeError as e:
        logger.error(f"❌ Failed to initialize VSCodeProcessManager: {e}")
        sys.exit(1)

    # Unconditionally trigger the reload process.
    # The manager will handle shutting down an existing instance and starting a new one.
    logger.info("Calling reload_singleton() to ensure a fresh instance...")
    manager.reload_singleton()

    # Wait for the new extension to fully initialize.
    logger.info("Waiting 5 seconds for extension to initialize after reload...")
    time.sleep(5)

    logger.info("🎉 Safe reload process completed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()
