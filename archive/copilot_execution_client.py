"""
VSCode Copilot Execution Client

Client for communicating with the Copilot Execution Server.
Provides simple API for sending execution requests and monitoring results.
"""

import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for Copilot"""
    AGENT = "agent"
    CHAT = "chat"


class ExecutionStatus(Enum):
    """Status of instruction execution"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResponse:
    """Response from execution request"""
    request_id: str
    status: str
    response: Optional[str] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None


class CopilotExecutionClient:
    """Client for communicating with Copilot Execution Server"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:5000", client_id: str = None):
        self.server_url = server_url.rstrip('/')
        self.client_id = client_id or f"client_{uuid.uuid4().hex[:8]}"
        self.session = requests.Session()
        
        logger.info(f"🔗 Copilot Client initialized: {self.server_url}")
        logger.info(f"🆔 Client ID: {self.client_id}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health status"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def execute_instruction(self, 
                          instruction: str,
                          mode: ExecutionMode = ExecutionMode.AGENT,
                          model: str = "copilot/gpt-4.1",
                          timeout: int = 60,
                          priority: int = 0,
                          wait_for_completion: bool = True,
                          poll_interval: float = 1.0) -> ExecutionResponse:
        """
        Execute a single instruction
        
        Args:
            instruction: The instruction text to execute
            mode: Execution mode (AGENT or CHAT)
            model: Model to use
            timeout: Execution timeout in seconds
            priority: Execution priority (lower = higher priority)
            wait_for_completion: Whether to wait for completion
            poll_interval: Polling interval when waiting
            
        Returns:
            ExecutionResponse with result
        """
        try:
            # Submit execution request
            request_data = {
                "instruction": instruction,
                "mode": mode.value,
                "model": model,
                "timeout": timeout,
                "priority": priority,
                "client_id": self.client_id
            }
            
            logger.info(f"📤 Submitting instruction: {instruction[:100]}...")
            
            response = self.session.post(
                f"{self.server_url}/execute",
                json=request_data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            request_id = result["request_id"]
            
            logger.info(f"✅ Request queued: {request_id}")
            
            if not wait_for_completion:
                return ExecutionResponse(
                    request_id=request_id,
                    status=result["status"]
                )
            
            # Wait for completion
            return self._wait_for_completion(request_id, timeout, poll_interval)
            
        except Exception as e:
            logger.error(f"Failed to execute instruction: {e}")
            return ExecutionResponse(
                request_id="",
                status="failed",
                error_message=str(e)
            )
    
    def get_status(self, request_id: str) -> ExecutionResponse:
        """Get status of a specific request"""
        try:
            response = self.session.get(f"{self.server_url}/status/{request_id}", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            return ExecutionResponse(
                request_id=data.get("request_id", request_id),
                status=data.get("status", "unknown"),
                response=data.get("response"),
                execution_time=data.get("execution_time"),
                error_message=data.get("error_message")
            )
            
        except Exception as e:
            logger.error(f"Failed to get status for {request_id}: {e}")
            return ExecutionResponse(
                request_id=request_id,
                status="error",
                error_message=str(e)
            )
    
    def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution results"""
        try:
            response = self.session.get(
                f"{self.server_url}/results",
                params={"limit": limit},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get recent results: {e}")
            return []
    
    def _wait_for_completion(self, 
                           request_id: str, 
                           timeout: int, 
                           poll_interval: float) -> ExecutionResponse:
        """Wait for request completion with polling"""
        start_time = time.time()
        
        logger.info(f"⏳ Waiting for completion: {request_id}")
        
        while time.time() - start_time < timeout:
            status_response = self.get_status(request_id)
            
            if status_response.status in ["success", "failed", "timeout"]:
                logger.info(f"🏁 Request completed: {request_id} ({status_response.status})")
                return status_response
            elif status_response.status == "error":
                logger.error(f"❌ Status check failed: {request_id}")
                return status_response
            
            time.sleep(poll_interval)
        
        # Timeout
        logger.warning(f"⏰ Request timed out: {request_id}")
        return ExecutionResponse(
            request_id=request_id,
            status="timeout",
            error_message="Client timeout waiting for completion"
        )
    
    def execute_batch(self, 
                     instructions: List[str],
                     mode: ExecutionMode = ExecutionMode.AGENT,
                     model: str = "copilot/gpt-4.1",
                     timeout: int = 60,
                     sequential: bool = True,
                     progress_callback: Optional[callable] = None) -> List[ExecutionResponse]:
        """
        Execute multiple instructions
        
        Args:
            instructions: List of instruction texts
            mode: Execution mode
            model: Model to use
            timeout: Per-instruction timeout
            sequential: Whether to execute sequentially or in parallel
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ExecutionResponse objects
        """
        results = []
        
        logger.info(f"📋 Executing batch of {len(instructions)} instructions")
        
        if sequential:
            # Sequential execution
            for i, instruction in enumerate(instructions):
                logger.info(f"📝 Executing instruction {i+1}/{len(instructions)}")
                
                result = self.execute_instruction(
                    instruction=instruction,
                    mode=mode,
                    model=model,
                    timeout=timeout,
                    wait_for_completion=True
                )
                
                results.append(result)
                
                if progress_callback:
                    progress_callback(i + 1, len(instructions), result)
                
                # Brief pause between executions
                time.sleep(0.5)
        else:
            # Parallel execution (submit all, then wait)
            request_ids = []
            
            # Submit all requests
            for instruction in instructions:
                result = self.execute_instruction(
                    instruction=instruction,
                    mode=mode,
                    model=model,
                    timeout=timeout,
                    wait_for_completion=False
                )
                request_ids.append(result.request_id)
            
            # Wait for all completions
            for i, request_id in enumerate(request_ids):
                result = self._wait_for_completion(request_id, timeout, 1.0)
                results.append(result)
                
                if progress_callback:
                    progress_callback(i + 1, len(instructions), result)
        
        logger.info(f"✅ Batch execution completed: {len(results)} results")
        return results


def main():
    """Example usage"""
    client = CopilotExecutionClient()
    
    # Health check
    health = client.health_check()
    print(f"Server health: {health}")
    
    if health.get("status") != "healthy":
        print("❌ Server is not healthy, cannot proceed")
        return
    
    # Example single execution
    result = client.execute_instruction(
        instruction="Create a simple Python function that calculates fibonacci numbers",
        mode=ExecutionMode.AGENT,
        wait_for_completion=True
    )
    
    print(f"Result: {result}")
    
    # Example batch execution
    instructions = [
        "Create a function to reverse a string",
        "Create a function to check if a number is prime",
        "Create a function to sort a list of dictionaries by a key"
    ]
    
    def progress_callback(current, total, result):
        print(f"Progress: {current}/{total} - {result.status}")
    
    batch_results = client.execute_batch(
        instructions=instructions,
        sequential=True,
        progress_callback=progress_callback
    )
    
    print(f"Batch results: {len(batch_results)} completed")
    
    # Show recent results
    recent = client.get_recent_results(limit=5)
    print(f"Recent results: {len(recent)} found")


if __name__ == "__main__":
    main()
