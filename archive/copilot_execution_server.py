"""
VSCode Copilot Execution Server

Single-instance server that manages VSCode Copilot operations.
Prevents multiple VSCode instances and provides centralized execution control.

Architecture:
- Single VSCode instance with extension loaded
- HTTP API server for receiving execution requests
- Queue-based sequential execution
- Persistent Copilot session management
"""

import json
import os
import sys
import time
import logging
import subprocess
import threading
import queue
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, request, jsonify
import sqlite3
import uuid
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('copilot_server.log')
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
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionRequest:
    """Request for instruction execution"""
    request_id: str
    instruction_text: str
    mode: ExecutionMode
    model: str
    timeout: int = 60
    priority: int = 0
    client_id: str = "default"


@dataclass
class ExecutionResult:
    """Result of instruction execution"""
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


class VSCodeManager:
    """Manages single VSCode instance with extension"""
    
    def __init__(self, extension_path: str, vscode_command: str = "code"):
        self.extension_path = extension_path
        self.vscode_command = vscode_command
        self.vscode_process = None
        self.extension_ready = False
        self.lock = threading.Lock()
        
    def start_vscode(self) -> bool:
        """Start VSCode with extension if not already running"""
        with self.lock:
            if self.is_vscode_running():
                logger.info("VSCode already running, reusing instance")
                return True
                
            try:
                # Kill any existing VSCode processes to ensure clean start
                self._kill_existing_vscode()
                
                # Start VSCode with extension
                cmd = [
                    self.vscode_command,
                    "--install-extension", f"{self.extension_path}/copilot-automation-extension-0.0.1.vsix",
                    "--new-window",
                    "--disable-workspace-trust"
                ]
                
                logger.info(f"Starting VSCode: {' '.join(cmd)}")
                self.vscode_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.extension_path
                )
                
                # Wait for VSCode to start and extension to load
                time.sleep(5)
                
                # Verify extension is loaded
                if self._verify_extension_ready():
                    self.extension_ready = True
                    logger.info("✅ VSCode started with extension loaded")
                    return True
                else:
                    logger.error("❌ Extension failed to load")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to start VSCode: {e}")
                return False
    
    def _kill_existing_vscode(self):
        """Kill existing VSCode processes"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'code' in proc.info['name'].lower():
                    if proc.info['cmdline'] and any('vscode' in arg.lower() or 'code' in arg.lower() for arg in proc.info['cmdline']):
                        logger.info(f"Killing existing VSCode process: {proc.info['pid']}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(2)  # Wait for processes to terminate
    
    def is_vscode_running(self) -> bool:
        """Check if VSCode is running"""
        return self.vscode_process is not None and self.vscode_process.poll() is None
    
    def _verify_extension_ready(self) -> bool:
        """Verify that the extension is ready"""
        # Try to execute a simple extension command
        try:
            result = subprocess.run([
                self.vscode_command,
                "--list-extensions"
            ], capture_output=True, text=True, timeout=10)
            
            return "copilot-automation-extension" in result.stdout
        except Exception as e:
            logger.error(f"Failed to verify extension: {e}")
            return False
    
    def execute_copilot_command(self, prompt: str, mode: ExecutionMode, model: str) -> Tuple[bool, str]:
        """Execute Copilot command via extension"""
        if not self.extension_ready:
            return False, "Extension not ready"
            
        try:
            # Create command file for extension
            command_data = {
                "prompt": prompt,
                "mode": mode.value,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
            
            command_file = os.path.join(self.extension_path, "command.json")
            with open(command_file, 'w') as f:
                json.dump(command_data, f, indent=2)
            
            # Execute via VSCode command
            result = subprocess.run([
                self.vscode_command,
                "--command", "copilot-automation.executePrompt"
            ], capture_output=True, text=True, timeout=60)
            
            # Read result file
            result_file = os.path.join(self.extension_path, "result.json")
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                return True, result_data.get("response", "No response")
            else:
                return False, "No result file generated"
                
        except Exception as e:
            logger.error(f"Failed to execute Copilot command: {e}")
            return False, str(e)


class CopilotExecutionServer:
    """Main server class for managing Copilot executions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vscode_manager = VSCodeManager(
            config.get('extension_path', '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension'),
            config.get('vscode_command', 'code')
        )
        
        # Execution queue and state
        self.execution_queue = queue.PriorityQueue()
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.completed_executions: Dict[str, ExecutionResult] = {}
        
        # Database
        self.db_path = config.get('db_path', 'copilot_server.db')
        self._setup_database()
        
        # Worker thread
        self.worker_thread = None
        self.running = False
        
        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()
        
        logger.info("🚀 Copilot Execution Server initialized")
    
    def _setup_database(self):
        """Setup SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                request_id TEXT PRIMARY KEY,
                instruction_text TEXT,
                mode TEXT,
                model TEXT,
                response TEXT,
                execution_time REAL,
                status TEXT,
                timestamp TEXT,
                error_message TEXT,
                client_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "healthy",
                "vscode_running": self.vscode_manager.is_vscode_running(),
                "extension_ready": self.vscode_manager.extension_ready,
                "queue_size": self.execution_queue.qsize(),
                "active_executions": len(self.active_executions)
            })
        
        @self.app.route('/execute', methods=['POST'])
        def execute():
            try:
                data = request.json
                
                # Create execution request
                req = ExecutionRequest(
                    request_id=str(uuid.uuid4()),
                    instruction_text=data['instruction'],
                    mode=ExecutionMode(data.get('mode', 'agent')),
                    model=data.get('model', 'copilot/gpt-4.1'),
                    timeout=data.get('timeout', 60),
                    priority=data.get('priority', 0),
                    client_id=data.get('client_id', 'default')
                )
                
                # Add to queue
                self.execution_queue.put((req.priority, req))
                
                logger.info(f"📝 Queued execution request: {req.request_id}")
                
                return jsonify({
                    "request_id": req.request_id,
                    "status": "queued",
                    "queue_position": self.execution_queue.qsize()
                })
                
            except Exception as e:
                logger.error(f"Failed to queue execution: {e}")
                return jsonify({"error": str(e)}), 400
        
        @self.app.route('/status/<request_id>', methods=['GET'])
        def get_status(request_id):
            if request_id in self.active_executions:
                result = self.active_executions[request_id]
                return jsonify({
                    "request_id": request_id,
                    "status": "running",
                    "started_at": result.timestamp.isoformat()
                })
            elif request_id in self.completed_executions:
                result = self.completed_executions[request_id]
                return jsonify({
                    "request_id": result.request_id,
                    "instruction_text": result.instruction_text,
                    "mode": result.mode.value,
                    "model": result.model,
                    "response": result.response,
                    "execution_time": result.execution_time,
                    "status": result.status.value,
                    "timestamp": result.timestamp.isoformat(),
                    "error_message": result.error_message
                })
            else:
                return jsonify({"error": "Request not found"}), 404
        
        @self.app.route('/results', methods=['GET'])
        def get_results():
            limit = request.args.get('limit', 100, type=int)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM executions 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "request_id": row[0],
                    "instruction_text": row[1],
                    "mode": row[2],
                    "model": row[3],
                    "response": row[4],
                    "execution_time": row[5],
                    "status": row[6],
                    "timestamp": row[7],
                    "error_message": row[8],
                    "client_id": row[9]
                })
            
            conn.close()
            return jsonify(results)
    
    def start_server(self, host: str = "127.0.0.1", port: int = 5000):
        """Start the server"""
        # Start VSCode
        if not self.vscode_manager.start_vscode():
            logger.error("❌ Failed to start VSCode, server cannot start")
            return False
        
        # Start worker thread
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.start()
        
        logger.info(f"🌐 Starting server on {host}:{port}")
        
        # Start Flask app
        self.app.run(host=host, port=port, debug=False, threaded=True)
        
        return True
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
        logger.info("🛑 Server stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing execution queue"""
        logger.info("🔄 Worker thread started")
        
        while self.running:
            try:
                # Get next execution request (blocking with timeout)
                try:
                    priority, req = self.execution_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Execute the request
                self._execute_request(req)
                
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(1)
        
        logger.info("🔄 Worker thread stopped")
    
    def _execute_request(self, req: ExecutionRequest):
        """Execute a single request"""
        start_time = time.time()
        
        # Create initial result
        result = ExecutionResult(
            request_id=req.request_id,
            instruction_text=req.instruction_text,
            mode=req.mode,
            model=req.model,
            response="",
            execution_time=0.0,
            status=ExecutionStatus.RUNNING,
            timestamp=datetime.now()
        )
        
        self.active_executions[req.request_id] = result
        
        logger.info(f"🚀 Executing request: {req.request_id}")
        
        try:
            # Execute via VSCode manager
            success, response = self.vscode_manager.execute_copilot_command(
                req.instruction_text, req.mode, req.model
            )
            
            # Update result
            result.response = response
            result.execution_time = time.time() - start_time
            result.status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
            
            if not success:
                result.error_message = response
            
            logger.info(f"✅ Completed request: {req.request_id} ({result.status.value})")
            
        except Exception as e:
            result.execution_time = time.time() - start_time
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            logger.error(f"❌ Failed request: {req.request_id} - {e}")
        
        # Move to completed
        self.completed_executions[req.request_id] = result
        del self.active_executions[req.request_id]
        
        # Save to database
        self._save_result(result)
    
    def _save_result(self, result: ExecutionResult):
        """Save result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO executions 
            (request_id, instruction_text, mode, model, response, 
             execution_time, status, timestamp, error_message, client_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.request_id,
            result.instruction_text,
            result.mode.value,
            result.model,
            result.response,
            result.execution_time,
            result.status.value,
            result.timestamp.isoformat(),
            result.error_message,
            "server"  # Default client_id for server executions
        ))
        
        conn.commit()
        conn.close()


def main():
    """Main function"""
    config = {
        'extension_path': '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
        'vscode_command': 'code',
        'db_path': 'copilot_server.db'
    }
    
    server = CopilotExecutionServer(config)
    
    try:
        server.start_server(host="127.0.0.1", port=5000)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down server...")
        server.stop_server()


if __name__ == "__main__":
    main()
