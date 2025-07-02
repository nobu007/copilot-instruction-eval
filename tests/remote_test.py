#!/usr/bin/env python3
"""
Remote environment test script for VSCode Tunnel and similar environments.

This script verifies that the evaluation system works correctly in remote 
development environments like VSCode Tunnel, GitHub Codespaces, etc.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path


class RemoteEnvironmentTester:
    """Test runner for remote environments."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {
            "environment": self._detect_environment(),
            "tests": [],
            "overall_status": "unknown",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _detect_environment(self):
        """Detect the type of remote environment."""
        env_info = {
            "platform": sys.platform,
            "python_version": sys.version,
            "remote_type": "unknown"
        }
        
        # Check for various remote environment indicators
        if "CODESPACES" in os.environ:
            env_info["remote_type"] = "github_codespaces"
        elif "VSCODE_REMOTE" in os.environ:
            env_info["remote_type"] = "vscode_remote"
        elif "SSH_CLIENT" in os.environ or "SSH_CONNECTION" in os.environ:
            env_info["remote_type"] = "ssh_remote"
        elif os.path.exists("/tmp/.X11-unix"):
            env_info["remote_type"] = "x11_forwarding"
        else:
            env_info["remote_type"] = "local_or_unknown"
        
        return env_info
    
    def run_test(self, test_name, test_func):
        """Run a single test and record results."""
        print(f"🧪 Running test: {test_name}")
        
        start_time = time.time()
        try:
            result = test_func()
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "status": "passed" if result else "failed",
                "duration": duration,
                "details": result if isinstance(result, dict) else {"success": result}
            }
            print(f"   ✅ Passed ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            test_result = {
                "name": test_name,
                "status": "error",
                "duration": duration,
                "error": str(e)
            }
            print(f"   ❌ Error: {e}")
        
        self.test_results["tests"].append(test_result)
        return test_result["status"] == "passed"
    
    def test_environment_setup(self):
        """Test basic environment setup."""
        checks = {
            "python_version": sys.version_info >= (3, 8),
            "project_root_exists": self.project_root.exists(),
            "requirements_exists": (self.project_root / "requirements.txt").exists(),
            "evaluation_script_exists": (self.project_root / "evaluate_agents.py").exists()
        }
        
        return all(checks.values()), checks
    
    def test_dependencies_install(self):
        """Test that dependencies can be installed."""
        try:
            # Check if basic dependencies are available
            import json, os, sys, time, pathlib
            import subprocess, tempfile, logging
            
            # Try to install missing packages
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-q", 
                "requests", "pandas", "matplotlib"
            ], capture_output=True, text=True, timeout=60)
            
            return result.returncode == 0
            
        except Exception as e:
            return False
    
    def test_evaluation_demo_mode(self):
        """Test evaluation system in demo mode."""
        try:
            os.chdir(self.project_root)
            
            result = subprocess.run([
                sys.executable, "evaluate_agents.py", "--demo-mode"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                return False
            
            # Check if result files were created
            results_dir = self.project_root / "results"
            required_files = [
                "evaluation_results.json",
                "evaluation_results.csv", 
                "evaluation_report.md"
            ]
            
            files_exist = all((results_dir / f).exists() for f in required_files)
            
            return files_exist and "DONE" in result.stdout
            
        except Exception as e:
            return False
    
    def test_recorder_availability(self):
        """Test if recorder components are available."""
        try:
            cascade_path = self.project_root / "copilot-recorder-poc"
            
            if not cascade_path.exists():
                return False
            
            # Check key recorder files
            key_files = [
                "cascade_recorder/__init__.py",
                "cascade_recorder/main.py",
                "cascade_recorder/recorder.py",
                "cascade_recorder/actions.py"
            ]
            
            return all((cascade_path / f).exists() for f in key_files)
            
        except Exception as e:
            return False
    
    def test_unit_tests(self):
        """Run basic unit tests."""
        try:
            os.chdir(self.project_root)
            
            # Run a subset of tests that don't require browser
            result = subprocess.run([
                sys.executable, "-m", "pytest", "tests/test_evaluation.py::TestEvaluationSystem", 
                "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            return result.returncode == 0 and "FAILED" not in result.stdout
            
        except Exception as e:
            return False
    
    def test_network_connectivity(self):
        """Test network connectivity for external dependencies."""
        try:
            import urllib.request
            
            # Test connection to common package repositories
            test_urls = [
                "https://pypi.org",
                "https://files.pythonhosted.org",
                "https://github.com"
            ]
            
            successful_connections = 0
            for url in test_urls:
                try:
                    urllib.request.urlopen(url, timeout=10)
                    successful_connections += 1
                except:
                    pass
            
            # Require at least 2/3 connections to succeed
            return successful_connections >= 2
            
        except Exception as e:
            return False
    
    def run_all_tests(self):
        """Run all remote environment tests."""
        print("🚀 Starting Remote Environment Tests")
        print(f"📡 Environment: {self.test_results['environment']['remote_type']}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print("=" * 60)
        
        tests = [
            ("Environment Setup", self.test_environment_setup),
            ("Dependencies Installation", self.test_dependencies_install),
            ("Network Connectivity", self.test_network_connectivity),
            ("Recorder Availability", self.test_recorder_availability),
            ("Unit Tests", self.test_unit_tests),
            ("Evaluation Demo Mode", self.test_evaluation_demo_mode),
        ]
        
        passed_tests = 0
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed_tests += 1
        
        # Overall status
        total_tests = len(tests)
        success_rate = passed_tests / total_tests
        
        if success_rate >= 0.8:
            self.test_results["overall_status"] = "passed"
            status_emoji = "✅"
        elif success_rate >= 0.6:
            self.test_results["overall_status"] = "partial"
            status_emoji = "⚠️"
        else:
            self.test_results["overall_status"] = "failed"
            status_emoji = "❌"
        
        print("=" * 60)
        print(f"{status_emoji} Overall Status: {self.test_results['overall_status'].upper()}")
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1%})")
        
        # Save results
        results_file = self.project_root / "remote_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"📄 Results saved to: {results_file}")
        
        return self.test_results["overall_status"] != "failed"


def main():
    """Main function to run remote environment tests."""
    tester = RemoteEnvironmentTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()