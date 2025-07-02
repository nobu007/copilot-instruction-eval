"""
Test cases for the evaluation system functionality.
"""

import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestEvaluationSystem(unittest.TestCase):
    """Test cases for the main evaluation system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
        self.instructions_file = os.path.join(self.test_dir, "instructions.json")
    
    def test_instructions_file_exists(self):
        """Test that the instructions file exists."""
        self.assertTrue(
            os.path.exists(self.instructions_file),
            f"Instructions file not found at {self.instructions_file}"
        )
    
    def test_instructions_file_format(self):
        """Test that the instructions file has the correct format."""
        with open(self.instructions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, dict)
        self.assertIn("instructions", data)
        self.assertIsInstance(data["instructions"], list)
        
        # Test structure of each instruction
        for instruction in data["instructions"]:
            required_fields = ["id", "type", "title", "description"]
            for field in required_fields:
                self.assertIn(field, instruction, f"Missing field '{field}' in instruction {instruction.get('id', 'unknown')}")
    
    def test_evaluation_script_imports(self):
        """Test that the evaluation script imports correctly."""
        try:
            # Add project root to path for imports
            import sys
            if self.test_dir not in sys.path:
                sys.path.insert(0, self.test_dir)
            
            import evaluate_agents
            self.assertTrue(hasattr(evaluate_agents, 'AgentEvaluator'))
            self.assertTrue(hasattr(evaluate_agents, 'main'))
            
        except ImportError as e:
            self.fail(f"Failed to import evaluate_agents module: {e}")


class TestAgentEvaluatorDemo(unittest.TestCase):
    """Test cases for AgentEvaluator in demo mode."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
        # Add project root to path for imports
        import sys
        if self.test_dir not in sys.path:
            sys.path.insert(0, self.test_dir)
        
        # Demo mode configuration
        self.demo_config = {
            "demo_mode": True,
            "instructions_file": os.path.join(self.test_dir, "instructions.json"),
            "results_dir": "test_results",
            "timeout": 60,
            "max_retries": 3,
            "retry_delay": 5
        }
    
    def test_demo_mode_initialization(self):
        """Test AgentEvaluator initialization in demo mode."""
        try:
            import evaluate_agents
            
            # Create temporary results directory
            with tempfile.TemporaryDirectory() as temp_dir:
                self.demo_config["results_dir"] = temp_dir
                
                evaluator = evaluate_agents.AgentEvaluator(self.demo_config)
                self.assertIsNotNone(evaluator)
                self.assertTrue(evaluator.config.get("demo_mode"))
                
        except Exception as e:
            self.fail(f"Failed to initialize AgentEvaluator in demo mode: {e}")
    
    def test_demo_response_simulation(self):
        """Test that demo mode generates simulated responses."""
        try:
            import evaluate_agents
            
            with tempfile.TemporaryDirectory() as temp_dir:
                self.demo_config["results_dir"] = temp_dir
                
                evaluator = evaluate_agents.AgentEvaluator(self.demo_config)
                
                # Test simulated response generation
                response = evaluator._simulate_agent_response("v1", "Review this authentication code for security issues.")
                
                self.assertIsInstance(response, str)
                self.assertIn("Agent v1", response)
                self.assertTrue(len(response) > 10)
                
        except Exception as e:
            self.fail(f"Failed to generate simulated response: {e}")
    
    def test_demo_evaluation_metrics(self):
        """Test evaluation metrics calculation in demo mode."""
        try:
            import evaluate_agents
            
            with tempfile.TemporaryDirectory() as temp_dir:
                self.demo_config["results_dir"] = temp_dir
                
                evaluator = evaluate_agents.AgentEvaluator(self.demo_config)
                
                # Mock instruction for testing
                test_instruction = {
                    "id": "test_1",
                    "type": "code_review",
                    "title": "Test Instruction",
                    "description": "Test description for metric calculation",
                    "expected_response": "This is a test expected response for metrics calculation.",
                    "difficulty": "medium"
                }
                
                # Test evaluation of single instruction
                result = evaluator._evaluate_instruction(test_instruction, "v1")
                
                self.assertIsInstance(result, dict)
                self.assertIn("success", result)
                
                # Test that metrics are calculated
                if result["success"]:
                    self.assertIn("metrics", result)
                    metrics = result["metrics"]
                    self.assertIn("jaccard_similarity", metrics)
                    self.assertIn("bleu_score", metrics)
                    self.assertIn("rouge_1", metrics)
                    self.assertIn("response_time", metrics)
                    
        except Exception as e:
            self.fail(f"Failed to calculate evaluation metrics: {e}")


class TestEvaluationResults(unittest.TestCase):
    """Test cases for evaluation results and reporting."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
        self.results_dir = os.path.join(self.test_dir, "results")
    
    def test_results_directory_exists(self):
        """Test that results directory exists."""
        self.assertTrue(
            os.path.exists(self.results_dir),
            f"Results directory not found at {self.results_dir}"
        )
    
    def test_evaluation_results_files(self):
        """Test that evaluation results files exist and are valid."""
        results_json = os.path.join(self.results_dir, "evaluation_results.json")
        results_csv = os.path.join(self.results_dir, "evaluation_results.csv")
        
        if os.path.exists(results_json):
            with open(results_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertIsInstance(data, dict)
            self.assertIn("timestamp", data)
            self.assertIn("results", data)
            
        if os.path.exists(results_csv):
            # Basic check that CSV file is readable
            with open(results_csv, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertTrue(len(content) > 0)
    
    def test_evaluation_report_exists(self):
        """Test that evaluation report exists and has basic structure."""
        report_path = os.path.join(self.results_dir, "evaluation_report.md")
        
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for basic report sections
            self.assertIn("# GitHub Copilot Agent Evaluation Report", content)
            self.assertIn("## 📊 Summary", content)


if __name__ == '__main__':
    unittest.main()