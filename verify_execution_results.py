#!/usr/bin/env python3
"""
Verifies the results of an execution run by auditing the SQLite database.
This script acts as an independent auditor to provide objective proof of success.
"""
import sqlite3
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'simple_continuous_execution.db'
EXPECTED_INSTRUCTIONS = 5

import os
import json

RESPONSE_DIR = '/tmp/copilot-evaluation/responses'

def main():
    logger.info("--- Starting Rigorous Verification of Execution Results ---")
    
    try:
        conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
        cursor = conn.cursor()
        logger.info(f"✅ Successfully connected to database: {DB_PATH}")
    except sqlite3.OperationalError as e:
        logger.error(f"❌ DATABASE NOT FOUND: {e}. The executor likely failed to run.")
        sys.exit(1)

    failures = []
    try:
        # Step 1: Fetch all execution records from the database.
        cursor.execute("SELECT instruction_id, request_id, status FROM execution_results")
        records = cursor.fetchall()
        
        if len(records) != EXPECTED_INSTRUCTIONS:
            logger.error(f"❌ PRE-CHECK FAILED: Expected {EXPECTED_INSTRUCTIONS} records in DB, but found {len(records)}.")
            sys.exit(1)
        logger.info(f"✅ Found {len(records)} records in the database. Starting detailed verification...")

        # Step 2: Iterate through each record and verify the physical evidence.
        for i, (instruction_id, request_id, db_status) in enumerate(records):
            logger.info(f"-- Verifying record {i+1}/{len(records)} (Instruction: {instruction_id}) --")
            response_path = os.path.join(RESPONSE_DIR, f"{request_id}.json")

            # Test 1: Response File Existence
            if not os.path.exists(response_path):
                msg = f"File Existence FAILED: Response file not found at {response_path}"
                logger.error(f"❌ {msg}")
                failures.append((instruction_id, msg))
                continue # Move to next record

            # Test 2: File Content and Status Match
            try:
                with open(response_path, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)
                
                file_status = response_data.get('status')
                if db_status != 'success' or file_status != 'success':
                     msg = f"Status Mismatch FAILED: DB status is '{db_status}', file status is '{file_status}'. Expected 'success' in both."
                     logger.error(f"❌ {msg}")
                     failures.append((instruction_id, msg))
                     continue

                # Test 3: Non-Empty Deliverable
                if not response_data.get('data'):
                    msg = f"Deliverable Quality FAILED: Status is 'success' but 'data' payload is empty or missing."
                    logger.error(f"❌ {msg}")
                    failures.append((instruction_id, msg))
                    continue
                
                logger.info(f"✅ Verification PASSED for instruction {instruction_id}.")

            except json.JSONDecodeError:
                msg = f"File Content FAILED: Response file {response_path} is not valid JSON."
                logger.error(f"❌ {msg}")
                failures.append((instruction_id, msg))
            except Exception as e:
                msg = f"An unexpected error occurred verifying {response_path}: {e}"
                logger.error(f"❌ {msg}", exc_info=True)
                failures.append((instruction_id, msg))

    except Exception as e:
        logger.error(f"A critical error occurred during the verification process: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()

    # Final Verdict
    logger.info("--------------------------------------------------")
    if not failures:
        logger.info("🎉🎉🎉 OVERALL VERIFICATION PASSED: All records and their corresponding deliverables are valid.")
        logger.info("--------------------------------------------------")
        sys.exit(0)
    else:
        logger.error(f"❌ OVERALL VERIFICATION FAILED: {len(failures)} instructions failed validation.")
        for instruction_id, reason in failures:
            logger.error(f"  - Instruction '{instruction_id}': {reason}")
        logger.error("--------------------------------------------------")
        sys.exit(1)

if __name__ == "__main__":
    main()
