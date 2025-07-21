#!/usr/bin/env python3
"""
Simple Screen Automation - Target Current Visible VSCode
Sends prompts to whatever VSCode is currently visible on screen
"""

import pyautogui
import time
import logging
import os
from datetime import datetime

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"screen_automation_{TIMESTAMP}.log")

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

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

def take_screenshot(name):
    """Take a screenshot for verification"""
    try:
        screenshot_path = os.path.join(LOG_DIR, f"screen_{name}_{TIMESTAMP}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return None

def send_prompt_to_current_screen():
    """Send prompt to the currently visible VSCode (whatever is on screen)"""
    try:
        logger.info("=== Simple Screen Automation Started ===")
        logger.info("⚠️  Please make sure the VSCode you want to target is visible and focused!")
        
        # Give user time to focus the correct VSCode window
        for i in range(5, 0, -1):
            print(f"Starting in {i} seconds... (Make sure your target VSCode is focused)")
            logger.info(f"Countdown: {i} seconds")
            time.sleep(1)
        
        # Take initial screenshot
        take_screenshot("before_automation")
        
        logger.info("🎯 Attempting to open Copilot chat...")
        
        # Try to open Copilot chat with Ctrl+Shift+I
        pyautogui.hotkey('ctrl', 'shift', 'i')
        time.sleep(2)
        
        # Take screenshot after opening chat
        take_screenshot("after_chat_open")
        
        logger.info("💬 Typing prompt...")
        
        # Type the prompt
        prompt = "Hello! Can you help me write a Python function to calculate the factorial of a number?"
        pyautogui.typewrite(prompt, interval=0.05)
        time.sleep(1)
        
        # Take screenshot after typing
        take_screenshot("after_typing")
        
        logger.info("⏎ Pressing Enter...")
        
        # Press Enter
        pyautogui.press('enter')
        time.sleep(2)
        
        # Take final screenshot
        take_screenshot("after_enter")
        
        logger.info("✅ Prompt sent to current screen!")
        logger.info("📸 Check the screenshots in evaluation_logs/ to verify the automation worked")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in screen automation: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("🎯 SIMPLE SCREEN AUTOMATION")
    print("=" * 60)
    print("This will send a prompt to whatever VSCode is currently visible.")
    print("Please:")
    print("1. Make sure your target VSCode window is visible and focused")
    print("2. Make sure GitHub Copilot is available in that VSCode")
    print("3. The automation will start in 5 seconds")
    print("=" * 60)
    
    success = send_prompt_to_current_screen()
    
    if success:
        print("✅ Automation completed! Check the logs and screenshots.")
    else:
        print("❌ Automation failed. Check the logs for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
