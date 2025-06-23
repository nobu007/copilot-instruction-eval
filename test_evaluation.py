"""
Tests for the GitHub Copilot evaluation setup.
"""

import unittest
import json
import os
import sys
from pathlib import Path

class TestEvaluationSetup(unittest.TestCase):
    """Test cases for the evaluation setup."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before any tests are run."""
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.instructions_file = os.path.join(cls.test_dir, "instructions.json")
        
    def test_instructions_file_exists(self):
        """Test that the instructions file exists."""
        self.assertTrue(
            os.path.exists(self.instructions_file),
            f"Instructions file not found at {self.instructions_file}"
        )
    
    def test_instructions_file_format(self):
        """Test that the instructions file has the correct format."""
        try:
            with open(self.instructions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.assertIn("instructions", data)
            self.assertIsInstance(data["instructions"], list)
            self.assertGreater(len(data["instructions"]), 0, "No instructions found in the file")
            
            # Check each instruction has required fields
            for instruction in data["instructions"]:
                self.assertIn("id", instruction)
                self.assertIn("type", instruction)
                self.assertIn("title", instruction)
                self.assertIn("description", instruction)
                
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON in instructions file: {e}")
    
    def test_required_packages(self):
        """Test that required Python packages can be imported."""
        try:
            import requests
            import pandas
            import numpy
            import matplotlib
            import nltk
            from openai import OpenAI
            import pytest
        except ImportError as e:
            self.fail(f"Failed to import required package: {e}")

class TestAgentEndpoints(unittest.TestCase):
    """Test cases for agent API endpoints."""
    
    def test_agent_v1_endpoint(self):
        """Test that agent_v1 endpoint is accessible."""
        # This is a placeholder - in a real test, you would make an actual API call
        # and check for a successful response
        self.skipTest("Agent endpoint tests require actual API endpoints")
        
    def test_agent_v2_endpoint(self):
        """Test that agent_v2 endpoint is accessible."""
        # This is a placeholder - in a real test, you would make an actual API call
        # and check for a successful response
        self.skipTest("Agent endpoint tests require actual API endpoints")

if __name__ == "__main__":
    unittest.main()
