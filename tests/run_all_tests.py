#!/usr/bin/env python3
"""
Comprehensive test runner for the Copilot Instruction Evaluation System.

This script runs all tests in the test suite and provides detailed reporting.
"""

import unittest
import sys
import os
import time
import json
from pathlib import Path
from io import StringIO


class TestResult:
    """Container for test execution results."""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.duration = 0
        self.failures = []
        self.errors = []


class ComprehensiveTestRunner:
    """Custom test runner with detailed reporting."""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.result = TestResult()
    
    def run_tests(self, test_suite):
        """Run the test suite and collect results."""
        start_time = time.time()
        
        # Capture test output
        test_output = StringIO()
        runner = unittest.TextTestRunner(
            stream=test_output,
            verbosity=self.verbosity,
            buffer=True
        )
        
        # Run tests
        test_result = runner.run(test_suite)
        
        # Collect results
        self.result.duration = time.time() - start_time
        self.result.total_tests = test_result.testsRun
        self.result.failed_tests = len(test_result.failures)
        self.result.error_tests = len(test_result.errors)
        self.result.skipped_tests = len(test_result.skipped)
        self.result.passed_tests = (
            self.result.total_tests - 
            self.result.failed_tests - 
            self.result.error_tests - 
            self.result.skipped_tests
        )
        
        self.result.failures = test_result.failures
        self.result.errors = test_result.errors
        
        return self.result, test_output.getvalue()
    
    def print_summary(self, result, output):
        """Print comprehensive test summary."""
        print("=" * 70)
        print("🧪 COPILOT INSTRUCTION EVALUATION SYSTEM - TEST RESULTS")
        print("=" * 70)
        
        # Overall summary
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests:  {result.total_tests}")
        print(f"   ✅ Passed:    {result.passed_tests}")
        print(f"   ❌ Failed:    {result.failed_tests}")
        print(f"   🚨 Errors:    {result.error_tests}")
        print(f"   ⏭️  Skipped:   {result.skipped_tests}")
        print(f"   ⏱️  Duration:  {result.duration:.2f}s")
        
        # Success rate
        if result.total_tests > 0:
            success_rate = (result.passed_tests / result.total_tests) * 100
            print(f"   📈 Success:   {success_rate:.1f}%")
        
        # Overall status
        print(f"\n🎯 OVERALL STATUS: ", end="")
        if result.failed_tests == 0 and result.error_tests == 0:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        
        # Detailed failure information
        if result.failures:
            print(f"\n❌ FAILURES ({len(result.failures)}):")
            for i, (test, traceback) in enumerate(result.failures, 1):
                print(f"   {i}. {test}")
                print(f"      {traceback.strip().split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            print(f"\n🚨 ERRORS ({len(result.errors)}):")
            for i, (test, traceback) in enumerate(result.errors, 1):
                print(f"   {i}. {test}")
                print(f"      {traceback.strip().split('Exception:')[-1].strip()}")
        
        # Test categories breakdown
        print(f"\n📂 TEST CATEGORIES:")
        categories = self._analyze_test_categories(output)
        for category, count in categories.items():
            print(f"   {category}: {count} tests")
        
        print("\n" + "=" * 70)
    
    def _analyze_test_categories(self, output):
        """Analyze test output to categorize tests."""
        categories = {
            "Recorder Tests": 0,
            "Evaluation Tests": 0,
            "Integration Tests": 0,
            "Configuration Tests": 0,
            "Other Tests": 0
        }
        
        lines = output.split('\n')
        for line in lines:
            if 'test_' in line:
                if 'recorder' in line.lower():
                    categories["Recorder Tests"] += 1
                elif 'evaluation' in line.lower():
                    categories["Evaluation Tests"] += 1
                elif 'integration' in line.lower():
                    categories["Integration Tests"] += 1
                elif 'config' in line.lower():
                    categories["Configuration Tests"] += 1
                else:
                    categories["Other Tests"] += 1
        
        return categories
    
    def save_results(self, result, output, filename="test_results.json"):
        """Save test results to JSON file."""
        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": result.total_tests,
                "passed_tests": result.passed_tests,
                "failed_tests": result.failed_tests,
                "error_tests": result.error_tests,
                "skipped_tests": result.skipped_tests,
                "duration": result.duration,
                "success_rate": (result.passed_tests / result.total_tests * 100) if result.total_tests > 0 else 0
            },
            "failures": [str(test) for test, _ in result.failures],
            "errors": [str(test) for test, _ in result.errors]
        }
        
        # Ensure results directory exists
        results_dir = Path(__file__).parent.parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / filename
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Test results saved to: {results_file}")


def discover_tests():
    """Discover all test modules in the tests directory."""
    test_dir = Path(__file__).parent
    test_loader = unittest.TestLoader()
    
    # Discover all tests in the tests directory
    test_suite = test_loader.discover(str(test_dir), pattern='test_*.py')
    
    return test_suite


def main():
    """Main function to run all tests."""
    print("🚀 Starting Comprehensive Test Suite...")
    print(f"📁 Test Directory: {Path(__file__).parent}")
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Discover and run tests
    test_suite = discover_tests()
    runner = ComprehensiveTestRunner(verbosity=2)
    
    try:
        result, output = runner.run_tests(test_suite)
        runner.print_summary(result, output)
        runner.save_results(result, output)
        
        # Exit with appropriate code
        sys.exit(0 if result.failed_tests == 0 and result.error_tests == 0 else 1)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()