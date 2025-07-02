"""
Test cases for the Cascade Recorder functionality.
"""

import unittest
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestRecorderActions(unittest.TestCase):
    """Test cases for recorder action handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid import issues
        import sys
        cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'copilot-recorder-poc')
        if cascade_path not in sys.path:
            sys.path.insert(0, cascade_path)
            
        from cascade_recorder.actions import Action
        self.Action = Action
    
    def test_action_creation(self):
        """Test action object creation."""
        action = self.Action.now(
            action_type="click",
            target_element={"tag": "button", "id": "test-btn"},
            comment="Test click action"
        )
        
        self.assertEqual(action.action_type, "click")
        self.assertIsNotNone(action.timestamp)
        self.assertEqual(action.target_element["tag"], "button")
        self.assertEqual(action.comment, "Test click action")
    
    def test_action_to_dict(self):
        """Test action serialization to dictionary."""
        action = self.Action.now(
            action_type="input",
            input_text="test input",
            target_element={"tag": "input", "id": "text-field"}
        )
        
        action_dict = action.to_dict()
        
        self.assertIsInstance(action_dict, dict)
        self.assertEqual(action_dict["action_type"], "input")
        self.assertEqual(action_dict["input_text"], "test input")
        self.assertIn("timestamp", action_dict)


class TestRecorderConfig(unittest.TestCase):
    """Test cases for recorder configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        import sys
        cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'copilot-recorder-poc')
        if cascade_path not in sys.path:
            sys.path.insert(0, cascade_path)
    
    def test_config_imports(self):
        """Test that config module imports correctly."""
        try:
            from cascade_recorder import config
            # Test that essential config values exist
            self.assertTrue(hasattr(config, 'DEBUG_PORT'))
            self.assertTrue(hasattr(config, 'RECORDED_ACTIONS_JSON_PATH'))
        except ImportError as e:
            self.fail(f"Failed to import config module: {e}")


class TestRecorderIntegration(unittest.TestCase):
    """Integration tests for the recorder system."""
    
    def setUp(self):
        """Set up test fixtures."""
        import sys
        cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'copilot-recorder-poc')
        if cascade_path not in sys.path:
            sys.path.insert(0, cascade_path)
    
    @patch('cascade_recorder.browser.webdriver.Chrome')
    def test_recorder_initialization(self, mock_driver):
        """Test recorder initialization without actual browser."""
        try:
            from cascade_recorder.recorder import Recorder
            
            # Mock driver instance
            mock_driver_instance = Mock()
            mock_driver_instance.current_url = "https://example.com"
            
            recorder = Recorder(mock_driver_instance)
            self.assertIsNotNone(recorder)
            self.assertEqual(len(recorder.recorded), 0)
            self.assertFalse(recorder._is_recording)
            
        except ImportError as e:
            self.fail(f"Failed to import recorder module: {e}")
    
    def test_recorded_actions_json_structure(self):
        """Test that recorded actions JSON has correct structure."""
        # Check if recorded actions file exists and has valid structure
        cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'copilot-recorder-poc')
        actions_file = os.path.join(cascade_path, 'cascade_recorder', 'recorded_actions.json')
        
        if os.path.exists(actions_file):
            with open(actions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertIsInstance(data, list)
            
            # Test structure of each action if data exists
            if data:
                action = data[0]
                required_fields = ['action_type', 'timestamp']
                for field in required_fields:
                    self.assertIn(field, action)


if __name__ == '__main__':
    unittest.main()