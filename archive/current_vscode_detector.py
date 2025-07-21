#!/usr/bin/env python3
"""
Current VSCode Instance Detector
Detects which VSCode instance the user is currently using and provides automation targeting
"""

import os
import sys
import subprocess
import psutil
import time
import logging
from datetime import datetime
import pyautogui
import cv2
import numpy as np

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"vscode_detector_{TIMESTAMP}.log")

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

class CurrentVSCodeDetector:
    def __init__(self):
        self.vscode_instances = []
        
    def detect_vscode_processes(self):
        """Detect all running VSCode-related processes"""
        try:
            logger.info("=== Detecting VSCode Processes ===")
            
            vscode_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    pinfo = proc.info
                    name = pinfo['name'].lower()
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    # Check for various VSCode processes
                    if any(keyword in name for keyword in ['code', 'electron']) or \
                       any(keyword in cmdline.lower() for keyword in ['vscode', 'code-server', 'code tunnel']):
                        
                        # Skip helper processes
                        if any(skip in cmdline.lower() for skip in ['--type=', 'gpu-process', 'utility']):
                            continue
                            
                        vscode_processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'cmdline': cmdline,
                            'create_time': pinfo['create_time'],
                            'type': self.classify_vscode_process(cmdline)
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by creation time (newest first)
            vscode_processes.sort(key=lambda x: x['create_time'], reverse=True)
            
            logger.info(f"Found {len(vscode_processes)} VSCode-related processes:")
            for i, proc in enumerate(vscode_processes):
                logger.info(f"  {i+1}. PID={proc['pid']}, Type={proc['type']}, Name={proc['name']}")
                logger.info(f"     Command: {proc['cmdline'][:100]}...")
            
            self.vscode_instances = vscode_processes
            return vscode_processes
            
        except Exception as e:
            logger.error(f"Error detecting VSCode processes: {e}")
            return []
    
    def classify_vscode_process(self, cmdline):
        """Classify the type of VSCode process"""
        cmdline_lower = cmdline.lower()
        
        if 'code-server' in cmdline_lower:
            return 'VSCode Server'
        elif 'code tunnel' in cmdline_lower:
            return 'VSCode Tunnel'
        elif 'remote' in cmdline_lower:
            return 'VSCode Remote'
        elif 'electron' in cmdline_lower and 'vscode' in cmdline_lower:
            return 'VSCode Desktop'
        elif '/usr/share/code' in cmdline_lower or '/snap/code' in cmdline_lower:
            return 'VSCode Desktop (System)'
        elif 'chrome' in cmdline_lower and 'vscode.dev' in cmdline_lower:
            return 'VSCode Web (Chrome)'
        else:
            return 'VSCode (Unknown)'
    
    def detect_active_vscode_window(self):
        """Detect which VSCode window is currently active/visible"""
        try:
            logger.info("=== Detecting Active VSCode Window ===")
            
            # Take a screenshot to analyze current screen
            screenshot = pyautogui.screenshot()
            screenshot_path = os.path.join(LOG_DIR, f"current_screen_{TIMESTAMP}.png")
            screenshot.save(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Convert to OpenCV format for analysis
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Look for VSCode-specific UI elements
            vscode_indicators = self.find_vscode_ui_indicators(screenshot_cv)
            
            if vscode_indicators:
                logger.info("✅ VSCode UI detected in current screen")
                for indicator in vscode_indicators:
                    logger.info(f"  - {indicator}")
                return True
            else:
                logger.warning("❌ No VSCode UI detected in current screen")
                return False
                
        except Exception as e:
            logger.error(f"Error detecting active VSCode window: {e}")
            return False
    
    def find_vscode_ui_indicators(self, image):
        """Find VSCode-specific UI indicators in the image"""
        indicators = []
        
        try:
            # Convert to grayscale for text detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for common VSCode UI elements
            # 1. Check for dark theme (common in VSCode)
            dark_pixels = np.sum(gray < 50)
            total_pixels = gray.shape[0] * gray.shape[1]
            dark_ratio = dark_pixels / total_pixels
            
            if dark_ratio > 0.3:  # More than 30% dark pixels
                indicators.append(f"Dark theme detected ({dark_ratio:.1%} dark pixels)")
            
            # 2. Look for typical VSCode layout patterns
            height, width = gray.shape
            
            # Check for sidebar (left edge with different brightness)
            left_edge = gray[:, :width//10]  # Left 10% of screen
            main_area = gray[:, width//4:width*3//4]  # Middle 50% of screen
            
            left_mean = np.mean(left_edge)
            main_mean = np.mean(main_area)
            
            if abs(left_mean - main_mean) > 20:  # Significant brightness difference
                indicators.append(f"Sidebar pattern detected (left: {left_mean:.1f}, main: {main_mean:.1f})")
            
            # 3. Check for bottom panel (terminal/output area)
            bottom_area = gray[height*3//4:, :]  # Bottom 25% of screen
            top_area = gray[:height//4, :]  # Top 25% of screen
            
            bottom_mean = np.mean(bottom_area)
            top_mean = np.mean(top_area)
            
            if abs(bottom_mean - top_mean) > 15:  # Different brightness patterns
                indicators.append(f"Bottom panel pattern detected (bottom: {bottom_mean:.1f}, top: {top_mean:.1f})")
            
            # 4. Look for rectangular regions that could be editor tabs
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            tab_like_regions = 0
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Tab-like: wide, not too tall, in upper area
                if (w > 80 and h > 20 and h < 50 and aspect_ratio > 2 and y < height // 3):
                    tab_like_regions += 1
            
            if tab_like_regions > 2:
                indicators.append(f"Tab-like regions detected ({tab_like_regions} regions)")
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error finding VSCode UI indicators: {e}")
            return []
    
    def get_recommended_automation_target(self):
        """Get recommendation for which VSCode instance to target for automation"""
        try:
            logger.info("=== Getting Automation Target Recommendation ===")
            
            # Detect processes and active window
            processes = self.detect_vscode_processes()
            active_window = self.detect_active_vscode_window()
            
            recommendations = []
            
            if active_window:
                recommendations.append({
                    'method': 'Screen Automation',
                    'description': 'Target the currently visible VSCode window using PyAutoGUI',
                    'confidence': 'High',
                    'approach': 'Use PyAutoGUI to interact with the visible VSCode interface'
                })
            
            # Check for different process types
            for proc in processes:
                if proc['type'] == 'VSCode Desktop':
                    recommendations.append({
                        'method': 'Desktop VSCode',
                        'description': f'Target desktop VSCode process (PID: {proc["pid"]})',
                        'confidence': 'Medium',
                        'approach': 'Launch new VSCode instance or focus existing desktop instance'
                    })
                elif proc['type'] == 'VSCode Server':
                    recommendations.append({
                        'method': 'VSCode Server',
                        'description': f'Target VSCode Server instance (PID: {proc["pid"]})',
                        'confidence': 'Low',
                        'approach': 'Use browser automation to interact with VSCode Server web interface'
                    })
            
            # Check for Chrome with vscode.dev
            chrome_processes = [p for p in processes if 'chrome' in p['cmdline'].lower()]
            for proc in chrome_processes:
                if 'vscode.dev' in proc['cmdline']:
                    recommendations.append({
                        'method': 'VSCode Web (Chrome)',
                        'description': f'Target VSCode Web in Chrome (PID: {proc["pid"]})',
                        'confidence': 'Medium',
                        'approach': 'Use Selenium to interact with VSCode Web interface in Chrome'
                    })
            
            logger.info("Automation recommendations:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec['method']} (Confidence: {rec['confidence']})")
                logger.info(f"     {rec['description']}")
                logger.info(f"     Approach: {rec['approach']}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting automation recommendations: {e}")
            return []
    
    def create_targeted_automation_script(self, target_method='Screen Automation'):
        """Create an automation script targeting the specified method"""
        try:
            logger.info(f"=== Creating Targeted Automation Script for: {target_method} ===")
            
            if target_method == 'Screen Automation':
                # Create script that targets the currently visible VSCode
                script_content = '''#!/usr/bin/env python3
"""
Targeted VSCode Automation - Screen Based
Targets the currently visible VSCode window
"""

import pyautogui
import time
import logging

def send_prompt_to_current_vscode():
    """Send prompt to the currently visible VSCode window"""
    try:
        # Wait a moment for user to focus on VSCode
        print("Please make sure VSCode is visible and focused...")
        time.sleep(3)
        
        # Try to open Copilot chat with Ctrl+Shift+I
        pyautogui.hotkey('ctrl', 'shift', 'i')
        time.sleep(2)
        
        # Type the prompt
        prompt = "Hello! Can you help me write a Python function to calculate the factorial of a number?"
        pyautogui.typewrite(prompt, interval=0.05)
        time.sleep(1)
        
        # Press Enter
        pyautogui.press('enter')
        
        print("✅ Prompt sent to current VSCode window")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    send_prompt_to_current_vscode()
'''
                
                script_path = os.path.join(os.getcwd(), "targeted_vscode_automation.py")
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                logger.info(f"✅ Targeted automation script created: {script_path}")
                return script_path
                
        except Exception as e:
            logger.error(f"Error creating targeted automation script: {e}")
            return None

def main():
    """Main function for VSCode detection and targeting"""
    logger.info("=== VSCode Instance Detection and Targeting ===")
    
    try:
        detector = CurrentVSCodeDetector()
        
        # Get recommendations
        recommendations = detector.get_recommended_automation_target()
        
        if recommendations:
            # Use the highest confidence recommendation
            best_rec = max(recommendations, key=lambda x: {'High': 3, 'Medium': 2, 'Low': 1}[x['confidence']])
            logger.info(f"🎯 Recommended approach: {best_rec['method']}")
            
            # Create targeted script
            script_path = detector.create_targeted_automation_script(best_rec['method'])
            
            if script_path:
                logger.info("=== Detection and Targeting Completed Successfully ===")
                logger.info(f"Run the targeted script: python {script_path}")
            else:
                logger.error("Failed to create targeted automation script")
        else:
            logger.warning("No VSCode instances detected for automation")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
