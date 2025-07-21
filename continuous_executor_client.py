"""
Continuous Executor Client

Adapter that converts the existing continuous execution system to use
the new client-server architecture. Maintains compatibility with existing
evaluation scripts while leveraging the centralized server.
"""

import json
import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
from copilot_execution_client import CopilotExecutionClient, ExecutionMode, ExecutionResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('continuous_execution_client.log')
    ]
)
logger = logging.getLogger(__name__)


class ContinuousExecutorClient:
    """
    Client-based continuous executor that maintains compatibility
    with existing evaluation systems while using the centralized server
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize client
        server_url = config.get('server_url', 'http://127.0.0.1:5000')
        client_id = config.get('client_id', f'continuous_executor_{int(time.time())}')
        
        self.client = CopilotExecutionClient(server_url=server_url, client_id=client_id)
        
        # Load instructions
        self.instructions = self._load_instructions()
        
        # Results storage
        self.results: List[ExecutionResponse] = []
        
        logger.info(f"🚀 Continuous Executor Client initialized")
        logger.info(f"📊 Loaded {len(self.instructions)} instructions")
        logger.info(f"🔗 Server: {server_url}")
        logger.info(f"🆔 Client: {client_id}")
    
    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from JSON file"""
        instructions_file = self.config.get('instructions_file', 'instructions.json')
        
        if not os.path.exists(instructions_file):
            logger.warning(f"Instructions file not found: {instructions_file}")
            return []
        
        try:
            with open(instructions_file, 'r') as f:
                instructions = json.load(f)
            
            logger.info(f"📋 Loaded {len(instructions)} instructions from {instructions_file}")
            return instructions
            
        except Exception as e:
            logger.error(f"Failed to load instructions: {e}")
            return []
    
    def check_server_health(self) -> bool:
        """Check if server is healthy and ready"""
        health = self.client.health_check()
        
        if health.get("status") == "healthy":
            logger.info("✅ Server is healthy and ready")
            logger.info(f"   VSCode running: {health.get('vscode_running', 'unknown')}")
            logger.info(f"   Extension ready: {health.get('extension_ready', 'unknown')}")
            logger.info(f"   Queue size: {health.get('queue_size', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Server is not healthy: {health}")
            return False
    
    def run_continuous_execution(self,
                                mode: ExecutionMode = ExecutionMode.AGENT,
                                model: str = "copilot/gpt-4.1",
                                instruction_filter: Optional[List[str]] = None,
                                max_instructions: Optional[int] = None,
                                delay_between_instructions: float = 2.0) -> List[ExecutionResponse]:
        """
        Run continuous execution of instructions
        
        Args:
            mode: Execution mode (AGENT or CHAT)
            model: Model to use
            instruction_filter: Optional list of instruction IDs to execute
            max_instructions: Maximum number of instructions to execute
            delay_between_instructions: Delay between instructions in seconds
            
        Returns:
            List of execution results
        """
        
        # Check server health first
        if not self.check_server_health():
            logger.error("❌ Cannot start execution - server not ready")
            return []
        
        # Filter instructions if needed
        instructions_to_execute = self.instructions
        
        if instruction_filter:
            instructions_to_execute = [
                inst for inst in instructions_to_execute 
                if inst.get('id') in instruction_filter
            ]
        
        if max_instructions:
            instructions_to_execute = instructions_to_execute[:max_instructions]
        
        logger.info(f"🚀 Starting continuous execution")
        logger.info(f"   Mode: {mode.value}")
        logger.info(f"   Model: {model}")
        logger.info(f"   Instructions: {len(instructions_to_execute)}")
        logger.info(f"   Delay: {delay_between_instructions}s")
        
        results = []
        start_time = time.time()
        
        for i, instruction in enumerate(instructions_to_execute):
            instruction_text = instruction.get('instruction', instruction.get('text', str(instruction)))
            instruction_id = instruction.get('id', f'inst_{i}')
            
            logger.info(f"📝 Executing {i+1}/{len(instructions_to_execute)}: {instruction_id}")
            logger.info(f"   Instruction: {instruction_text[:100]}...")
            
            try:
                # Execute instruction
                result = self.client.execute_instruction(
                    instruction=instruction_text,
                    mode=mode,
                    model=model,
                    timeout=self.config.get('execution_timeout', 60),
                    wait_for_completion=True
                )
                
                # Add metadata
                result.instruction_id = instruction_id
                result.instruction_index = i
                
                results.append(result)
                
                # Log result
                if result.status == "success":
                    logger.info(f"✅ Success: {instruction_id} ({result.execution_time:.2f}s)")
                    logger.info(f"   Response: {result.response[:200]}...")
                else:
                    logger.error(f"❌ Failed: {instruction_id} - {result.error_message}")
                
                # Delay between instructions (except for last one)
                if i < len(instructions_to_execute) - 1:
                    logger.info(f"⏳ Waiting {delay_between_instructions}s before next instruction...")
                    time.sleep(delay_between_instructions)
                
            except Exception as e:
                logger.error(f"❌ Exception executing {instruction_id}: {e}")
                
                # Create error result
                error_result = ExecutionResponse(
                    request_id="",
                    status="failed",
                    error_message=str(e)
                )
                error_result.instruction_id = instruction_id
                error_result.instruction_index = i
                results.append(error_result)
        
        total_time = time.time() - start_time
        
        logger.info(f"🏁 Continuous execution completed")
        logger.info(f"   Total time: {total_time:.2f}s")
        logger.info(f"   Instructions: {len(results)}")
        logger.info(f"   Success: {sum(1 for r in results if r.status == 'success')}")
        logger.info(f"   Failed: {sum(1 for r in results if r.status == 'failed')}")
        
        # Store results
        self.results = results
        
        # Save results to file
        self._save_results_to_file(results)
        
        return results
    
    def _save_results_to_file(self, results: List[ExecutionResponse]):
        """Save results to JSON file"""
        output_file = self.config.get('output_file', 'continuous_execution_results.json')
        
        try:
            # Convert results to serializable format
            serializable_results = []
            for result in results:
                result_dict = {
                    'request_id': result.request_id,
                    'status': result.status,
                    'response': result.response,
                    'execution_time': result.execution_time,
                    'error_message': result.error_message,
                    'instruction_id': getattr(result, 'instruction_id', ''),
                    'instruction_index': getattr(result, 'instruction_index', -1),
                    'timestamp': datetime.now().isoformat()
                }
                serializable_results.append(result_dict)
            
            with open(output_file, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"💾 Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def generate_execution_report(self) -> Dict[str, Any]:
        """Generate execution report"""
        if not self.results:
            logger.warning("No results available for report generation")
            return {}
        
        # Calculate statistics
        total_instructions = len(self.results)
        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "failed")
        success_rate = (successful / total_instructions) * 100 if total_instructions > 0 else 0
        
        # Calculate timing statistics
        execution_times = [r.execution_time for r in self.results if r.execution_time is not None]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        report = {
            "summary": {
                "total_instructions": total_instructions,
                "successful": successful,
                "failed": failed,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time
            },
            "results": []
        }
        
        # Add individual results
        for result in self.results:
            report["results"].append({
                "instruction_id": getattr(result, 'instruction_id', ''),
                "status": result.status,
                "execution_time": result.execution_time,
                "response_length": len(result.response) if result.response else 0,
                "has_error": result.error_message is not None
            })
        
        # Save report
        report_file = self.config.get('report_file', 'execution_report.json')
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📊 Report saved to {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        # Print summary
        logger.info("📊 Execution Report Summary:")
        logger.info(f"   Total Instructions: {total_instructions}")
        logger.info(f"   Successful: {successful}")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        logger.info(f"   Average Execution Time: {avg_execution_time:.2f}s")
        
        return report


def main():
    """Main function for testing"""
    config = {
        'server_url': 'http://127.0.0.1:5000',
        'instructions_file': 'test_instructions.json',
        'execution_timeout': 60,
        'output_file': 'test_results.json',
        'report_file': 'test_report.json'
    }
    
    # Create test instructions file if it doesn't exist
    if not os.path.exists(config['instructions_file']):
        test_instructions = [
            {
                "id": "test_1",
                "instruction": "Create a Python function that calculates the factorial of a number"
            },
            {
                "id": "test_2", 
                "instruction": "Create a Python function that checks if a string is a palindrome"
            },
            {
                "id": "test_3",
                "instruction": "Create a Python function that finds the maximum element in a list"
            }
        ]
        
        with open(config['instructions_file'], 'w') as f:
            json.dump(test_instructions, f, indent=2)
        
        logger.info(f"Created test instructions file: {config['instructions_file']}")
    
    # Run continuous execution
    executor = ContinuousExecutorClient(config)
    
    results = executor.run_continuous_execution(
        mode=ExecutionMode.AGENT,
        model="copilot/gpt-4.1",
        max_instructions=3,
        delay_between_instructions=1.0
    )
    
    # Generate report
    report = executor.generate_execution_report()
    
    print(f"\n🎯 Execution completed with {len(results)} results")
    print(f"📊 Success rate: {report['summary']['success_rate']:.1f}%")


if __name__ == "__main__":
    main()
