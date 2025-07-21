"""
GitHub Copilot Evaluation Framework

既存のVSCode拡張機能を活用したCopilot性能評価システム。
プロンプト・モデルごとのアウトプットと処理時間を比較・評価する。
"""

import json
import time
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import requests
from copilot_execution_client import CopilotExecutionClient, ExecutionMode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('copilot_evaluation.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationTest:
    """Single evaluation test case"""
    test_id: str
    category: str
    prompt: str
    expected_elements: List[str]
    timeout: int = 60
    models_to_test: List[str] = None
    modes_to_test: List[str] = None


@dataclass
class EvaluationResult:
    """Result of a single evaluation"""
    test_id: str
    model: str
    mode: str
    prompt: str
    response: str
    execution_time: float
    success: bool
    timestamp: str
    response_length: int
    contains_expected_elements: int
    error_message: Optional[str] = None


class CopilotEvaluationFramework:
    """Main evaluation framework class"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize client
        server_url = config.get('server_url', 'http://127.0.0.1:5001')
        client_id = f'evaluator_{int(time.time())}'
        
        self.client = CopilotExecutionClient(server_url=server_url, client_id=client_id)
        
        # Load test cases
        self.test_cases = self._load_test_cases()
        
        # Results storage
        self.results: List[EvaluationResult] = []
        
        logger.info(f"🎯 Copilot Evaluation Framework initialized")
        logger.info(f"🔗 Server: {server_url}")
        logger.info(f"📋 Test cases: {len(self.test_cases)}")
    
    def _load_test_cases(self) -> List[EvaluationTest]:
        """Load test cases from JSON file"""
        test_file = self.config.get('test_cases_file', 'evaluation_test_cases.json')
        
        if not Path(test_file).exists():
            logger.warning(f"Test cases file not found: {test_file}")
            return self._create_default_test_cases()
        
        try:
            with open(test_file, 'r') as f:
                test_data = json.load(f)
            
            test_cases = []
            for item in test_data:
                test_cases.append(EvaluationTest(
                    test_id=item['test_id'],
                    category=item['category'],
                    prompt=item['prompt'],
                    expected_elements=item.get('expected_elements', []),
                    timeout=item.get('timeout', 60),
                    models_to_test=item.get('models_to_test'),
                    modes_to_test=item.get('modes_to_test')
                ))
            
            logger.info(f"📋 Loaded {len(test_cases)} test cases from {test_file}")
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to load test cases: {e}")
            return self._create_default_test_cases()
    
    def _create_default_test_cases(self) -> List[EvaluationTest]:
        """Create default test cases for evaluation"""
        default_tests = [
            {
                "test_id": "code_gen_001",
                "category": "code_generation",
                "prompt": "Create a Python function that calculates fibonacci numbers",
                "expected_elements": ["def", "fibonacci", "return"]
            },
            {
                "test_id": "code_gen_002", 
                "category": "code_generation",
                "prompt": "Write a function to check if a number is prime",
                "expected_elements": ["def", "prime", "return", "for"]
            },
            {
                "test_id": "code_gen_003",
                "category": "code_generation", 
                "prompt": "Create a function that reverses a string",
                "expected_elements": ["def", "reverse", "return"]
            },
            {
                "test_id": "algorithm_001",
                "category": "algorithms",
                "prompt": "Implement bubble sort algorithm in Python",
                "expected_elements": ["def", "sort", "for", "while"]
            },
            {
                "test_id": "data_struct_001",
                "category": "data_structures",
                "prompt": "Create a simple linked list class in Python",
                "expected_elements": ["class", "Node", "__init__", "next"]
            }
        ]
        
        test_cases = []
        for item in default_tests:
            test_cases.append(EvaluationTest(
                test_id=item['test_id'],
                category=item['category'],
                prompt=item['prompt'],
                expected_elements=item['expected_elements'],
                models_to_test=['copilot/gpt-4', 'copilot/claude-3.5'],
                modes_to_test=['agent', 'chat']
            ))
        
        # Save default test cases
        self._save_test_cases_to_file(default_tests)
        
        logger.info(f"📋 Created {len(test_cases)} default test cases")
        return test_cases
    
    def _save_test_cases_to_file(self, test_data: List[Dict]):
        """Save test cases to JSON file"""
        test_file = self.config.get('test_cases_file', 'evaluation_test_cases.json')
        
        try:
            with open(test_file, 'w') as f:
                json.dump(test_data, f, indent=2)
            logger.info(f"💾 Saved test cases to {test_file}")
        except Exception as e:
            logger.error(f"Failed to save test cases: {e}")
    
    def run_evaluation(self, 
                      models: Optional[List[str]] = None,
                      modes: Optional[List[str]] = None,
                      test_filter: Optional[List[str]] = None,
                      delay_between_tests: float = 2.0) -> List[EvaluationResult]:
        """
        Run complete evaluation suite
        
        Args:
            models: List of models to test (None for default)
            modes: List of modes to test (None for default)  
            test_filter: List of test IDs to run (None for all)
            delay_between_tests: Delay between tests in seconds
            
        Returns:
            List of evaluation results
        """
        
        # Check server health
        health = self.client.health_check()
        if health.get("status") != "healthy":
            logger.error("❌ Server is not healthy, cannot run evaluation")
            return []
        
        # Filter test cases
        tests_to_run = self.test_cases
        if test_filter:
            tests_to_run = [t for t in tests_to_run if t.test_id in test_filter]
        
        # Default models and modes
        default_models = models or ['copilot/gpt-4']
        default_modes = modes or ['agent']
        
        logger.info(f"🚀 Starting evaluation")
        logger.info(f"   Tests: {len(tests_to_run)}")
        logger.info(f"   Models: {default_models}")
        logger.info(f"   Modes: {default_modes}")
        logger.info(f"   Total executions: {len(tests_to_run) * len(default_models) * len(default_modes)}")
        
        results = []
        total_executions = 0
        
        for test_case in tests_to_run:
            # Use test-specific models/modes or defaults
            test_models = test_case.models_to_test or default_models
            test_modes = test_case.modes_to_test or default_modes
            
            for model in test_models:
                for mode_str in test_modes:
                    total_executions += 1
                    mode = ExecutionMode.AGENT if mode_str.lower() == 'agent' else ExecutionMode.CHAT
                    
                    logger.info(f"📝 Executing {total_executions}: {test_case.test_id} | {model} | {mode_str}")
                    logger.info(f"   Prompt: {test_case.prompt[:100]}...")
                    
                    try:
                        # Execute test
                        result = self.client.execute_instruction(
                            instruction=test_case.prompt,
                            mode=mode,
                            model=model,
                            timeout=test_case.timeout,
                            wait_for_completion=True
                        )
                        
                        # Analyze result
                        evaluation_result = self._analyze_result(
                            test_case, model, mode_str, result
                        )
                        
                        results.append(evaluation_result)
                        
                        # Log result
                        if evaluation_result.success:
                            logger.info(f"✅ Success: {evaluation_result.execution_time:.2f}s")
                            logger.info(f"   Response length: {evaluation_result.response_length}")
                            logger.info(f"   Expected elements found: {evaluation_result.contains_expected_elements}/{len(test_case.expected_elements)}")
                        else:
                            logger.error(f"❌ Failed: {evaluation_result.error_message}")
                        
                        # Delay between tests
                        if delay_between_tests > 0:
                            logger.info(f"⏳ Waiting {delay_between_tests}s...")
                            time.sleep(delay_between_tests)
                        
                    except Exception as e:
                        logger.error(f"❌ Exception in test execution: {e}")
                        
                        # Create error result
                        error_result = EvaluationResult(
                            test_id=test_case.test_id,
                            model=model,
                            mode=mode_str,
                            prompt=test_case.prompt,
                            response="",
                            execution_time=0.0,
                            success=False,
                            timestamp=datetime.now().isoformat(),
                            response_length=0,
                            contains_expected_elements=0,
                            error_message=str(e)
                        )
                        results.append(error_result)
        
        logger.info(f"🏁 Evaluation completed")
        logger.info(f"   Total executions: {len(results)}")
        logger.info(f"   Successful: {sum(1 for r in results if r.success)}")
        logger.info(f"   Failed: {sum(1 for r in results if not r.success)}")
        
        # Store results
        self.results = results
        
        # Save results
        self._save_results()
        
        return results
    
    def _analyze_result(self, test_case: EvaluationTest, model: str, mode: str, result) -> EvaluationResult:
        """Analyze execution result and create evaluation result"""
        
        response = result.response or ""
        response_length = len(response)
        
        # Check for expected elements
        contains_expected = 0
        if test_case.expected_elements:
            for element in test_case.expected_elements:
                if element.lower() in response.lower():
                    contains_expected += 1
        
        return EvaluationResult(
            test_id=test_case.test_id,
            model=model,
            mode=mode,
            prompt=test_case.prompt,
            response=response,
            execution_time=result.execution_time or 0.0,
            success=result.status == "success",
            timestamp=datetime.now().isoformat(),
            response_length=response_length,
            contains_expected_elements=contains_expected,
            error_message=result.error_message
        )
    
    def _save_results(self):
        """Save evaluation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_file = f"evaluation_results_{timestamp}.json"
        try:
            results_data = []
            for result in self.results:
                results_data.append({
                    "test_id": result.test_id,
                    "model": result.model,
                    "mode": result.mode,
                    "prompt": result.prompt,
                    "response": result.response,
                    "execution_time": result.execution_time,
                    "success": result.success,
                    "timestamp": result.timestamp,
                    "response_length": result.response_length,
                    "contains_expected_elements": result.contains_expected_elements,
                    "error_message": result.error_message
                })
            
            with open(json_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"💾 Results saved to {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to save JSON results: {e}")
        
        # Save as CSV
        csv_file = f"evaluation_results_{timestamp}.csv"
        try:
            df = pd.DataFrame([
                {
                    "test_id": r.test_id,
                    "model": r.model,
                    "mode": r.mode,
                    "execution_time": r.execution_time,
                    "success": r.success,
                    "response_length": r.response_length,
                    "contains_expected_elements": r.contains_expected_elements,
                    "error_message": r.error_message
                }
                for r in self.results
            ])
            
            df.to_csv(csv_file, index=False)
            logger.info(f"💾 Results saved to {csv_file}")
            
        except Exception as e:
            logger.error(f"Failed to save CSV results: {e}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report with statistics"""
        if not self.results:
            logger.warning("No results available for report generation")
            return {}
        
        # Overall statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Timing statistics
        execution_times = [r.execution_time for r in self.results if r.success]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Model comparison
        model_stats = {}
        for result in self.results:
            if result.model not in model_stats:
                model_stats[result.model] = {"total": 0, "success": 0, "avg_time": 0}
            
            model_stats[result.model]["total"] += 1
            if result.success:
                model_stats[result.model]["success"] += 1
        
        # Calculate success rates and average times per model
        for model in model_stats:
            stats = model_stats[model]
            stats["success_rate"] = (stats["success"] / stats["total"]) * 100
            
            model_times = [r.execution_time for r in self.results 
                          if r.model == model and r.success]
            stats["avg_time"] = sum(model_times) / len(model_times) if model_times else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time
            },
            "model_comparison": model_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        # Print report
        logger.info("📊 Evaluation Report:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        logger.info(f"   Average Execution Time: {avg_execution_time:.2f}s")
        logger.info("   Model Comparison:")
        for model, stats in model_stats.items():
            logger.info(f"     {model}: {stats['success_rate']:.1f}% success, {stats['avg_time']:.2f}s avg")
        
        return report


def main():
    """Main function for running evaluation"""
    config = {
        'server_url': 'http://127.0.0.1:5001',
        'test_cases_file': 'evaluation_test_cases.json'
    }
    
    # Create evaluation framework
    evaluator = CopilotEvaluationFramework(config)
    
    # Run evaluation
    results = evaluator.run_evaluation(
        models=['copilot/gpt-4'],
        modes=['agent'],
        delay_between_tests=1.0
    )
    
    # Generate report
    report = evaluator.generate_report()
    
    print(f"\n🎯 Evaluation completed with {len(results)} results")
    print(f"📊 Success rate: {report['summary']['success_rate']:.1f}%")


if __name__ == "__main__":
    main()
