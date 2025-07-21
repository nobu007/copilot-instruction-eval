"""
VSCode Extension Client - Stdout Based Communication

既存のVSCode拡張機能と標準出力経由で通信するクライアント。
拡張機能のバッチコマンドを実行し、標準出力から結果を解析する。
"""

import json
import subprocess
import time
import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for Copilot"""
    AGENT = "agent"
    CHAT = "chat"


@dataclass
class ExecutionResult:
    """Result of Copilot execution"""
    success: bool
    prompt: str
    response: Optional[str] = None
    model: Optional[str] = None
    mode: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: Optional[str] = None
    execution_id: Optional[str] = None
    error: Optional[str] = None


class VSCodeExtensionClient:
    """Client for communicating with VSCode extension via stdout"""
    
    def __init__(self, extension_path: str, vscode_command: str = "code"):
        self.extension_path = extension_path
        self.vscode_command = vscode_command
        
        logger.info(f"🔗 VSCode Extension Client initialized")
        logger.info(f"📁 Extension path: {extension_path}")
        logger.info(f"💻 VSCode command: {vscode_command}")
    
    def execute_prompt(self, 
                      prompt: str, 
                      timeout: int = 60,
                      model: Optional[str] = None,
                      mode: ExecutionMode = ExecutionMode.AGENT) -> ExecutionResult:
        """
        Execute a prompt via VSCode extension and capture result from stdout
        
        Args:
            prompt: The prompt text to execute
            timeout: Execution timeout in seconds
            model: Model to use (optional, uses extension default)
            mode: Execution mode (agent/chat)
            
        Returns:
            ExecutionResult with parsed response
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Executing prompt via VSCode extension")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            logger.info(f"⏱️ Timeout: {timeout}s")
            
            # Prepare command
            cmd = [
                self.vscode_command,
                "--command", "copilotAutomation.executeBatchPrompt",
                prompt
            ]
            
            logger.info(f"💻 Command: {' '.join(cmd)}")
            
            # Execute command and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.extension_path
            )
            
            execution_time = time.time() - start_time
            
            logger.info(f"📊 Command completed in {execution_time:.2f}s")
            logger.info(f"📤 Return code: {result.returncode}")
            logger.info(f"📝 Stdout length: {len(result.stdout)} chars")
            logger.info(f"📝 Stderr length: {len(result.stderr)} chars")
            
            # Parse stdout for result
            parsed_result = self._parse_stdout_result(result.stdout)
            
            if parsed_result:
                logger.info(f"✅ Successfully parsed result from stdout")
                return ExecutionResult(
                    success=parsed_result.get('success', False),
                    prompt=prompt,
                    response=parsed_result.get('response'),
                    model=parsed_result.get('model'),
                    mode=parsed_result.get('mode'),
                    execution_time=execution_time,
                    timestamp=parsed_result.get('timestamp'),
                    execution_id=parsed_result.get('executionId'),
                    error=parsed_result.get('error')
                )
            else:
                logger.warning(f"⚠️ No result found in stdout, checking stderr")
                error_msg = result.stderr if result.stderr else "No output captured"
                
                return ExecutionResult(
                    success=False,
                    prompt=prompt,
                    execution_time=execution_time,
                    error=f"Failed to parse result: {error_msg}"
                )
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(f"⏰ Command timed out after {timeout}s")
            
            return ExecutionResult(
                success=False,
                prompt=prompt,
                execution_time=execution_time,
                error=f"Execution timed out after {timeout}s"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Command execution failed: {e}")
            
            return ExecutionResult(
                success=False,
                prompt=prompt,
                execution_time=execution_time,
                error=str(e)
            )
    
    def _parse_stdout_result(self, stdout: str) -> Optional[Dict[str, Any]]:
        """
        Parse result from stdout using delimiters
        
        Args:
            stdout: Raw stdout content
            
        Returns:
            Parsed result dictionary or None if not found
        """
        try:
            # Look for result delimiters
            start_marker = "COPILOT_RESULT_START"
            end_marker = "COPILOT_RESULT_END"
            
            # Find result content between markers
            start_idx = stdout.find(start_marker)
            end_idx = stdout.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                logger.warning(f"⚠️ Result markers not found in stdout")
                logger.debug(f"Stdout content: {stdout[:500]}...")
                return None
            
            # Extract JSON content
            json_start = start_idx + len(start_marker)
            json_content = stdout[json_start:end_idx].strip()
            
            logger.debug(f"📋 Extracted JSON: {json_content[:200]}...")
            
            # Parse JSON
            result = json.loads(json_content)
            logger.info(f"✅ Successfully parsed JSON result")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.debug(f"Raw content: {stdout}")
            return None
        except Exception as e:
            logger.error(f"❌ Result parsing failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to VSCode extension
        
        Returns:
            True if extension is accessible, False otherwise
        """
        try:
            logger.info(f"🔍 Testing VSCode extension connection...")
            
            # Try a simple test command
            result = self.execute_prompt(
                prompt="Test connection - return 'OK'",
                timeout=30
            )
            
            if result.success:
                logger.info(f"✅ Extension connection test successful")
                return True
            else:
                logger.warning(f"⚠️ Extension connection test failed: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Extension connection test error: {e}")
            return False


def main():
    """Test the VSCode Extension Client"""
    
    # Configuration
    extension_path = "/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension"
    
    # Create client
    client = VSCodeExtensionClient(extension_path)
    
    # Test connection
    print("🔍 Testing VSCode extension connection...")
    if not client.test_connection():
        print("❌ Extension connection failed")
        return
    
    # Test prompt execution
    print("\n📝 Testing prompt execution...")
    
    test_prompts = [
        "Create a simple Python function that adds two numbers",
        "Write a function to check if a number is prime",
        "Create a function that reverses a string"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Test {i}/{len(test_prompts)} ---")
        print(f"Prompt: {prompt}")
        
        result = client.execute_prompt(prompt, timeout=60)
        
        print(f"Success: {result.success}")
        print(f"Execution time: {result.execution_time:.2f}s")
        
        if result.success:
            print(f"Model: {result.model}")
            print(f"Mode: {result.mode}")
            print(f"Response length: {len(result.response) if result.response else 0}")
            print(f"Response preview: {result.response[:200] if result.response else 'None'}...")
        else:
            print(f"Error: {result.error}")
        
        # Brief pause between tests
        time.sleep(2)
    
    print("\n🎯 VSCode Extension Client test completed")


if __name__ == "__main__":
    main()
