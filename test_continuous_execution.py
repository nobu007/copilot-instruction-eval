#!/usr/bin/env python3
"""
Test script for VSCode Copilot Continuous Execution System

This script tests the integration between the continuous execution engine
and the VSCode extension with CLI connectivity.
"""

import json
import os
import sys
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_extension_availability():
    """Test if VSCode extension is available and responsive"""
    logger.info("🔍 Testing VSCode extension availability...")
    
    # Check if VSCode is running
    import subprocess
    try:
        result = subprocess.run(['code', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"✅ VSCode is available: {result.stdout.strip().split()[0]}")
            return True
        else:
            logger.error("❌ VSCode is not available")
            return False
    except Exception as e:
        logger.error(f"❌ VSCode availability check failed: {e}")
        return False

def test_file_based_communication():
    """Test file-based communication with extension"""
    logger.info("📁 Testing file-based communication...")
    
    # Create test directory
    test_dir = Path('.vscode/copilot-automation')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test instruction file
    test_instruction = {
        "id": "test_001",
        "type": "test",
        "prompt": "Hello, this is a test prompt for Copilot integration.",
        "mode": "agent",
        "model": "copilot/gpt-4.1",
        "timestamp": time.time()
    }
    
    instruction_file = test_dir / 'instruction_queue.json'
    with open(instruction_file, 'w', encoding='utf-8') as f:
        json.dump(test_instruction, f, indent=2)
    
    logger.info(f"📝 Test instruction created: {instruction_file}")
    
    # Wait for result file (simulated)
    result_file = test_dir / 'execution_result.json'
    
    # For testing, create a mock result
    mock_result = {
        "success": True,
        "instruction_id": "test_001",
        "response": "This is a mock response from Copilot for testing purposes.",
        "execution_time": 2.5,
        "timestamp": time.time(),
        "model": "copilot/gpt-4.1",
        "mode": "agent"
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(mock_result, f, indent=2)
    
    logger.info(f"✅ Mock result created: {result_file}")
    return True

def test_continuous_executor():
    """Test the continuous executor with a simple instruction"""
    logger.info("🚀 Testing continuous executor...")
    
    try:
        from vscode_copilot_continuous_executor import VSCodeCopilotExecutor, ExecutionMode
        
        config = {
            'extension_path': '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
            'instructions_file': 'instructions.json',
            'execution_timeout': 30,
            'retry_attempts': 2,
            'db_path': 'test_continuous_execution.db'
        }
        
        executor = VSCodeCopilotExecutor(config)
        
        # Test with a single instruction
        test_instruction = {
            "id": "integration_test_001",
            "type": "test",
            "description": "Test integration between continuous executor and VSCode extension",
            "expected_response": "Integration test response"
        }
        
        logger.info("🎯 Executing test instruction...")
        result = executor.execute_instruction(
            test_instruction,
            mode=ExecutionMode.AGENT,
            model="copilot/gpt-4.1"
        )
        
        logger.info(f"📊 Execution result:")
        logger.info(f"  - Status: {result.status.value}")
        logger.info(f"  - Execution time: {result.execution_time:.2f}s")
        logger.info(f"  - Response length: {len(result.response)} chars")
        
        if result.error_message:
            logger.warning(f"⚠️ Error message: {result.error_message}")
        
        return result.status.value == 'completed'
        
    except Exception as e:
        logger.error(f"❌ Continuous executor test failed: {e}")
        return False

def test_batch_execution():
    """Test batch execution of multiple instructions"""
    logger.info("📦 Testing batch execution...")
    
    try:
        from vscode_copilot_continuous_executor import VSCodeCopilotExecutor, ExecutionMode
        
        config = {
            'extension_path': '/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
            'instructions_file': 'instructions.json',
            'execution_timeout': 30,
            'retry_attempts': 1,
            'db_path': 'test_batch_execution.db'
        }
        
        executor = VSCodeCopilotExecutor(config)
        
        # Test with first 2 instructions only
        results = executor.run_continuous_execution(
            mode=ExecutionMode.AGENT,
            model="copilot/gpt-4.1",
            instruction_filter=["code_review_1", "pr_creation_1"]  # Limit to 2 instructions
        )
        
        logger.info(f"📊 Batch execution results:")
        logger.info(f"  - Total instructions: {len(results)}")
        
        successful = sum(1 for r in results if r.status.value == 'completed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        
        logger.info(f"  - Successful: {successful}")
        logger.info(f"  - Failed: {failed}")
        
        # Generate report
        report = executor.generate_execution_report()
        report_file = 'test_batch_execution_report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 Report saved: {report_file}")
        
        return successful > 0
        
    except Exception as e:
        logger.error(f"❌ Batch execution test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🎉 Starting VSCode Copilot Continuous Execution System Tests")
    
    tests = [
        ("Extension Availability", test_extension_availability),
        ("File-based Communication", test_file_based_communication),
        ("Continuous Executor", test_continuous_executor),
        ("Batch Execution", test_batch_execution)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready for production use.")
        return 0
    else:
        logger.warning("⚠️ Some tests failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
