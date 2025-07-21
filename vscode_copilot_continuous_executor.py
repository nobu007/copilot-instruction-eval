"""
VSCode Copilot Continuous Execution System

This system leverages the completed VSCode extension to provide continuous,
automated execution of GitHub Copilot instructions with internal API reliability.

Key Features:
- Integration with VSCode Copilot Automation Extension
- Continuous execution of instruction sets
- Real-time monitoring and logging
- Performance metrics and evaluation
- Agent Mode and Chat Mode support
"""

import json
import os
import sys
import time
import logging
import subprocess
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests
from dataclasses import dataclass
from enum import Enum
import sqlite3
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('continuous_execution.log')
    ]
)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for Copilot"""
    AGENT = "agent"
    CHAT = "chat"


class ExecutionStatus(Enum):
    """Status of instruction execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


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


class VSCodeCopilotExecutor:
    """
    Main executor class that integrates with VSCode extension
    for continuous Copilot instruction execution
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the continuous executor"""
        self.config = config
        self.extension_path = config.get('extension_path', 
            '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension')
        self.vscode_command = config.get('vscode_command', 'code')
        self.execution_timeout = config.get('execution_timeout', 60)  # seconds
        self.retry_attempts = config.get('retry_attempts', 3)
        
        # Initialize database
        self.db_path = config.get('db_path', 'continuous_execution.db')
        self._setup_database()
        
        # Load instructions
        self.instructions = self._load_instructions()
        
        # Execution state
        self.current_execution: Optional[ExecutionResult] = None
        self.execution_queue: List[Dict[str, Any]] = []
        self.results: List[ExecutionResult] = []
        
        logger.info(f"🚀 VSCode Copilot Continuous Executor initialized")
        logger.info(f"📁 Extension path: {self.extension_path}")
        logger.info(f"📊 Database: {self.db_path}")
    
    def _setup_database(self):
        """Setup SQLite database for storing execution results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
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
        logger.info("✅ Database setup completed")
    
    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from JSON file"""
        instructions_file = self.config.get('instructions_file', 'instructions.json')
        
        try:
            with open(instructions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                instructions = data.get('instructions', [])
                logger.info(f"📋 Loaded {len(instructions)} instructions")
                return instructions
        except Exception as e:
            logger.error(f"❌ Failed to load instructions: {e}")
            return []
    
    def _ensure_extension_installed(self) -> bool:
        """Ensure VSCode extension is installed and ready"""
        try:
            # Check if extension directory exists
            if not os.path.exists(self.extension_path):
                logger.error(f"❌ Extension path not found: {self.extension_path}")
                return False
            
            # Try to install/update extension
            install_cmd = f"cd {self.extension_path} && make install"
            result = subprocess.run(install_cmd, shell=True, 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✅ VSCode extension installed/updated successfully")
                return True
            else:
                logger.error(f"❌ Extension installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Extension setup error: {e}")
            return False
    
    def _execute_vscode_command(self, command: str, args: Optional[str] = None) -> Tuple[bool, str]:
        """Execute VSCode command via extension"""
        try:
            # Use VSCode CLI to execute extension commands
            if args:
                cmd = f'{self.vscode_command} --command "{command}" --args "{args}"'
            else:
                cmd = f'{self.vscode_command} --command "{command}"'
            
            logger.info(f"🔧 Executing: {cmd}")
            
            result = subprocess.run(cmd, shell=True, 
                                  capture_output=True, text=True, 
                                  timeout=self.execution_timeout)
            
            if result.returncode == 0:
                logger.info(f"✅ Command executed successfully")
                return True, result.stdout
            else:
                logger.error(f"❌ Command failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Command timeout: {command}")
            return False, "Command timeout"
        except Exception as e:
            logger.error(f"❌ Command execution error: {e}")
            return False, str(e)
    
    def _send_prompt_to_copilot(self, prompt: str, mode: ExecutionMode, 
                               model: str) -> Tuple[bool, str, float]:
        """Send prompt to Copilot via VSCode extension"""
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Sending prompt to Copilot (Mode: {mode.value}, Model: {model})")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            
            # Step 1: Switch to specified mode
            logger.info(f"⚙️ Switching to {mode.value} mode...")
            mode_command = "copilot-automation.switchMode"
            success, error = self._execute_vscode_command(mode_command, mode.value)
            if not success:
                logger.warning(f"⚠️ Mode switch failed: {error}")
            
            # Step 2: Select model
            logger.info(f"🤖 Selecting model: {model}...")
            model_command = "copilot-automation.selectModel"
            success, error = self._execute_vscode_command(model_command, model)
            if not success:
                logger.warning(f"⚠️ Model selection failed: {error}")
            
            # Step 3: Execute batch prompt with the actual prompt text
            logger.info(f"💬 Executing batch prompt...")
            prompt_command = "copilot-automation.executeBatchPrompt"
            success, response = self._execute_vscode_command(prompt_command, prompt)
            
            execution_time = time.time() - start_time
            
            if success:
                logger.info(f"✅ Prompt executed successfully in {execution_time:.2f}s")
                
                # Try to read the execution result file
                result_file = self._get_execution_result_file()
                if result_file and os.path.exists(result_file):
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            if result_data.get('success'):
                                response = result_data.get('response', response)
                                logger.info(f"📄 Retrieved response from result file")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to read result file: {e}")
                
                return True, response, execution_time
            else:
                logger.error(f"❌ Prompt execution failed: {response}")
                return False, response, execution_time
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Prompt execution error: {e}")
            return False, str(e), execution_time
    
    def _get_execution_result_file(self) -> Optional[str]:
        """Get the path to the execution result file"""
        try:
            # Try workspace folder first
            if hasattr(self, 'workspace_folder') and self.workspace_folder:
                result_file = os.path.join(self.workspace_folder, '.vscode', 'copilot-automation', 'execution_result.json')
                if os.path.exists(result_file):
                    return result_file
            
            # Fallback to current directory
            result_file = os.path.join(os.getcwd(), '.vscode', 'copilot-automation', 'execution_result.json')
            if os.path.exists(result_file):
                return result_file
                
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error getting result file path: {e}")
            return None
    
    def execute_instruction(self, instruction: Dict[str, Any], 
                          mode: ExecutionMode = ExecutionMode.AGENT,
                          model: str = "copilot/gpt-4.1") -> ExecutionResult:
        """Execute a single instruction"""
        instruction_id = instruction.get('id', 'unknown')
        instruction_text = instruction.get('description', '')
        
        logger.info(f"🎯 Executing instruction: {instruction_id}")
        logger.info(f"📝 Text: {instruction_text[:100]}...")
        
        # Create execution result
        result = ExecutionResult(
            instruction_id=instruction_id,
            instruction_text=instruction_text,
            mode=mode,
            model=model,
            response="",
            execution_time=0.0,
            status=ExecutionStatus.RUNNING,
            timestamp=datetime.now()
        )
        
        self.current_execution = result
        
        try:
            # Execute with retry mechanism
            for attempt in range(self.retry_attempts):
                logger.info(f"🔄 Attempt {attempt + 1}/{self.retry_attempts}")
                
                success, response, exec_time = self._send_prompt_to_copilot(
                    instruction_text, mode, model
                )
                
                if success:
                    result.response = response
                    result.execution_time = exec_time
                    result.status = ExecutionStatus.COMPLETED
                    logger.info(f"✅ Instruction completed: {instruction_id}")
                    break
                else:
                    result.error_message = response
                    if attempt == self.retry_attempts - 1:
                        result.status = ExecutionStatus.FAILED
                        logger.error(f"❌ Instruction failed: {instruction_id}")
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            logger.error(f"❌ Instruction execution error: {e}")
        
        # Save result
        self._save_result(result)
        self.results.append(result)
        self.current_execution = None
        
        return result
    
    def _save_result(self, result: ExecutionResult):
        """Save execution result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO executions 
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
            logger.debug(f"💾 Result saved: {result.instruction_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save result: {e}")
    
    def run_continuous_execution(self, 
                                mode: ExecutionMode = ExecutionMode.AGENT,
                                model: str = "copilot/gpt-4.1",
                                instruction_filter: Optional[List[str]] = None) -> List[ExecutionResult]:
        """Run continuous execution of all instructions"""
        
        logger.info("🚀 Starting continuous execution...")
        logger.info(f"⚙️ Mode: {mode.value}")
        logger.info(f"🤖 Model: {model}")
        
        # Ensure extension is ready
        if not self._ensure_extension_installed():
            logger.error("❌ Extension setup failed, aborting execution")
            return []
        
        # Filter instructions if specified
        instructions_to_execute = self.instructions
        if instruction_filter:
            instructions_to_execute = [
                inst for inst in self.instructions 
                if inst.get('id') in instruction_filter
            ]
        
        logger.info(f"📋 Executing {len(instructions_to_execute)} instructions")
        
        results = []
        
        for i, instruction in enumerate(instructions_to_execute):
            logger.info(f"📊 Progress: {i+1}/{len(instructions_to_execute)}")
            
            result = self.execute_instruction(instruction, mode, model)
            results.append(result)
            
            # Brief pause between executions
            time.sleep(2)
        
        logger.info("🎉 Continuous execution completed!")
        logger.info(f"✅ Successful: {sum(1 for r in results if r.status == ExecutionStatus.COMPLETED)}")
        logger.info(f"❌ Failed: {sum(1 for r in results if r.status == ExecutionStatus.FAILED)}")
        
        return results
    
    def generate_execution_report(self) -> str:
        """Generate execution report"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM executions ORDER BY timestamp DESC", conn)
            conn.close()
            
            if df.empty:
                return "No execution data available."
            
            # Generate basic statistics
            total_executions = len(df)
            successful = len(df[df['status'] == 'completed'])
            failed = len(df[df['status'] == 'failed'])
            avg_execution_time = df['execution_time'].mean()
            
            report = f"""
# VSCode Copilot Continuous Execution Report

## Summary
- **Total Executions**: {total_executions}
- **Successful**: {successful} ({successful/total_executions*100:.1f}%)
- **Failed**: {failed} ({failed/total_executions*100:.1f}%)
- **Average Execution Time**: {avg_execution_time:.2f}s

## Recent Executions
{df.head(10).to_string(index=False)}

Generated at: {datetime.now().isoformat()}
"""
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return f"Report generation failed: {e}"


def main():
    """Main function for continuous execution"""
    config = {
        'extension_path': '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
        'instructions_file': 'instructions.json',
        'execution_timeout': 60,
        'retry_attempts': 3,
        'db_path': 'continuous_execution.db'
    }
    
    executor = VSCodeCopilotExecutor(config)
    
    # Run continuous execution
    results = executor.run_continuous_execution(
        mode=ExecutionMode.AGENT,
        model="copilot/gpt-4.1"
    )
    
    # Generate and save report
    report = executor.generate_execution_report()
    with open('continuous_execution_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info("📄 Report saved to continuous_execution_report.md")


if __name__ == "__main__":
    main()
