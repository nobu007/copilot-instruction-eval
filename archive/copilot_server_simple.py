"""
Simple Copilot Execution Server

既存のVSCode拡張機能を活用したシンプルなサーバー実装。
標準出力ベースの通信で確実な動作を実現。
"""

import json
import time
import logging
import threading
import queue
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, request, jsonify
import sqlite3
import uuid

from vscode_extension_client import VSCodeExtensionClient, ExecutionMode, ExecutionResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('copilot_server_simple.log')
    ]
)
logger = logging.getLogger(__name__)


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


class SimpleCopilotServer:
    """Simple server using VSCode extension client"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize VSCode extension client
        extension_path = config.get('extension_path', 
            '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension')
        vscode_command = config.get('vscode_command', 'code')
        
        self.extension_client = VSCodeExtensionClient(extension_path, vscode_command)
        
        # Execution queue and state
        self.execution_queue = queue.PriorityQueue()
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.completed_executions: Dict[str, ExecutionResult] = {}
        
        # Database
        self.db_path = config.get('db_path', 'copilot_server_simple.db')
        self._setup_database()
        
        # Worker thread
        self.worker_thread = None
        self.running = False
        
        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()
        
        logger.info("🚀 Simple Copilot Server initialized")
    
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
                success BOOLEAN,
                timestamp TEXT,
                error_message TEXT,
                client_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"📊 Database initialized: {self.db_path}")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            # Test extension connection
            extension_ready = self.extension_client.test_connection()
            
            return jsonify({
                "status": "healthy" if extension_ready else "degraded",
                "extension_ready": extension_ready,
                "queue_size": self.execution_queue.qsize(),
                "active_executions": len(self.active_executions),
                "completed_executions": len(self.completed_executions),
                "timestamp": datetime.now().isoformat()
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
                    model=data.get('model', 'copilot/gpt-4'),
                    timeout=data.get('timeout', 60),
                    priority=data.get('priority', 0),
                    client_id=data.get('client_id', 'default')
                )
                
                # Add to queue (priority queue: lower number = higher priority)
                self.execution_queue.put((req.priority, req))
                
                logger.info(f"📝 Queued execution request: {req.request_id}")
                logger.info(f"   Instruction: {req.instruction_text[:100]}...")
                
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
                    "started_at": result.timestamp
                })
            elif request_id in self.completed_executions:
                result = self.completed_executions[request_id]
                return jsonify({
                    "request_id": request_id,
                    "status": "success" if result.success else "failed",
                    "instruction_text": result.prompt,
                    "response": result.response,
                    "execution_time": result.execution_time,
                    "timestamp": result.timestamp,
                    "error_message": result.error,
                    "model": result.model,
                    "mode": result.mode
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
                    "success": bool(row[6]),
                    "timestamp": row[7],
                    "error_message": row[8],
                    "client_id": row[9]
                })
            
            conn.close()
            return jsonify(results)
    
    def start_server(self, host: str = "127.0.0.1", port: int = 5001):
        """Start the server"""
        
        # Test extension connection
        logger.info("🔍 Testing VSCode extension connection...")
        if not self.extension_client.test_connection():
            logger.warning("⚠️ Extension connection test failed, but starting server anyway")
        else:
            logger.info("✅ Extension connection verified")
        
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
        logger.info(f"🚀 Executing request: {req.request_id}")
        logger.info(f"   Instruction: {req.instruction_text[:100]}...")
        logger.info(f"   Mode: {req.mode.value}")
        logger.info(f"   Model: {req.model}")
        
        # Create placeholder for active execution
        placeholder_result = ExecutionResult(
            success=False,
            prompt=req.instruction_text,
            timestamp=datetime.now().isoformat()
        )
        self.active_executions[req.request_id] = placeholder_result
        
        try:
            # Execute via extension client
            result = self.extension_client.execute_prompt(
                prompt=req.instruction_text,
                timeout=req.timeout,
                model=req.model,
                mode=req.mode
            )
            
            logger.info(f"✅ Completed request: {req.request_id}")
            logger.info(f"   Success: {result.success}")
            logger.info(f"   Execution time: {result.execution_time:.2f}s")
            
            if result.success:
                logger.info(f"   Response length: {len(result.response) if result.response else 0}")
            else:
                logger.info(f"   Error: {result.error}")
            
        except Exception as e:
            logger.error(f"❌ Failed request: {req.request_id} - {e}")
            result = ExecutionResult(
                success=False,
                prompt=req.instruction_text,
                execution_time=0.0,
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
        
        # Move to completed
        self.completed_executions[req.request_id] = result
        del self.active_executions[req.request_id]
        
        # Save to database
        self._save_result(req.request_id, result, req.client_id)
    
    def _save_result(self, request_id: str, result: ExecutionResult, client_id: str):
        """Save result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO executions 
            (request_id, instruction_text, mode, model, response, 
             execution_time, success, timestamp, error_message, client_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_id,
            result.prompt,
            result.mode or "unknown",
            result.model or "unknown",
            result.response,
            result.execution_time,
            result.success,
            result.timestamp,
            result.error,
            client_id
        ))
        
        conn.commit()
        conn.close()


def main():
    """Main function"""
    config = {
        'extension_path': '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
        'vscode_command': 'code',
        'db_path': 'copilot_server_simple.db'
    }
    
    server = SimpleCopilotServer(config)
    
    try:
        server.start_server(host="127.0.0.1", port=5001)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down server...")
        server.stop_server()


if __name__ == "__main__":
    main()
