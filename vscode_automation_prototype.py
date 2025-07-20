#!/usr/bin/env python3
"""
VSCode Local Automation Prototype for Ubuntu 24.04
PyAutoGUI + OpenCV based screen automation for VSCode Copilot interaction
"""

import os
import sys
import time
import subprocess
import logging
import cv2
import numpy as np
import pyautogui
import psutil
from PIL import Image, ImageGrab
from datetime import datetime
import json

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"vscode_automation_{TIMESTAMP}.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class VSCodeAutomation:
    def __init__(self, project_path=None):
        self.project_path = project_path or os.getcwd()
        self.vscode_process = None
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")
        
    def launch_vscode(self):
        """Launch VSCode with the specified project path"""
        try:
            logger.info(f"Launching VSCode with project: {self.project_path}")
            
            # Launch VSCode
            cmd = ["code", self.project_path]
            self.vscode_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info(f"VSCode launched with PID: {self.vscode_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch VSCode: {e}")
            return False
    
    def wait_for_vscode_ready(self, timeout=30):
        """Wait for VSCode to be fully loaded and ready"""
        logger.info("Waiting for VSCode to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Take screenshot
                screenshot = ImageGrab.grab()
                screenshot_np = np.array(screenshot)
                
                # Check if VSCode window is visible by looking for characteristic elements
                if self._detect_vscode_window(screenshot_np):
                    logger.info("VSCode window detected and ready")
                    time.sleep(2)  # Additional wait for full initialization
                    return True
                    
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error during VSCode detection: {e}")
                time.sleep(1)
        
        logger.error(f"VSCode not ready after {timeout} seconds")
        return False
    
    def _detect_vscode_window(self, screenshot):
        """Detect if VSCode window is visible and active"""
        try:
            # Convert to grayscale for template matching
            gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            
            # Look for VSCode-specific UI elements
            # Check for dark theme (common VSCode appearance)
            dark_pixels = np.sum(gray < 50)
            total_pixels = gray.shape[0] * gray.shape[1]
            dark_ratio = dark_pixels / total_pixels
            
            # VSCode typically has a high ratio of dark pixels
            if dark_ratio > 0.3:
                logger.debug(f"Dark theme detected (ratio: {dark_ratio:.2f})")
                
                # Additional check: look for window title area
                # Check top portion of screen for title bar
                top_portion = gray[:100, :]
                if np.mean(top_portion) < 100:  # Dark title bar
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in VSCode window detection: {e}")
            return False
    
    def find_ui_element(self, template_name, confidence=0.8):
        """Find UI element using template matching"""
        try:
            # Take screenshot
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            
            # For now, we'll use simple color-based detection
            # In a full implementation, we would use pre-trained templates
            
            if template_name == "copilot_chat":
                return self._find_copilot_chat_button(screenshot_np)
            elif template_name == "command_palette":
                return self._find_command_palette_area(screenshot_np)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding UI element {template_name}: {e}")
            return None
    
    def _find_copilot_chat_button(self, screenshot):
        """Find GitHub Copilot chat button/panel"""
        # This is a simplified implementation
        # In practice, we would train a model or use template matching
        
        # Look for sidebar area (typically on the left)
        height, width = screenshot.shape[:2]
        sidebar_width = width // 6  # Approximate sidebar width
        sidebar = screenshot[:, :sidebar_width]
        
        # Return approximate position for Copilot icon in sidebar
        # This would be replaced with actual detection logic
        return (sidebar_width // 2, height // 3)
    
    def _find_command_palette_area(self, screenshot):
        """Find command palette area"""
        height, width = screenshot.shape[:2]
        # Command palette typically appears at top center
        return (width // 2, height // 4)
    
    def open_copilot_chat(self):
        """Open GitHub Copilot chat panel"""
        try:
            logger.info("Opening Copilot chat...")
            
            # Method 1: Use keyboard shortcut
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(2)
            
            # Verify if chat panel opened
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            
            # Simple verification - check if right panel appeared
            if self._verify_chat_panel_open(screenshot_np):
                logger.info("Copilot chat panel opened successfully")
                return True
            
            # Method 2: Try clicking on Copilot icon if shortcut failed
            copilot_pos = self.find_ui_element("copilot_chat")
            if copilot_pos:
                pyautogui.click(copilot_pos[0], copilot_pos[1])
                time.sleep(2)
                return True
            
            logger.warning("Failed to open Copilot chat panel")
            return False
            
        except Exception as e:
            logger.error(f"Error opening Copilot chat: {e}")
            return False
    
    def _verify_chat_panel_open(self, screenshot):
        """Verify if chat panel is open"""
        # Simple check - look for changes in right side of screen
        height, width = screenshot.shape[:2]
        right_panel = screenshot[:, int(width * 0.7):]
        
        # Check if there's content in the right panel area
        gray_panel = cv2.cvtColor(right_panel, cv2.COLOR_RGB2GRAY)
        return np.std(gray_panel) > 10  # Some variation indicates content
    
    def send_message_to_copilot(self, message):
        """Send a message to Copilot chat"""
        try:
            logger.info(f"Sending message to Copilot: {message}")
            
            # Find chat input area (typically at bottom of chat panel)
            screenshot = ImageGrab.grab()
            height, width = screenshot.size
            
            # Click in approximate chat input area (bottom right)
            chat_input_x = int(width * 0.85)
            chat_input_y = int(height * 0.9)
            
            pyautogui.click(chat_input_x, chat_input_y)
            time.sleep(1)
            
            # Type the message
            pyautogui.typewrite(message)
            time.sleep(1)
            
            # Send the message (Enter key)
            pyautogui.press('enter')
            time.sleep(2)
            
            logger.info("Message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to Copilot: {e}")
            return False
    
    def take_screenshot(self, filename=None):
        """Take a screenshot for debugging/logging"""
        try:
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            screenshot_path = os.path.join(LOG_DIR, filename)
            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)
            
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources and close VSCode if needed"""
        try:
            if self.vscode_process and self.vscode_process.poll() is None:
                logger.info("Terminating VSCode process...")
                self.vscode_process.terminate()
                time.sleep(2)
                
                if self.vscode_process.poll() is None:
                    self.vscode_process.kill()
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main execution function"""
    logger.info("=== VSCode Automation Prototype Started ===")
    
    # Initialize automation
    project_path = "/home/jinno/copilot-instruction-eval"
    automation = VSCodeAutomation(project_path)
    
    try:
        # Step 1: Launch VSCode
        if not automation.launch_vscode():
            logger.error("Failed to launch VSCode")
            return False
        
        # Step 2: Wait for VSCode to be ready
        if not automation.wait_for_vscode_ready():
            logger.error("VSCode not ready")
            return False
        
        # Step 3: Take initial screenshot
        automation.take_screenshot("initial_state.png")
        
        # Step 4: Open Copilot chat
        if not automation.open_copilot_chat():
            logger.error("Failed to open Copilot chat")
            return False
        
        # Step 5: Take screenshot after opening chat
        automation.take_screenshot("copilot_opened.png")
        
        # Step 6: Send test message
        test_message = "Hello, can you help me write a Python function?"
        if automation.send_message_to_copilot(test_message):
            logger.info("Test message sent successfully")
        
        # Step 7: Take final screenshot
        automation.take_screenshot("final_state.png")
        
        # Wait a bit to see the response
        logger.info("Waiting for Copilot response...")
        time.sleep(10)
        
        automation.take_screenshot("with_response.png")
        
        logger.info("=== VSCode Automation Prototype Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False
        
    finally:
        automation.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
