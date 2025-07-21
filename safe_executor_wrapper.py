#!/usr/bin/env python3
"""
Safe Executor Wrapper

This script provides a safe execution environment for the 
`simple_continuous_executor.py` to prevent unintended side effects like
closing essential processes.
"""

import sys
import logging
import os

# Add project root to sys.path to allow module import
sys.path.append(os.path.dirname(__file__))

from simple_continuous_executor import main as executor_main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the executor safely."""
    logger.info("🚀 Starting the safe execution wrapper.")
    
    try:
        logger.info("Executing simple_continuous_executor.main()...")
        executor_main()
        logger.info("✅ Executor script completed successfully.")
            
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred in the wrapper: {e}", exc_info=True)

if __name__ == "__main__":
    main()
