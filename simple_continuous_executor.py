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
        self.retry_attempts = config.get('retry_attempts', 3)
        
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
            "category": params.get("category", "general"),
            "retry_count": params.get("retry_count", 0),
            "max_retries": self.retry_attempts
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
        """Send prompt to Copilot via file-based IPC and wait for response."""
        base_dir = '/tmp/copilot-evaluation'
        requests_dir = os.path.join(base_dir, 'requests')
        responses_dir = os.path.join(base_dir, 'responses')
        processed_dir = os.path.join(base_dir, 'processed')
        failed_dir = os.path.join(base_dir, 'failed')
        timed_out_dir = os.path.join(base_dir, 'timed_out')

        for d in [requests_dir, responses_dir, processed_dir, failed_dir, timed_out_dir]:
            os.makedirs(d, exist_ok=True)

        request_id = instruction['id']
        request_file = os.path.join(requests_dir, f"{request_id}.json")
        execution_start_time = time.time()

        try:
            instruction_text = instruction.get('description', '')
            params = instruction.get('params', {})
            req = self._create_request(request_id, instruction_text, mode, model, instruction.get('params', {}))
            
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(req, f, indent=2)
            
            logger.info(f"Request file created: {request_file}")
            
            result_file = os.path.join(responses_dir, f"{request_id}.json")
            timeout_end = time.time() + self.execution_timeout
            
            while time.time() < timeout_end:
                if os.path.exists(result_file):
                    execution_time = time.time() - execution_start_time
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                        
                        if result_data.get('success'):
                            response = result_data.get('response', 'No response content found.')
                            logger.info(f"Successfully received response for {request_id}")
                            os.rename(request_file, os.path.join(processed_dir, os.path.basename(request_file)))
                            os.remove(result_file)
                            return ExecutionStatus.SUCCESS, response, execution_time
                        else:
                            error_message = result_data.get('error_message', 'Unknown error from extension')
                            logger.error(f"Extension reported failure for {request_id}: {error_message}")
                            os.rename(request_file, os.path.join(failed_dir, os.path.basename(request_file)))
                            os.remove(result_file)
                            return ExecutionStatus.FAILED, error_message, execution_time

                    except (json.JSONDecodeError, Exception) as e:
                        logger.error(f"Error processing result file for {request_id}: {e}")
                        os.rename(request_file, os.path.join(failed_dir, os.path.basename(request_file)))
                        if os.path.exists(result_file):
                            os.remove(result_file)
                        return ExecutionStatus.ERROR, f"Error processing result: {e}", execution_time
                time.sleep(1)
            
            logger.warning(f"Timeout waiting for extension response for request {request_id}")
            os.rename(request_file, os.path.join(timed_out_dir, os.path.basename(request_file)))
            return ExecutionStatus.TIMEOUT, "Timeout waiting for extension response", self.execution_timeout

        except Exception as e:
            execution_time = time.time() - execution_start_time
            logger.error(f"❌ An unexpected error occurred in _send_prompt_to_copilot: {e}")
            if os.path.exists(request_file):
                os.rename(request_file, os.path.join(failed_dir, os.path.basename(request_file)))
            return ExecutionStatus.ERROR, f"Unexpected error in send_prompt: {e}", execution_time

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

    def run(self, 
            mode: ExecutionMode = ExecutionMode.AGENT,
            model: str = "copilot/gpt-4",
            instruction_filter: Optional[List[str]] = None):
        """Run continuous execution of all instructions."""
        
        instructions_to_execute = self.instructions
        if instruction_filter:
            instructions_to_execute = [
                inst for inst in self.instructions 
                if inst.get('id') in instruction_filter
            ]
        
        logger.info(f"📋 Executing {len(instructions_to_execute)} instructions")
        
        for i, instruction in enumerate(instructions_to_execute, 1):
            logger.info(f"[INSTRUCTION {i}/{len(instructions_to_execute)}]")
            self.execute_instruction(instruction, mode, model)
            logger.info(f"[INSTRUCTION {i}/{len(instructions_to_execute)} COMPLETE]")
            
            if i < len(instructions_to_execute):
                logger.info("--- Pausing for 2 seconds ---")
                self.execution_completed = True
        logger.info("All instructions processed.")

    def run_once(self, mode: ExecutionMode = ExecutionMode.AGENT, model: str = "copilot/gpt-4"):
        """Scans the request directory and processes each request file once."""
        request_dir = self.config.get('request_dir', '/tmp/copilot-evaluation/requests')
        failed_dir = os.path.join(os.path.dirname(request_dir), 'failed')
        os.makedirs(failed_dir, exist_ok=True)

        logger.info(f"Scanning for requests in {request_dir}")
        request_files = [f for f in os.listdir(request_dir) if f.endswith('.json')]

        if not request_files:
            logger.info("No new requests found.")
            return

        for filename in request_files:
            filepath = os.path.join(request_dir, filename)
            logger.info(f"Processing request file: {filepath}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    instruction = json.load(f)
                # Basic validation
                if 'request_id' not in instruction or 'instruction' not in instruction:
                    raise ValueError("Request missing required fields 'request_id' or 'instruction'")
                
                self.execute_instruction(instruction, mode, model)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in {filepath}. Moving to 'failed' directory.")
                shutil.move(filepath, os.path.join(failed_dir, filename))
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid request data in {filepath}: {e}. Moving to 'failed' directory.")
                shutil.move(filepath, os.path.join(failed_dir, filename))
            except Exception as e:
                logger.critical(f"An unexpected error occurred while processing {filepath}: {e}", exc_info=True)
                shutil.move(filepath, os.path.join(failed_dir, filename))
        
        logger.info("Finished processing all files in the request directory.")

    def generate_report(self):
        """Generate execution report"""
        try:
            total_instructions = len(self.results)
            if total_instructions == 0:
                logger.info("No results to generate a report.")
                return

            successful = len([r for r in self.results if r.status == ExecutionStatus.SUCCESS])
            failed = len([r for r in self.results if r.status == ExecutionStatus.FAILED])
            errors = len([r for r in self.results if r.status == ExecutionStatus.ERROR])
            
            avg_execution_time = sum(r.execution_time for r in self.results) / total_instructions if total_instructions > 0 else 0
            success_rate = (successful / total_instructions * 100) if total_instructions > 0 else 0
            
            report = f"""
# Simple Continuous Execution Report

## Summary
- **Total Instructions**: {total_instructions}
- **Successful**: {successful}
- **Failed**: {failed}
- **Errors**: {errors}
- **Success Rate**: {success_rate:.1f}%
- **Average Execution Time**: {avg_execution_time:.2f}s

## Results
"""
            
            for result in self.results:
                report += f"- **{result.instruction_id}**: {result.status.value} ({result.execution_time:.2f}s)\n"
            
            report_file = 'simple_continuous_execution_report.md'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"📊 Report generated: {report_file}")
            print(report)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")

def main(args):
    """Main execution function"""
    config = {
        'extension_path': args.extension_path,
        'vscode_command': args.vscode_command,
        'execution_timeout': args.timeout,
        'retry_attempts': args.retries,
        'db_path': args.db_path
    }
    
    executor = SimpleCopilotExecutor(config)
    
    try:
        logger.info("Ensuring VSCode singleton is running via VSCodeProcessManager...")
        executor.vscode_manager.ensure_singleton_running()

        # Verify the status and get the PID correctly
        pid, is_running = executor.vscode_manager.get_status()
        if not is_running:
            logger.critical("❌ VSCode process is not running after ensuring it started. Aborting.")
            return
        logger.info(f"✅ VSCode Process Manager reports singleton is running with PID: {pid}")

        # Add a hardcoded wait for extension to warm up, addressing the 'cold start' problem.
        logger.info("Waiting 20 seconds for the extension to cold start and initialize...")
        time.sleep(20)

        executor._wait_for_extension_ready()

        if args.run_once:
            executor.run_once()
        else:
            executor.run(instruction_filter=args.instructions)

    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
    finally:
        logger.info("Requesting VSCode singleton shutdown via VSCodeProcessManager...")
        executor.vscode_manager.shutdown_singleton()
        
        executor.generate_report()
        logger.info("Execution finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple VSCode Copilot Continuous Execution System")
    parser.add_argument('--extension-path', type=str, default='/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension', help='Path to the VSCode extension.')
    parser.add_argument('--vscode-command', type=str, default='code', help='The command to run VSCode.')
    parser.add_argument('--timeout', type=int, default=120, help='Execution timeout for each instruction.')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries for each instruction.')
    parser.add_argument('--db-path', type=str, default='simple_continuous_execution.db', help='Path to the SQLite database.')
    parser.add_argument('--instructions', type=str, nargs='*', help='Optional list of instruction IDs to execute.')
    parser.add_argument('--run-once', action='store_true', help='Run in single-scan mode, processing the requests directory once.')
    
    args = parser.parse_args()
    main(args)
