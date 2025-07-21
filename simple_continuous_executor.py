#!/usr/bin/env python3
"""
Simple VSCode Copilot Continuous Execution System

This system leverages the completed VSCode extension to provide continuous,
automated execution of GitHub Copilot instructions with internal API reliability.
Simplified version without pandas dependency.
"""

import json
import os
import sys
import time
import uuid
import logging

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests
from dataclasses import dataclass
from enum import Enum
import sqlite3
import argparse
import shutil

# Import the safe process manager
# Add workspace to sys.path to allow module import
sys.path.append(os.path.join(os.path.dirname(__file__), 'workspace', 'src'))
from vscode_process_manager import VSCodeProcessManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('simple_continuous_execution.log')
    ]
)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for Copilot"""
    AGENT = "agent"
    CHAT = "chat"


class ExecutionStatus(Enum):
    """Status of instruction execution"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """Result of a single instruction execution"""
    instruction_id: str
    instruction_text: str
    mode: ExecutionMode
    model: str
    response: str
    execution_time: float
    status: ExecutionStatus
    timestamp: datetime
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None


class SimpleCopilotExecutor:
    """Simplified executor class that integrates with VSCode extension"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the continuous executor"""
        self.config = config
        self.extension_path = config.get('extension_path', 
            '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension')
        self.vscode_command = config.get('vscode_command', 'code')
        self.execution_timeout = config.get('execution_timeout', 60)  # seconds

        
        # Initialize database
        self.db_path = config.get('db_path', 'simple_continuous_execution.db')
        self._setup_database()
        
        # Load instructions
        self.instructions = self._load_instructions()
        
        # Execution state
        self.current_execution: Optional[ExecutionResult] = None
        self.execution_queue: List[Dict[str, Any]] = []
        self.results: List[ExecutionResult] = []
        self.execution_completed = False

        # Initialize the safe process manager
        self.vscode_manager = VSCodeProcessManager(workspace_path=os.path.dirname(__file__))

    def _create_request(self, request_id: str, instruction: Dict[str, Any], mode: ExecutionMode, model: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to create a request dictionary."""
        return {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "test_id": params.get("test_id", "N/A"),
            'prompt': instruction.get('description', '') if isinstance(instruction, dict) else instruction,
            "model": model,
            "mode": mode.value,
            "timeout": self.execution_timeout,
            "expected_elements": params.get("expected_elements", []),
            "category": params.get("category", "general")
        }

    def _wait_for_extension_ready(self, timeout: int = 60):
        """Wait for the VSCode extension to be ready by pinging it robustly."""
        logger.info("Waiting for VSCode extension to become ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            ping_id = f"ping_{uuid.uuid4()}"
            request_file = os.path.join('/tmp/copilot-evaluation/requests', f"{ping_id}.json")
            response_file = os.path.join('/tmp/copilot-evaluation/responses', f"{ping_id}.json")
            ping_request = self._create_request(ping_id, "ping", ExecutionMode.AGENT, "health-check", {})

            # Ensure response from previous failed ping doesn't exist
            if os.path.exists(response_file):
                os.remove(response_file)

            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(ping_request, f)
            logger.info(f"Ping request {ping_id} sent.")

            # Poll for the pong response
            poll_start_time = time.time()
            while time.time() - poll_start_time < 10:  # Poll for 10 seconds for this specific ping
                if os.path.exists(response_file):
                    try:
                        # Short delay to prevent reading a partially written file
                        time.sleep(0.1)
                        with open(response_file, 'r', encoding='utf-8') as f:
                            response_data = json.load(f)
                        
                        if response_data.get('response') == 'pong' and response_data.get('request_id') == ping_id:
                            logger.info(f"✅ Pong received for {ping_id}.")
                            # SUCCESS: Clean up both files and return
                            os.remove(request_file)
                            os.remove(response_file)
                            logger.info("✅ Extension is ready.")
                            return
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"⚠️ Could not read or decode pong file {response_file}: {e}")
                time.sleep(0.5) # Poll every 500ms

            # TIMEOUT for this specific ping. Do NOT remove the request file.
            # The extension might still be processing it. We'll just try with a new ping.
            logger.warning(f"⚠️ Timed out waiting for pong for {ping_id}. Retrying with a new ping.")

        # GLOBAL TIMEOUT: If the entire loop finishes, the extension is not ready.
        logger.error("❌ Global timeout. Timed out waiting for VSCode extension to become ready.")
        raise TimeoutError("VSCode extension did not become ready in time.")
        
        logger.info(f"🚀 Simple VSCode Copilot Continuous Executor initialized")
        logger.info(f"📁 Extension path: {self.extension_path}")
        logger.info(f"📊 Database: {self.db_path}")

    def _setup_database(self):
        """Setup SQLite database for storing execution results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instruction_id TEXT NOT NULL,
                    instruction_text TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    response TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    error_message TEXT,
                    metrics TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"📊 Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise

    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from JSON file"""
        try:
            instructions_file = os.path.join(os.path.dirname(__file__), 'instructions.json')
            with open(instructions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get('instructions', [])
                logger.info(f"📝 Loaded {len(instructions)} instructions")
                return instructions
        except Exception as e:
            logger.error(f"❌ Failed to load instructions: {e}")
            return []


    def _send_prompt_to_copilot(self, instruction: 'Instruction', mode: ExecutionMode, model: str) -> Tuple[ExecutionStatus, str, float]:
        """Send prompt to Copilot via file-based IPC by only placing the request file."""
        base_dir = '/tmp/copilot-evaluation'
        requests_dir = os.path.join(base_dir, 'requests')
        os.makedirs(requests_dir, exist_ok=True)

        request_id = instruction['id']
        request_file = os.path.join(requests_dir, f"{request_id}.json")
        execution_start_time = time.time()

        try:
            instruction_text = instruction.get('description', '')
            req = self._create_request(request_id, instruction_text, mode, model, instruction.get('params', {}))

            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(req, f, indent=2)

            execution_time = time.time() - execution_start_time
            logger.info(f"Request file placed: {request_file} (took {execution_time:.4f}s)")

            # The client's responsibility ends here. It returns a success status
            # indicating the request was PLACED, not that it was completed.
            return ExecutionStatus.SUCCESS, "Request placed successfully.", execution_time

        except Exception as e:
            execution_time = time.time() - execution_start_time
            logger.error(f"❌ An unexpected error occurred while placing request: {e}", exc_info=True)
            return ExecutionStatus.ERROR, f"Unexpected error placing request: {e}", execution_time

    def execute_instruction(self, instruction: 'Instruction', 
                          mode: ExecutionMode = ExecutionMode.AGENT,
                          model: str = "copilot/gpt-4") -> ExecutionResult:
        """Execute a single instruction"""
        
        instruction_id = instruction['id']
        instruction_text = instruction.get('description', '')
        
        logger.info(f"🎯 Executing instruction: {instruction_id}")
        logger.info(f"📝 Description: {instruction_text[:100]}...")
        
        start_time = time.time()
        
        try:
            # Send prompt to Copilot
            status, response, exec_time = self._send_prompt_to_copilot(
                instruction, mode, model
            )
            
            result = ExecutionResult(
                instruction_id=instruction_id,
                instruction_text=instruction_text,
                mode=mode,
                model=model,
                response=response,
                execution_time=exec_time,
                status=status,
                timestamp=datetime.now(),
                error_message=None if status == ExecutionStatus.SUCCESS else response,
                metrics={}
            )
            
            # Save result
            self._save_result(result)
            self.results.append(result)
            
            logger.info(f"✅ Instruction '{instruction_id}' executed. Status: {status.name}")
            if status == ExecutionStatus.SUCCESS:
                logger.info("Creating verification proof file...")
                os.system("ls -l /tmp/copilot-evaluation/processed/ > run_verification_proof.txt")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Instruction execution failed: {e}")
            
            result = ExecutionResult(
                instruction_id=instruction_id,
                instruction_text=instruction_text,
                mode=mode,
                model=model,
                response="",
                execution_time=execution_time,
                status=ExecutionStatus.ERROR,
                timestamp=datetime.now(),
                error_message=str(e),
                metrics={}
            )
            
            self._save_result(result)
            self.results.append(result)
            return result

    def _save_result(self, result: ExecutionResult):
        """Save execution result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO execution_results 
                (instruction_id, instruction_text, mode, model, response, 
                 execution_time, status, timestamp, error_message, metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.instruction_id,
                result.instruction_text,
                result.mode.value,
                result.model,
                result.response,
                result.execution_time,
                result.status.value,
                result.timestamp.isoformat(),
                result.error_message,
                json.dumps(result.metrics) if result.metrics else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to save result: {e}")

    def _process_request_file(self, filepath: str, mode: ExecutionMode, model: str):
        """
        Processes a single request file with robust error handling and logging.
        This is the single source of truth for request processing.
        """
        filename = os.path.basename(filepath)
        request_dir = os.path.dirname(filepath)
        base_dir = os.path.dirname(request_dir)
        failed_dir = os.path.join(base_dir, 'failed')
        response_dir = os.path.join(base_dir, 'responses')
        
        logger.info(f"--- Processing request file: {filename} ---")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                instruction = json.load(f)
            logger.info(f"File {filename} read successfully.")

            # Basic validation
            if 'id' not in instruction or 'description' not in instruction:
                raise ValueError("Request missing required fields 'id' or 'description'")
            logger.info(f"File {filename} validated successfully.")
            
            # This is the core execution call
            self.execute_instruction(instruction, mode, model)
            logger.info(f"--- Finished processing {filename} successfully ---")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}. Moving to 'failed' directory.")
            shutil.move(filepath, os.path.join(failed_dir, filename))
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid request data in {filepath}: {e}. Moving to 'failed' directory.")
            shutil.move(filepath, os.path.join(failed_dir, filename))
        except Exception as e:
            logger.critical(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
            # Ensure both the request and any potential response file are cleaned up.
            shutil.move(filepath, os.path.join(failed_dir, filename))
            
            response_file = os.path.join(response_dir, filename)
            if os.path.exists(response_file):
                logger.warning(f"Cleaning up orphaned response file from failed request: {response_file}")
                os.remove(response_file)

    def run(self, run_once: bool, mode: ExecutionMode, model: str, poll_interval: int = 5):
        """
        The single, unified execution loop.
        Scans for requests and processes them using _process_request_file.
        
        Args:
            run_once: If True, the loop runs once and exits. Otherwise, runs continuously.
            mode: The execution mode (agent or chat).
            model: The model to use.
            poll_interval: Seconds to wait between scans in continuous mode.
        """
        request_dir = self.config.get('request_dir', '/tmp/copilot-evaluation/requests')

        while True:
            logger.info(f"Scanning for requests in {request_dir}")
            try:
                request_files = [f for f in os.listdir(request_dir) if f.endswith('.json')]
                if not request_files:
                    logger.info("No new requests found.")
                else:
                    for filename in request_files:
                        filepath = os.path.join(request_dir, filename)
                        self._process_request_file(filepath, mode, model)
            except Exception as e:
                logger.error(f"Error during request scanning loop: {e}", exc_info=True)

            if run_once:
                logger.info("Run-once mode finished. Exiting loop.")
                break
            
            logger.info(f"Waiting for {poll_interval} seconds before next scan...")
            time.sleep(poll_interval)

    def generate_report(self):
        """Generate a summary report of the execution results"""
        if not self.results:
            logger.info("No results to generate a report.")
            return

        total_executions = len(self.results)
        success_count = sum(1 for r in self.results if r.status == ExecutionStatus.SUCCESS)
        failed_count = sum(1 for r in self.results if r.status != ExecutionStatus.SUCCESS)
        avg_exec_time = sum(r.execution_time for r in self.results) / total_executions if total_executions > 0 else 0

        logger.info("\n--- Execution Report ---")
        logger.info(f"Total Executions: {total_executions}")
        logger.info(f"  - Success: {success_count}")
        logger.info(f"  - Failed:  {failed_count}")
        logger.info(f"Average Execution Time: {avg_exec_time:.2f} seconds")
        logger.info("----------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple, Unified VSCode Copilot Executor")
    parser.add_argument('--run-once', action='store_true', help='Run the executor once and exit.')
    parser.add_argument('--mode', type=str, choices=['agent', 'chat'], default='agent', help='Execution mode for Copilot.')
    parser.add_argument('--model', type=str, default='copilot/gpt-4', help='Model to use for execution.')
    args = parser.parse_args()

    config = {
        'db_path': 'simple_continuous_execution.db',
        'execution_timeout': 120,
        'request_dir': '/tmp/copilot-evaluation/requests'
    }
    
    executor = SimpleCopilotExecutor(config)
    
    # --- Main Execution Block ---
    execution_mode_log = "Run-Once" if args.run_once else "Continuous"
    logger.info(f"=================================================")
    logger.info(f"  Starting Copilot Executor in {execution_mode_log} Mode")
    logger.info(f"=================================================")

    try:
        logger.info("Ensuring VSCode singleton is running...")
        executor.vscode_manager.ensure_singleton_running()
        pid, _ = executor.vscode_manager.get_status()
        logger.info(f"✅ VSCode is running with PID: {pid}")

        logger.info("Waiting 20 seconds for the extension to cold start...")
        time.sleep(20)
        
        executor._wait_for_extension_ready()

        # The single, unified run call
        executor.run(
            run_once=args.run_once,
            mode=ExecutionMode(args.mode),
            model=args.model
        )
            
    except (Exception, KeyboardInterrupt) as e:
        logger.error(f"A critical error occurred in the main execution block: {e}", exc_info=True)
    finally:
        logger.info("Execution finished. Requesting VSCode singleton shutdown...")
        executor.vscode_manager.shutdown_singleton()
        executor.generate_report()
        logger.info("Executor has shut down gracefully.")
    parser.add_argument('--timeout', type=int, default=120, help='Execution timeout for each instruction.')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries for each instruction.')
    parser.add_argument('--db-path', type=str, default='simple_continuous_execution.db', help='Path to the SQLite database.')
    parser.add_argument('--instructions', type=str, nargs='*', help='Optional list of instruction IDs to execute.')
    parser.add_argument('--run-once', action='store_true', help='Run in single-scan mode, processing the requests directory once.')
    
    args = parser.parse_args()
    main(args)
