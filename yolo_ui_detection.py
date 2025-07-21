#!/usr/bin/env python3
"""
YOLO-based UI Detection for VSCode Automation
Detects UI elements like buttons, input fields, chat panels using computer vision
"""

import os
import sys
import time
import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageGrab
import logging
from datetime import datetime
import json
import torch
from ultralytics import YOLO

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"yolo_ui_detection_{TIMESTAMP}.log")

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

class VSCodeUIDetector:
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")
        
        # Initialize YOLO model (we'll use a pre-trained model and adapt it)
        # For now, we'll use traditional computer vision methods as a foundation
        self.ui_elements = {}
        
    def capture_screen(self, save_path=None):
        """Capture current screen"""
        try:
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            
            if save_path:
                screenshot.save(save_path)
                logger.info(f"Screenshot saved: {save_path}")
            
            return screenshot_np
            
        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None
    
    def detect_vscode_window(self, screenshot):
        """Detect VSCode window and its boundaries"""
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            
            # VSCode typically has dark theme with specific characteristics
            # Look for title bar, sidebar, and main editor area
            
            # Find dark regions (VSCode's dark theme)
            dark_mask = gray < 50
            
            # Find contours of dark regions
            contours, _ = cv2.findContours(dark_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest dark region (likely VSCode window)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # Validate if this looks like a VSCode window
                if w > 800 and h > 600:  # Reasonable window size
                    logger.info(f"VSCode window detected: ({x}, {y}, {w}, {h})")
                    return (x, y, w, h)
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting VSCode window: {e}")
            return None
    
    def detect_sidebar(self, screenshot, vscode_bounds=None):
        """Detect VSCode sidebar (left panel)"""
        try:
            if vscode_bounds:
                x, y, w, h = vscode_bounds
                # Focus on left portion of VSCode window
                sidebar_region = screenshot[y:y+h, x:x+int(w*0.2)]
            else:
                # Use left portion of screen
                sidebar_region = screenshot[:, :int(self.screen_width*0.2)]
            
            # Convert to grayscale
            gray_sidebar = cv2.cvtColor(sidebar_region, cv2.COLOR_RGB2GRAY)
            
            # Look for vertical lines and icons typical of sidebar
            edges = cv2.Canny(gray_sidebar, 50, 150)
            
            # Find vertical lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
            
            if lines is not None and len(lines) > 0:
                logger.info(f"Sidebar detected with {len(lines)} vertical elements")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting sidebar: {e}")
            return False
    
    def detect_copilot_chat_panel(self, screenshot, vscode_bounds=None):
        """Detect Copilot chat panel (typically on right side)"""
        try:
            if vscode_bounds:
                x, y, w, h = vscode_bounds
                # Focus on right portion of VSCode window
                chat_region = screenshot[y:y+h, x+int(w*0.7):x+w]
            else:
                # Use right portion of screen
                chat_region = screenshot[:, int(self.screen_width*0.7):]
            
            # Convert to grayscale
            gray_chat = cv2.cvtColor(chat_region, cv2.COLOR_RGB2GRAY)
            
            # Look for chat-like patterns
            # Chat panels typically have text areas, input fields, and buttons
            
            # Detect text regions (areas with moderate pixel variation)
            text_variance = cv2.Laplacian(gray_chat, cv2.CV_64F).var()
            
            # Detect potential input areas (horizontal lines at bottom)
            edges = cv2.Canny(gray_chat, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=50, maxLineGap=5)
            
            # Check for horizontal lines in bottom portion (input field)
            bottom_region = gray_chat[int(gray_chat.shape[0]*0.8):, :]
            bottom_edges = cv2.Canny(bottom_region, 50, 150)
            bottom_lines = cv2.HoughLinesP(bottom_edges, 1, np.pi/180, threshold=20, minLineLength=30, maxLineGap=5)
            
            if text_variance > 100 and bottom_lines is not None:
                logger.info(f"Copilot chat panel detected (text variance: {text_variance:.2f}, bottom lines: {len(bottom_lines)})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting chat panel: {e}")
            return False
    
    def detect_input_field(self, screenshot, region=None):
        """Detect input fields (text boxes, chat input)"""
        try:
            if region:
                x, y, w, h = region
                search_area = screenshot[y:y+h, x:x+w]
            else:
                search_area = screenshot
            
            # Convert to grayscale
            gray = cv2.cvtColor(search_area, cv2.COLOR_RGB2GRAY)
            
            # Input fields typically have rectangular borders
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            input_fields = []
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter for input field-like shapes (wide and not too tall)
                if w > 100 and h > 20 and h < 60 and w/h > 3:
                    input_fields.append((x, y, w, h))
            
            if input_fields:
                logger.info(f"Detected {len(input_fields)} potential input fields")
                return input_fields
            
            return []
            
        except Exception as e:
            logger.error(f"Error detecting input fields: {e}")
            return []
    
    def detect_buttons(self, screenshot, region=None):
        """Detect clickable buttons"""
        try:
            if region:
                x, y, w, h = region
                search_area = screenshot[y:y+h, x:x+w]
            else:
                search_area = screenshot
            
            # Convert to grayscale
            gray = cv2.cvtColor(search_area, cv2.COLOR_RGB2GRAY)
            
            # Buttons typically have distinct edges and consistent shapes
            edges = cv2.Canny(gray, 30, 100)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            buttons = []
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter for button-like shapes
                if 30 < w < 200 and 20 < h < 50 and 0.5 < w/h < 5:
                    buttons.append((x, y, w, h))
            
            if buttons:
                logger.info(f"Detected {len(buttons)} potential buttons")
                return buttons
            
            return []
            
        except Exception as e:
            logger.error(f"Error detecting buttons: {e}")
            return []
    
    def analyze_vscode_ui(self, save_analysis=True):
        """Comprehensive analysis of VSCode UI elements"""
        try:
            logger.info("Starting VSCode UI analysis...")
            
            # Capture current screen
            screenshot_path = os.path.join(LOG_DIR, f"ui_analysis_{TIMESTAMP}.png")
            screenshot = self.capture_screen(screenshot_path)
            
            if screenshot is None:
                return None
            
            analysis_results = {
                "timestamp": TIMESTAMP,
                "screen_resolution": (self.screen_width, self.screen_height),
                "elements_detected": {}
            }
            
            # Detect VSCode window
            vscode_bounds = self.detect_vscode_window(screenshot)
            if vscode_bounds:
                analysis_results["elements_detected"]["vscode_window"] = vscode_bounds
            
            # Detect sidebar
            sidebar_detected = self.detect_sidebar(screenshot, vscode_bounds)
            analysis_results["elements_detected"]["sidebar"] = sidebar_detected
            
            # Detect chat panel
            chat_panel_detected = self.detect_copilot_chat_panel(screenshot, vscode_bounds)
            analysis_results["elements_detected"]["chat_panel"] = chat_panel_detected
            
            # Detect input fields
            input_fields = self.detect_input_field(screenshot)
            analysis_results["elements_detected"]["input_fields"] = input_fields
            
            # Detect buttons
            buttons = self.detect_buttons(screenshot)
            analysis_results["elements_detected"]["buttons"] = buttons
            
            # Save analysis results
            if save_analysis:
                analysis_path = os.path.join(LOG_DIR, f"ui_analysis_{TIMESTAMP}.json")
                with open(analysis_path, 'w') as f:
                    json.dump(analysis_results, f, indent=2)
                logger.info(f"UI analysis saved: {analysis_path}")
            
            # Create annotated image
            self.create_annotated_image(screenshot, analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in UI analysis: {e}")
            return None
    
    def create_annotated_image(self, screenshot, analysis_results):
        """Create an annotated image showing detected UI elements"""
        try:
            # Create a copy for annotation
            annotated = screenshot.copy()
            
            # Draw VSCode window bounds
            if "vscode_window" in analysis_results["elements_detected"]:
                x, y, w, h = analysis_results["elements_detected"]["vscode_window"]
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(annotated, "VSCode Window", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw input fields
            input_fields = analysis_results["elements_detected"].get("input_fields", [])
            for i, (x, y, w, h) in enumerate(input_fields):
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(annotated, f"Input {i+1}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Draw buttons
            buttons = analysis_results["elements_detected"].get("buttons", [])
            for i, (x, y, w, h) in enumerate(buttons):
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(annotated, f"Btn {i+1}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # Save annotated image
            annotated_path = os.path.join(LOG_DIR, f"ui_annotated_{TIMESTAMP}.png")
            cv2.imwrite(annotated_path, cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))
            logger.info(f"Annotated image saved: {annotated_path}")
            
        except Exception as e:
            logger.error(f"Error creating annotated image: {e}")

def main():
    """Main function for UI detection testing"""
    logger.info("=== YOLO-based UI Detection Started ===")
    
    try:
        # Initialize detector
        detector = VSCodeUIDetector()
        
        # Wait a moment for user to prepare VSCode
        logger.info("Please ensure VSCode is open and visible...")
        time.sleep(3)
        
        # Analyze current UI
        analysis = detector.analyze_vscode_ui()
        
        if analysis:
            logger.info("=== UI Analysis Results ===")
            for element_type, data in analysis["elements_detected"].items():
                logger.info(f"{element_type}: {data}")
            
            logger.info("=== UI Detection Completed Successfully ===")
        else:
            logger.error("UI analysis failed")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
