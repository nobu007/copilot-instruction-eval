#!/usr/bin/env python3
"""
Simple VSCode Copilot Continuous Execution System

This system leverages the completed VSCode extension to provide continuous,
automated execution of GitHub Copilot instructions with internal API reliability.
Simplified version without pandas dependency.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import requests

# Import the safe process manager
# Add workspace to sys.path to allow module import
sys.path.append(os.path.join(os.path.dirname(__file__), 'workspace', 'src'))
from vscode_process_manager import VSCodeProcessManager


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
    request_id: str
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
    
    def __init__(self, config: Dict[str, Any], vscode_manager: VSCodeProcessManager, logger):
        """Initialize the continuous executor"""
        self.config = config
        self.vscode_manager = vscode_manager
        self.logger = logger
        self.execution_timeout = config.get('execution_timeout', 60)
        self.extension_path = vscode_manager.extension_path

        # Initialize database
        self.db_path = config.get('db_path', 'simple_continuous_execution.db')
        self._setup_database()
        
        # Load instructions
        self.instructions = self._load_instructions()
        
        # Execution state
        self.results: List[ExecutionResult] = []

        self.logger.info(f"🚀 Simple VSCode Copilot Continuous Executor initialized")
        self.logger.info(f"📁 Extension path: {self.extension_path}")
        self.logger.info(f"📊 Database: {self.db_path}")

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
        self.logger.info("Waiting for VSCode extension to become ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            ping_id = f"ping_{uuid.uuid4()}"
            request_filepath = os.path.join(self.config['request_dir'], f"{ping_id}.json")
            response_filepath = os.path.join(self.config['response_dir'], f"{ping_id}.json")

            try:
                ping_request = self._create_request(ping_id, "ping", ExecutionMode.AGENT, "health-check", {})
                with open(request_filepath, 'w', encoding='utf-8') as f:
                    json.dump(ping_request, f)
                self.logger.info(f"Ping request {ping_id} sent.")

                pong_wait_start = time.time()
                while time.time() - pong_wait_start < 10:
                    if os.path.exists(response_filepath):
                        try:
                            with open(response_filepath, 'r', encoding='utf-8') as f:
                                response_data = json.load(f)
                            
                            if response_data.get("response_id") == ping_id and response_data.get("status") == "pong":
                                self.logger.info(f"✅ Pong received for {ping_id}. Extension is ready.")
                                try:
                                    os.remove(request_filepath)
                                    os.remove(response_filepath)
                                except OSError as e:
                                    self.logger.warning(f"Error cleaning up IPC files for ping {ping_id}: {e}")
                                return
                        except (json.JSONDecodeError, KeyError) as e:
                            self.logger.warning(f"Error decoding or processing pong response for {ping_id}: {e}")
                        except Exception as e:
                            self.logger.error(f"An unexpected error occurred while checking for pong {ping_id}: {e}")
                    time.sleep(0.5)

                self.logger.warning(f"Pong not received for {ping_id} within 10s. Retrying with new ping.")
            
            finally:
                if os.path.exists(request_filepath):
                    try:
                        os.remove(request_filepath)
                    except OSError as e:
                        self.logger.error(f"Error cleaning up request file {request_filepath}: {e}")

        self.logger.error("❌ Global timeout. Timed out waiting for VSCode extension to become ready.")
        raise TimeoutError("VSCode extension did not become ready in time.")

    def _setup_database(self):
        """Setup SQLite database for storing execution results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instruction_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
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
            self.logger.info(f"📊 Database initialized: {self.db_path}")
        except Exception as e:
            self.logger.error(f"❌ Database setup failed: {e}")
            raise

    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from JSON file"""
        try:
            instructions_file = os.path.join(os.path.dirname(__file__), 'instructions.json')
            with open(instructions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get('instructions', [])
                self.logger.info(f"📝 Loaded {len(instructions)} instructions")
                return instructions
        except Exception as e:
            self.logger.error(f"❌ Failed to load instructions: {e}")
            return []

    def execute_instruction(self, instruction: Dict[str, Any], mode: ExecutionMode, model: str) -> ExecutionResult:
        """Executes a single instruction by writing a request and polling for a response."""
        request_id = f"{instruction['id']}_{uuid.uuid4()}"
        instruction_text = instruction.get('description', '')
        request_filepath = os.path.join(self.config['request_dir'], f"{request_id}.json")
        response_filepath = os.path.join(self.config['response_dir'], f"{request_id}.json")
        start_time = time.time()

        try:
            request_data = self._create_request(request_id, instruction, mode, model, instruction.get('params', {}))
            with open(request_filepath, 'w', encoding='utf-8') as f:
                json.dump(request_data, f)
            self.logger.info(f"Request {request_id} sent for instruction '{instruction['id']}'.")

            while time.time() - start_time < self.execution_timeout:
                if os.path.exists(response_filepath):
                    try:
                        with open(response_filepath, 'r', encoding='utf-8') as f:
                            response_data = json.load(f)
                        
                        exec_time = time.time() - start_time
                        self.logger.info(f"Response {request_id} received in {exec_time:.2f}s.")
                        
                        status = ExecutionStatus.SUCCESS if response_data.get('status') == 'success' else ExecutionStatus.FAILED
                        response_content = json.dumps(response_data.get('response', ''))

                        return ExecutionResult(
                            instruction_id=instruction['id'], instruction_text=instruction_text, mode=mode, model=model,
                            response=response_content, execution_time=exec_time, status=status, timestamp=datetime.now()
                        )
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.error(f"Error decoding response {request_id}: {e}")
                        return ExecutionResult(
                            instruction_id=instruction['id'], instruction_text=instruction_text, mode=mode, model=model,
                            response="", execution_time=time.time() - start_time, status=ExecutionStatus.ERROR,
                            timestamp=datetime.now(), error_message=f"JSON decode error: {e}"
                        )
                time.sleep(0.5)

            self.logger.warning(f"Timeout for request {request_id} after {self.execution_timeout}s.")
            return ExecutionResult(
                instruction_id=instruction['id'], instruction_text=instruction_text, mode=mode, model=model,
                response="", execution_time=self.execution_timeout, status=ExecutionStatus.TIMEOUT,
                timestamp=datetime.now(), error_message="Execution timed out."
            )
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred during execution of {instruction['id']}: {e}", exc_info=True)
            return ExecutionResult(
                instruction_id=instruction['id'], instruction_text=instruction_text, mode=mode, model=model,
                response="", execution_time=time.time() - start_time, status=ExecutionStatus.ERROR,
                timestamp=datetime.now(), error_message=str(e)
            )
        finally:
            if os.path.exists(request_filepath):
                try:
                    os.remove(request_filepath)
                except OSError as e:
                    self.logger.warning(f"Could not remove request file {request_filepath}: {e}")
            if os.path.exists(response_filepath):
                try:
                    os.remove(response_filepath)
                except OSError as e:
                    self.logger.warning(f"Could not remove response file {response_filepath}: {e}")

    def _save_result(self, result: ExecutionResult):
        """Save execution result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO execution_results 
                (instruction_id, request_id, instruction_text, mode, model, response, 
                 execution_time, status, timestamp, error_message, metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.instruction_id,
                result.request_id if hasattr(result, 'request_id') else f"req_{result.instruction_id}",
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
            self.logger.error(f"❌ Failed to save result: {e}")

    def generate_report(self):
        """Generate a summary report of the execution results"""
        if not self.results:
            self.logger.info("No results to generate a report.")
            return

        total_executions = len(self.results)
        success_count = sum(1 for r in self.results if r.status == ExecutionStatus.SUCCESS)
        failed_count = sum(1 for r in self.results if r.status != ExecutionStatus.SUCCESS)
        avg_exec_time = sum(r.execution_time for r in self.results) / total_executions if total_executions > 0 else 0

        self.logger.info("\n--- Execution Report ---")
        self.logger.info(f"Total Executions: {total_executions}")
        self.logger.info(f"  - Success: {success_count}")
        self.logger.info(f"  - Failed:  {failed_count}")
        self.logger.info(f"Average Execution Time: {avg_exec_time:.2f} seconds")
        self.logger.info("----------------------\n")


def main():
    """Main function to set up and run the executor."""
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
    
    parser = argparse.ArgumentParser(description="Simple, Unified VSCode Copilot Executor")
    parser.add_argument('--run-once', action='store_true', help='Run the executor once and exit.')
    parser.add_argument('--mode', type=str, choices=['agent', 'chat'], default='agent', help='Execution mode for Copilot.')
    parser.add_argument('--model', type=str, default='copilot/gpt-4', help='Model to use for execution.')
    parser.add_argument('--timeout', type=int, default=120, help='Execution timeout for each instruction.')
    parser.add_argument('--db-path', type=str, default='simple_continuous_execution.db', help='Path to the SQLite database.')
    args = parser.parse_args()

    config = {
        'db_path': args.db_path,
        'execution_timeout': args.timeout,
        'request_dir': '/tmp/copilot-evaluation/requests',
        'response_dir': '/tmp/copilot-evaluation/responses'
    }

    vscode_manager = None
    executor = None
    try:
        extension_path = '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension'
        vscode_manager = VSCodeProcessManager(
            workspace_path=os.path.dirname(__file__),
            extension_path=extension_path
        )
        logger.info("Ensuring VSCode singleton is running...")
        vscode_manager.ensure_singleton_running()
        pid, _ = vscode_manager.get_status()
        logger.info(f"✅ VSCode is running with PID: {pid}")

        executor = SimpleCopilotExecutor(config, vscode_manager, logger)
        executor._wait_for_extension_ready()

        execution_mode_log = "Run-Once" if args.run_once else "Continuous"
        logger.info(f"=================================================")
        logger.info(f"  Starting Copilot Executor in {execution_mode_log} Mode")
        logger.info(f"=================================================")

        for instruction in executor.instructions:
            result = executor.execute_instruction(
                instruction,
                mode=ExecutionMode(args.mode),
                model=args.model
            )
            executor.results.append(result)
            executor._save_result(result)
        
        logger.info("All instructions processed.")

    except (KeyboardInterrupt, TimeoutError) as e:
        logger.warning(f"🛑 Execution interrupted or timed out: {e}")
    except Exception as e:
        logger.critical(f"❌ A critical error occurred in the main execution block: {e}", exc_info=True)
    finally:
        if vscode_manager:
            logger.info("Execution finished or interrupted. Requesting VSCode singleton shutdown...")
            vscode_manager.shutdown_singleton()
        if executor:
            executor.generate_report()
            logger.info("Executor has shut down gracefully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # This will catch errors during initial setup, before the main try-block
        # Note: logger might not be initialized here if basicConfig fails.
        print(f"❌ An unrecoverable error occurred during startup: {e}", file=sys.stderr)
        # Attempt to log, but it may fail
        try:
            logging.getLogger(__name__).critical(f"❌ An unrecoverable error occurred during startup: {e}", exc_info=True)
        except:
            pass
        sys.exit(1)