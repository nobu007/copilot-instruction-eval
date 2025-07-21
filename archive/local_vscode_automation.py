#!/usr/bin/env python3
"""
Local VSCode Desktop Automation
Targets ONLY the user's local VSCode Desktop window, excluding Windsurf/AI screens
"""

import pyautogui
import time
import logging
import os
import subprocess
import psutil
from datetime import datetime
import cv2
import numpy as np

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"local_vscode_{TIMESTAMP}.log")

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

class LocalVSCodeAutomation:
    def __init__(self):
        self.project_path = "/home/jinno/copilot-instruction-eval"
        
    def find_local_vscode_processes(self):
        """Find local VSCode Desktop processes (excluding Windsurf/AI)"""
        try:
            logger.info("=== Finding Local VSCode Desktop Processes ===")
            
            vscode_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    pinfo = proc.info
                    name = pinfo['name'].lower()
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    exe = pinfo['exe'] or ''
                    
                    # Look for LOCAL VSCode Desktop processes ONLY
                    is_local_vscode = False
                    
                    # STRICT CHECK: Must be LOCAL VSCode Desktop executable
                    if '/usr/share/code/code' in exe or '/snap/code/' in exe:
                        # Additional check: NOT a web/remote process
                        if not any(web_indicator in cmdline.lower() for web_indicator in 
                                 ['--remote', '--server', 'vscode.dev', 'github.dev', 'localhost', '127.0.0.1']):
                            is_local_vscode = True
                    elif 'code' in name and 'electron' in cmdline:
                        # Electron-based VSCode, but ensure it's local
                        if '/usr/share/code' in cmdline and not any(web_indicator in cmdline.lower() for web_indicator in 
                                                                  ['--remote', '--server', 'vscode.dev', 'github.dev']):
                            is_local_vscode = True
                    
                    # EXCLUDE Windsurf/AI processes
                    if 'windsurf' in exe.lower() or 'windsurf' in cmdline.lower():
                        logger.info(f"EXCLUDED Windsurf process: PID={pinfo['pid']}")
                        continue
                    
                    # EXCLUDE helper processes
                    if any(skip in cmdline.lower() for skip in ['--type=', 'gpu-process', 'utility', 'renderer']):
                        continue
                    
                    if is_local_vscode:
                        vscode_processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'exe': exe,
                            'cmdline': cmdline
                        })
                        logger.info(f"Found LOCAL VSCode Desktop: PID={pinfo['pid']}, exe={exe}")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info(f"Total local VSCode Desktop processes found: {len(vscode_processes)}")
            return vscode_processes
            
        except Exception as e:
            logger.error(f"Error finding VSCode processes: {e}")
            return []
    
    def launch_or_focus_local_vscode(self):
        """Launch local VSCode Desktop or focus existing window"""
        try:
            logger.info("=== Launching/Focusing Local VSCode Desktop ===")
            
            # Check if VSCode Desktop is already running
            existing_processes = self.find_local_vscode_processes()
            
            if existing_processes:
                logger.info("VSCode Desktop already running, FORCING focus to LOCAL VSCode...")
                # Force focus to LOCAL VSCode Desktop window (not Web version)
                # Try multiple methods to ensure we get the right window
                
                # Method 1: Focus by process ID
                for proc in existing_processes:
                    try:
                        subprocess.run(['wmctrl', '-i', '-a', str(proc['pid'])], capture_output=True)
                        logger.info(f"Attempted to focus VSCode PID: {proc['pid']}")
                    except:
                        pass
                
                # Method 2: Focus by window title (exclude Chrome/Web)
                subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
                
                # Method 3: Bring to front using xdotool
                try:
                    # Get all VSCode windows and focus the non-Chrome one
                    result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if 'Visual Studio Code' in line and 'Chrome' not in line:
                            window_id = line.split()[0]
                            subprocess.run(['xdotool', 'windowactivate', window_id], capture_output=True)
                            logger.info(f"Forced activation of LOCAL VSCode window: {window_id}")
                            break
                except:
                    pass
                
                time.sleep(3)  # Give more time for window switching
            else:
                logger.info("Launching new VSCode Desktop instance...")
                # Launch VSCode Desktop with project path
                subprocess.Popen([
                    'code',
                    self.project_path,
                    '--disable-extensions',  # Disable extensions to avoid conflicts
                    '--new-window'  # Force new window
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Wait for VSCode to start
                logger.info("Waiting for VSCode to start...")
                time.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"Error launching/focusing VSCode: {e}")
            return False
    
    def verify_vscode_window_active(self):
        """Verify that a LOCAL VSCode Desktop window is active (not Web/Windsurf)"""
        try:
            logger.info("=== Verifying LOCAL VSCode Desktop Window ===")
            
            # Get active window information
            try:
                result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], 
                                      capture_output=True, text=True)
                active_window = result.stdout.strip()
                logger.info(f"Active window: {active_window}")
                
                # STRICT CHECK: Must be LOCAL VSCode Desktop, NOT Web version
                is_local_vscode = False
                
                if 'Visual Studio Code' in active_window:
                    # EXCLUDE Windsurf
                    if 'Windsurf' in active_window:
                        logger.warning(f"❌ EXCLUDED: Windsurf window detected: {active_window}")
                        return False
                    
                    # EXCLUDE Web VSCode (browser-based)
                    if any(browser in active_window.lower() for browser in ['chrome', 'firefox', 'browser', 'web']):
                        logger.warning(f"❌ EXCLUDED: Web VSCode detected: {active_window}")
                        return False
                    
                    # EXCLUDE vscode.dev or github.dev
                    if 'vscode.dev' in active_window.lower() or 'github.dev' in active_window.lower():
                        logger.warning(f"❌ EXCLUDED: Web VSCode (vscode.dev/github.dev) detected: {active_window}")
                        return False
                    
                    # If none of the exclusions match, it should be local VSCode
                    is_local_vscode = True
                
                if is_local_vscode:
                    logger.info("✅ LOCAL VSCode Desktop window is active")
                    return True
                else:
                    logger.warning(f"❌ Active window is not LOCAL VSCode Desktop: {active_window}")
                    return False
                    
            except subprocess.CalledProcessError:
                logger.warning("Could not get active window name, proceeding with caution")
                return True
                
        except Exception as e:
            logger.error(f"Error verifying VSCode window: {e}")
            return False
    
    def take_screenshot(self, name):
        """Take screenshot for verification"""
        try:
            screenshot_path = os.path.join(LOG_DIR, f"local_vscode_{name}_{TIMESTAMP}.png")
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def send_prompt_to_local_vscode(self):
        """Send prompt to local VSCode Desktop (not Windsurf)"""
        try:
            logger.info("=== Sending Prompt to Local VSCode Desktop ===")
            
            # Step 1: Launch or focus VSCode Desktop
            if not self.launch_or_focus_local_vscode():
                logger.error("Failed to launch/focus VSCode Desktop")
                return False
            
            # Step 2: Verify correct window is active (with retry)
            for attempt in range(3):
                if self.verify_vscode_window_active():
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1}: LOCAL VSCode Desktop not active, retrying focus...")
                    # Try additional focus methods
                    subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
                    subprocess.run(['xdotool', 'search', '--name', 'Visual Studio Code', 'windowactivate'], capture_output=True)
                    time.sleep(2)
            else:
                logger.error("Failed to activate LOCAL VSCode Desktop window after 3 attempts")
                logger.error("Please manually focus your LOCAL VSCode Desktop window and try again")
                return False
            
            # Step 3: Take initial screenshot
            self.take_screenshot("before_automation")
            
            # Step 4: Wait for user confirmation
            logger.info("⚠️  IMPORTANT: Please verify that VSCode Desktop (NOT Windsurf) is focused!")
            logger.info("The automation will start in 5 seconds...")
            
            for i in range(5, 0, -1):
                print(f"Starting in {i} seconds... (Make sure VSCode Desktop is focused, NOT Windsurf)")
                time.sleep(1)
            
            # Step 5: Open Copilot chat
            logger.info("🎯 Opening Copilot chat in VSCode Desktop...")
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(2)
            
            self.take_screenshot("after_chat_open")
            
            # Step 6: Type prompt
            logger.info("💬 Typing prompt...")
            prompt = "Hello! Can you help me write a Python function to calculate the factorial of a number?"
            pyautogui.typewrite(prompt, interval=0.05)
            time.sleep(1)
            
            self.take_screenshot("after_typing")
            
            # Step 7: Send prompt
            logger.info("⏎ Sending prompt...")
            pyautogui.press('enter')
            time.sleep(2)
            
            self.take_screenshot("after_send")
            
            logger.info("✅ Prompt sent to Local VSCode Desktop!")
            logger.info("📸 Check screenshots to verify automation targeted correct VSCode")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in local VSCode automation: {e}")
            return False

def main():
    """Main function"""
    print("=" * 70)
    print("🎯 LOCAL VSCODE DESKTOP AUTOMATION")
    print("=" * 70)
    print("This targets ONLY your local VSCode Desktop window.")
    print("It will NOT target Windsurf or any other editor.")
    print("")
    print("IMPORTANT:")
    print("1. Make sure your local VSCode Desktop is running")
    print("2. Make sure it has the copilot-instruction-eval project open")
    print("3. Make sure GitHub Copilot extension is installed")
    print("4. The automation will focus VSCode Desktop automatically")
    print("=" * 70)
    
    try:
        automation = LocalVSCodeAutomation()
        success = automation.send_prompt_to_local_vscode()
        
        if success:
            print("✅ Local VSCode Desktop automation completed!")
            print("📸 Check evaluation_logs/ for screenshots to verify results")
        else:
            print("❌ Local VSCode Desktop automation failed!")
            print("📋 Check the logs for details")
        
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
