#!/usr/bin/env python3
"""
Precise VSCode Automation using YOLO-detected UI coordinates
Combines UI detection with precise PyAutoGUI operations
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
from yolo_ui_detection import VSCodeUIDetector

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"precise_automation_{TIMESTAMP}.log")

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

class PreciseVSCodeAutomation:
    def __init__(self, project_path=None):
        self.project_path = project_path or os.getcwd()
        self.vscode_process = None
        self.screen_width, self.screen_height = pyautogui.size()
        self.ui_detector = VSCodeUIDetector()
        self.detected_elements = None
        
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
                # Use UI detector to check if VSCode is ready
                analysis = self.ui_detector.analyze_vscode_ui(save_analysis=False)
                
                if analysis and analysis["elements_detected"].get("vscode_window"):
                    logger.info("VSCode window detected and ready")
                    self.detected_elements = analysis["elements_detected"]
                    time.sleep(2)  # Additional wait for full initialization
                    return True
                    
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error during VSCode detection: {e}")
                time.sleep(1)
        
        logger.error(f"VSCode not ready after {timeout} seconds")
        return False
    
    def detect_ui_elements(self):
        """Detect current UI elements using YOLO-based detection"""
        try:
            logger.info("Detecting UI elements...")
            
            analysis = self.ui_detector.analyze_vscode_ui(save_analysis=True)
            
            if analysis:
                self.detected_elements = analysis["elements_detected"]
                logger.info("UI elements detected successfully")
                return True
            else:
                logger.error("Failed to detect UI elements")
                return False
                
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            return False
    
    def open_copilot_chat(self):
        """Open GitHub Copilot chat panel"""
        try:
            logger.info("Opening Copilot chat...")
            
            # Method 1: Use keyboard shortcut
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(3)
            
            # Re-detect UI elements after opening chat
            if self.detect_ui_elements():
                # Check if chat panel is detected
                if self.detected_elements.get("chat_panel"):
                    logger.info("Copilot chat panel opened successfully")
                    return True
            
            logger.warning("Failed to confirm Copilot chat panel opening")
            return False
            
        except Exception as e:
            logger.error(f"Error opening Copilot chat: {e}")
            return False
    
    def find_best_input_field(self):
        """Find the most likely chat input field from detected elements"""
        try:
            input_fields = self.detected_elements.get("input_fields", [])
            
            if not input_fields:
                logger.error("No input fields detected")
                return None
            
            # Find input field in bottom portion of screen (most likely chat input)
            bottom_threshold = self.screen_height * 0.8
            
            bottom_inputs = []
            for x, y, w, h in input_fields:
                if y > bottom_threshold and w > 200:  # Bottom area and reasonably wide
                    bottom_inputs.append((x, y, w, h))
            
            if bottom_inputs:
                # Choose the widest input field in bottom area
                best_input = max(bottom_inputs, key=lambda field: field[2])  # Sort by width
                logger.info(f"Best input field found: {best_input}")
                return best_input
            else:
                # Fallback: choose the widest input field overall
                best_input = max(input_fields, key=lambda field: field[2])
                logger.info(f"Fallback input field: {best_input}")
                return best_input
                
        except Exception as e:
            logger.error(f"Error finding input field: {e}")
            return None
    
    def send_message_to_copilot(self, message):
        """Send a message to Copilot chat using detected coordinates"""
        try:
            logger.info(f"Sending message to Copilot: {message}")
            
            # Find the best input field
            input_field = self.find_best_input_field()
            
            if not input_field:
                logger.error("No suitable input field found")
                return False
            
            x, y, w, h = input_field
            
            # Calculate center of input field
            center_x = x + w // 2
            center_y = y + h // 2
            
            logger.info(f"Clicking input field at: ({center_x}, {center_y})")
            
            # Take screenshot before input
            screenshot_before = ImageGrab.grab()
            screenshot_before.save(os.path.join(LOG_DIR, f"before_precise_input_{TIMESTAMP}.png"))
            
            # Click on the input field
            pyautogui.click(center_x, center_y)
            time.sleep(1)
            
            # Clear any existing text
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            
            # Type the message
            logger.info(f"Typing message: {message}")
            pyautogui.typewrite(message, interval=0.05)
            time.sleep(2)
            
            # Take screenshot after typing
            screenshot_after_type = ImageGrab.grab()
            screenshot_after_type.save(os.path.join(LOG_DIR, f"after_precise_typing_{TIMESTAMP}.png"))
            
            # Send the message (Enter key)
            logger.info("Pressing Enter key")
            pyautogui.press('enter')
            time.sleep(3)
            
            # Take screenshot after Enter
            screenshot_after_enter = ImageGrab.grab()
            screenshot_after_enter.save(os.path.join(LOG_DIR, f"after_precise_enter_{TIMESTAMP}.png"))
            
            logger.info("Message sent successfully using precise coordinates")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to Copilot: {e}")
            return False
    
    def take_screenshot(self, filename=None):
        """Take a screenshot for debugging/logging"""
        try:
            if not filename:
                filename = f"precise_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
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
    logger.info("=== Precise VSCode Automation Started ===")
    
    # Initialize automation
    project_path = "/home/jinno/copilot-instruction-eval"
    automation = PreciseVSCodeAutomation(project_path)
    
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
        automation.take_screenshot("precise_initial_state.png")
        
        # Step 4: Open Copilot chat
        if not automation.open_copilot_chat():
            logger.error("Failed to open Copilot chat")
            return False
        
        # Step 5: Take screenshot after opening chat
        automation.take_screenshot("precise_copilot_opened.png")
        
        # Step 6: Send test message using precise coordinates
        test_message = "Hello! Can you help me write a Python function to calculate the factorial of a number?"
        if automation.send_message_to_copilot(test_message):
            logger.info("Test message sent successfully using precise coordinates")
        else:
            logger.error("Failed to send test message")
            return False
        
        # Step 7: Take final screenshot
        automation.take_screenshot("precise_final_state.png")
        
        # Wait a bit to see the response
        logger.info("Waiting for Copilot response...")
        time.sleep(10)
        
        automation.take_screenshot("precise_with_response.png")
        
        logger.info("=== Precise VSCode Automation Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False
        
    finally:
        automation.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
