#!/usr/bin/env python3
"""
Prepares a clean environment for a test run by deleting the old database file.
"""
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'simple_continuous_execution.db'

def main():
    logger.info("--- Preparing for a new test run ---")
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info(f"✅ Successfully deleted existing database: {DB_PATH}")
        except OSError as e:
            logger.error(f"❌ Failed to delete database {DB_PATH}: {e}", exc_info=True)
            # Exit with an error code if cleanup fails, to prevent running a dirty test
            exit(1)
    else:
        logger.info("No existing database found. Environment is clean.")
    logger.info("--- Preparation complete ---")

if __name__ == "__main__":
    main()
