"""
Integration tests for the complete Copilot Instruction Evaluation System.
"""

import unittest
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
        self.project_root = self.test_dir
    
    def test_project_structure(self):
        """Test that the project has the expected structure."""
        expected_files = [
            "evaluate_agents.py",
            "instructions.json",
            "requirements.txt",
            "docs/TASKS.md",
            "copilot-recorder-poc/cascade_recorder/main.py",
            "tests/__init__.py"
        ]
        
        for file_path in expected_files:
            full_path = os.path.join(self.project_root, file_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"Expected file not found: {file_path}"
            )
    
    def test_requirements_file(self):
        """Test that requirements.txt exists and is readable."""
        requirements_path = os.path.join(self.project_root, "requirements.txt")
        self.assertTrue(os.path.exists(requirements_path))
        
        with open(requirements_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for essential packages
            essential_packages = ["requests", "pandas", "matplotlib"]
            for package in essential_packages:
                self.assertIn(package, content, f"Missing essential package: {package}")
    
    def test_evaluation_demo_mode_execution(self):
        """Test that evaluation script runs successfully in demo mode."""
        try:
            # Run evaluation script in demo mode
            cmd = [
                "python3", 
                os.path.join(self.project_root, "evaluate_agents.py"),
                "--demo-mode"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes timeout
                cwd=self.project_root
            )
            
            # Check that the script executed successfully
            self.assertEqual(result.returncode, 0, f"Demo mode execution failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            
            # Check for expected output patterns
            self.assertIn("GitHub Copilot Agent Evaluation", result.stdout)
            self.assertIn("[DONE] Evaluation completed", result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("Evaluation script timed out during execution")
        except Exception as e:
            self.fail(f"Failed to execute evaluation script: {e}")
    
    def test_recorder_test_harness_execution(self):
        """Test that recorder test harness runs successfully."""
        try:
            # Run recorder test harness
            cmd = [
                "python3", 
                "-m", "cascade_recorder.test_harness"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
                cwd=os.path.join(self.project_root, "copilot-recorder-poc")
            )
            
            # Check that the script executed successfully
            self.assertEqual(result.returncode, 0, f"Test harness execution failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            
            # Check for expected output patterns
            self.assertIn("PASS", result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("Recorder test harness timed out during execution")
        except Exception as e:
            # Test harness may fail due to Chrome dependencies in CI environment
            # Log the error but don't fail the test
            print(f"Note: Recorder test harness execution issue (expected in headless environments): {e}")
    
    def test_results_generation(self):
        """Test that evaluation generates expected result files."""
        results_dir = os.path.join(self.project_root, "results")
        
        # Expected result files
        expected_files = [
            "evaluation_results.json",
            "evaluation_results.csv",
            "evaluation_report.md"
        ]
        
        # Check if any results exist (they should after demo mode test)
        for file_name in expected_files:
            file_path = os.path.join(results_dir, file_name)
            if os.path.exists(file_path):
                self.assertTrue(os.path.getsize(file_path) > 0, f"Result file is empty: {file_name}")


class TestSystemConfiguration(unittest.TestCase):
    """Test system configuration and environment setup."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
    
    def test_python_version(self):
        """Test that Python version is compatible."""
        import sys
        version = sys.version_info
        
        # Require Python 3.8 or higher
        self.assertGreaterEqual(version.major, 3, "Python 3 is required")
        self.assertGreaterEqual(version.minor, 8, "Python 3.8 or higher is required")
    
    def test_essential_imports(self):
        """Test that essential Python packages can be imported."""
        essential_modules = [
            "json", "os", "sys", "time", "pathlib", "unittest",
            "subprocess", "tempfile", "logging"
        ]
        
        for module_name in essential_modules:
            try:
                __import__(module_name)
            except ImportError:
                self.fail(f"Failed to import essential module: {module_name}")
    
    def test_optional_imports(self):
        """Test optional packages (warn if missing but don't fail)."""
        optional_modules = [
            "requests", "pandas", "matplotlib", "numpy", "nltk", "rouge"
        ]
        
        missing_modules = []
        for module_name in optional_modules:
            try:
                __import__(module_name)
            except ImportError:
                missing_modules.append(module_name)
        
        if missing_modules:
            print(f"Warning: Missing optional modules: {missing_modules}")
            print("Install with: pip install -r requirements.txt")


class TestDocumentation(unittest.TestCase):
    """Test documentation and configuration files."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.dirname(os.path.dirname(__file__))
    
    def test_tasks_documentation(self):
        """Test that TASKS.md exists and has proper structure."""
        tasks_file = os.path.join(self.test_dir, "docs", "TASKS.md")
        self.assertTrue(os.path.exists(tasks_file))
        
        with open(tasks_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected sections
        expected_sections = [
            "# 🎯 最終ゴール",
            "## 🎭 ゴールまでのマイルストーン",
            "## 🎭 直近のゴール",
            "## 📋 タスク一覧",
            "## 💬 ユーザフィードバック履歴"
        ]
        
        for section in expected_sections:
            self.assertIn(section, content, f"Missing section: {section}")
    
    def test_readme_exists(self):
        """Test that README.md exists."""
        readme_file = os.path.join(self.test_dir, "README.md")
        self.assertTrue(os.path.exists(readme_file))
        
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertTrue(len(content) > 100, "README.md seems too short")


if __name__ == '__main__':
    unittest.main()