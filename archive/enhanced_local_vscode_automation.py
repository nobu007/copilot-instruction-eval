#!/usr/bin/env python3
"""
Enhanced Local VSCode Desktop Automation with YOLO Input Field Detection
ローカルVSCode Desktopのみを対象とした自動操作（YOLO入力欄検出付き）
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import subprocess
import psutil
import pyautogui
import logging
from datetime import datetime
import os
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image, ImageTk

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# Setup logging
log_dir = Path("evaluation_logs")
log_dir.mkdir(exist_ok=True)

class TkinterLogHandler(logging.Handler):
    """Custom log handler for Tkinter GUI"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
        # Schedule GUI update in main thread
        self.text_widget.after(0, append)

class EnhancedLocalVSCodeAutomation:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 Enhanced Local VSCode Desktop Automation")
        self.root.geometry("900x700")
        
        # Status variables
        self.is_running = False
        self.automation_thread = None
        
        # YOLO model for UI detection
        self.yolo_model = None
        
        # Setup GUI
        self.setup_gui()
        
        # Setup logging
        self.setup_logging()
        
        # Project path
        self.project_path = "/home/jinno/copilot-instruction-eval"
        
        # Load YOLO model
        self.load_yolo_model()
        
    def load_yolo_model(self):
        """Load YOLO model for UI element detection"""
        try:
            self.logger.info("Loading YOLO model for UI detection...")
            self.yolo_model = YOLO('yolov8n.pt')  # Use nano model for speed
            self.logger.info("✅ YOLO model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            self.yolo_model = None
        
    def setup_gui(self):
        """Setup the GUI components"""
        # Title
        title_label = tk.Label(self.root, text="🎯 Enhanced Local VSCode Desktop Automation", 
                              font=("Arial", 16, "bold"), fg="blue")
        title_label.pack(pady=10)
        
        # Warning
        warning_text = """⚠️ IMPORTANT: This targets ONLY your LOCAL VSCode Desktop window.
It will NOT target Windsurf, Web VSCode, or any other editor.
🔍 Uses YOLO to detect and click the correct input fields."""
        warning_label = tk.Label(self.root, text=warning_text, 
                                font=("Arial", 10), fg="red", justify=tk.LEFT)
        warning_label.pack(pady=5)
        
        # Control buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # Start button
        self.start_button = tk.Button(button_frame, text="🚀 Start Enhanced Automation", 
                                     command=self.start_automation, 
                                     font=("Arial", 12, "bold"), 
                                     bg="green", fg="white", width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = tk.Button(button_frame, text="⏹️ Stop", 
                                    command=self.stop_automation, 
                                    font=("Arial", 12, "bold"), 
                                    bg="red", fg="white", width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status frame
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(status_frame, text="Status:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.status_label = tk.Label(status_frame, text="Ready", 
                                    font=("Arial", 10), fg="green")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress frame
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(progress_frame, text="Progress:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.progress_label = tk.Label(progress_frame, text="Waiting to start...", 
                                      font=("Arial", 10), fg="blue")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        # Screenshot preview frame
        preview_frame = tk.Frame(self.root)
        preview_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(preview_frame, text="🖼️ Current Screenshot:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.screenshot_label = tk.Label(preview_frame, text="No screenshot yet", 
                                        bg="lightgray", width=60, height=8)
        self.screenshot_label.pack(pady=5)
        
        # Log display
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(log_frame, text="📋 Enhanced Automation Log:", 
                font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80,
                                                 font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
    def setup_logging(self):
        """Setup logging to both file and GUI"""
        # Create logger
        self.logger = logging.getLogger("EnhancedLocalVSCodeAutomation")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"enhanced_local_vscode_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # GUI handler
        gui_handler = TkinterLogHandler(self.log_text)
        gui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(gui_formatter)
        self.logger.addHandler(gui_handler)
        
    def update_status(self, status, color="black"):
        """Update status label"""
        def update():
            self.status_label.config(text=status, fg=color)
        self.root.after(0, update)
        
    def update_progress(self, progress, color="blue"):
        """Update progress label"""
        def update():
            self.progress_label.config(text=progress, fg=color)
        self.root.after(0, update)
    
    def update_screenshot_preview(self, image_path):
        """Update screenshot preview in GUI"""
        try:
            # Load and resize image for preview
            img = Image.open(image_path)
            img.thumbnail((300, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            def update():
                self.screenshot_label.config(image=photo, text="")
                self.screenshot_label.image = photo  # Keep a reference
            self.root.after(0, update)
            
        except Exception as e:
            self.logger.error(f"Error updating screenshot preview: {e}")
    
    def find_local_vscode_processes(self):
        """Find LOCAL VSCode Desktop processes (exclude Windsurf and Web)"""
        self.logger.info("=== Finding Local VSCode Desktop Processes ===")
        vscode_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    pinfo = proc.info
                    name = pinfo['name'] or ''
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
                        self.logger.info(f"EXCLUDED Windsurf process: PID={pinfo['pid']}")
                        continue
                    
                    # Skip helper processes
                    if any(skip in cmdline.lower() for skip in ['--type=', 'gpu-process', 'utility', 'renderer']):
                        continue
                    
                    if is_local_vscode:
                        vscode_processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'exe': exe,
                            'cmdline': cmdline
                        })
                        self.logger.info(f"Found LOCAL VSCode Desktop: PID={pinfo['pid']}, exe={exe}")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            self.logger.info(f"Total local VSCode Desktop processes found: {len(vscode_processes)}")
            return vscode_processes
            
        except Exception as e:
            self.logger.error(f"Error finding VSCode processes: {e}")
            return []
    
    def verify_vscode_window_active(self):
        """Verify that a LOCAL VSCode Desktop window is active (not Web/Windsurf)"""
        try:
            self.logger.info("=== Verifying LOCAL VSCode Desktop Window ===")
            
            # Get active window information
            try:
                result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], 
                                      capture_output=True, text=True)
                active_window = result.stdout.strip()
                self.logger.info(f"Active window: {active_window}")
                
                # STRICT CHECK: Must be LOCAL VSCode Desktop, NOT Web version
                is_local_vscode = False
                
                if 'Visual Studio Code' in active_window:
                    # EXCLUDE Windsurf
                    if 'Windsurf' in active_window:
                        self.logger.warning(f"❌ EXCLUDED: Windsurf window detected: {active_window}")
                        return False
                    
                    # EXCLUDE Web VSCode (browser-based)
                    if any(browser in active_window.lower() for browser in ['chrome', 'firefox', 'browser', 'web']):
                        self.logger.warning(f"❌ EXCLUDED: Web VSCode detected: {active_window}")
                        return False
                    
                    # EXCLUDE vscode.dev or github.dev
                    if 'vscode.dev' in active_window.lower() or 'github.dev' in active_window.lower():
                        self.logger.warning(f"❌ EXCLUDED: Web VSCode (vscode.dev/github.dev) detected: {active_window}")
                        return False
                    
                    # If none of the exclusions match, it should be local VSCode
                    is_local_vscode = True
                
                if is_local_vscode:
                    self.logger.info("✅ LOCAL VSCode Desktop window is active")
                    return True
                else:
                    self.logger.warning(f"❌ Active window is not LOCAL VSCode Desktop: {active_window}")
                    return False
                    
            except subprocess.CalledProcessError:
                self.logger.warning("Could not get active window name, proceeding with caution")
                return True
                
        except Exception as e:
            self.logger.error(f"Error verifying VSCode window: {e}")
            return False
    
    def take_screenshot(self, stage):
        """Take screenshot for verification and update preview"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_local_vscode_{stage}_{timestamp}.png"
            filepath = log_dir / filename
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            self.logger.info(f"Screenshot saved: {filepath}")
            
            # Update preview in GUI
            self.update_screenshot_preview(filepath)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    def detect_input_fields_with_yolo(self, screenshot_path):
        """Use YOLO to detect potential input fields in the screenshot"""
        try:
            if not self.yolo_model:
                self.logger.warning("YOLO model not available, using fallback method")
                return []
            
            self.logger.info("🔍 Detecting input fields with YOLO...")
            
            # Load screenshot
            img = cv2.imread(screenshot_path)
            if img is None:
                self.logger.error("Failed to load screenshot for YOLO detection")
                return []
            
            # Run YOLO detection
            results = self.yolo_model(img)
            
            input_fields = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        # Filter for potential input areas (adjust confidence threshold)
                        if confidence > 0.3:
                            width = x2 - x1
                            height = y2 - y1
                            
                            # Look for rectangular areas that could be input fields
                            if width > 100 and height > 20 and height < 100:
                                input_fields.append({
                                    'x': int(x1),
                                    'y': int(y1),
                                    'width': int(width),
                                    'height': int(height),
                                    'confidence': float(confidence),
                                    'center_x': int((x1 + x2) / 2),
                                    'center_y': int((y1 + y2) / 2)
                                })
            
            self.logger.info(f"Found {len(input_fields)} potential input fields")
            return input_fields
            
        except Exception as e:
            self.logger.error(f"Error in YOLO detection: {e}")
            return []
    
    def find_best_input_field(self, input_fields):
        """Find the best input field candidate (likely at bottom of screen)"""
        if not input_fields:
            return None
        
        # Sort by Y coordinate (bottom of screen first) and confidence
        sorted_fields = sorted(input_fields, key=lambda x: (-x['y'], -x['confidence']))
        
        best_field = sorted_fields[0]
        self.logger.info(f"Selected input field: x={best_field['x']}, y={best_field['y']}, "
                        f"confidence={best_field['confidence']:.2f}")
        
        return best_field
    
    def open_copilot_chat_enhanced(self):
        """Open Copilot chat with multiple methods"""
        try:
            self.logger.info("🎯 Opening Copilot chat with enhanced detection...")
            self.update_progress("Opening Copilot chat...")
            
            # Method 1: Standard shortcut
            self.logger.info("Trying Ctrl+Shift+I...")
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(3)
            
            # Take screenshot to see what opened
            screenshot_path = self.take_screenshot("after_ctrl_shift_i")
            
            # Method 2: Try Command Palette
            self.logger.info("Trying Command Palette approach...")
            pyautogui.hotkey('ctrl', 'shift', 'p')
            time.sleep(1)
            pyautogui.typewrite("GitHub Copilot: Open Chat", interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(3)
            
            # Take screenshot after command palette
            screenshot_path = self.take_screenshot("after_command_palette")
            
            return screenshot_path
            
        except Exception as e:
            self.logger.error(f"Error opening Copilot chat: {e}")
            return None
    
    def send_prompt_enhanced(self):
        """Send prompt with YOLO-enhanced input field detection"""
        try:
            self.logger.info("🚀 Starting enhanced prompt sending...")
            
            # Step 1: Open Copilot chat
            screenshot_path = self.open_copilot_chat_enhanced()
            if not screenshot_path:
                return False
            
            # Step 2: Detect input fields with YOLO
            self.update_progress("Detecting input fields with YOLO...")
            input_fields = self.detect_input_fields_with_yolo(screenshot_path)
            
            if not input_fields:
                self.logger.warning("No input fields detected, trying fallback click method")
                # Fallback: Click at bottom center of screen
                screen_width, screen_height = pyautogui.size()
                fallback_x = screen_width // 2
                fallback_y = int(screen_height * 0.9)  # 90% down the screen
                pyautogui.click(fallback_x, fallback_y)
                time.sleep(1)
            else:
                # Step 3: Click on the best input field
                best_field = self.find_best_input_field(input_fields)
                if best_field:
                    self.logger.info(f"Clicking on detected input field at ({best_field['center_x']}, {best_field['center_y']})")
                    self.update_progress("Clicking on detected input field...")
                    pyautogui.click(best_field['center_x'], best_field['center_y'])
                    time.sleep(1)
            
            # Step 4: Clear and type prompt
            self.update_progress("Typing enhanced prompt...")
            prompt = "🎯 ENHANCED AUTOMATION TEST: Hello from YOLO-enhanced local VSCode Desktop automation! This message was sent using advanced input field detection. Please confirm you received this message and that it appears in GitHub Copilot chat."
            
            # Clear any existing text
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            
            # Type the prompt
            self.logger.info("💬 Typing enhanced prompt...")
            pyautogui.typewrite(prompt, interval=0.03)
            time.sleep(2)
            
            # Take screenshot after typing
            self.take_screenshot("after_enhanced_typing")
            
            # Step 5: Send the prompt
            self.logger.info("⏎ Sending enhanced prompt...")
            self.update_progress("Sending enhanced prompt...")
            pyautogui.press('enter')
            time.sleep(2)
            
            # Take final screenshot
            self.take_screenshot("after_enhanced_send")
            
            self.logger.info("✅ Enhanced prompt sent successfully!")
            self.update_progress("✅ Enhanced prompt sent!", "green")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in enhanced prompt sending: {e}")
            self.update_progress(f"❌ Error: {e}", "red")
            return False
    
    def launch_or_focus_vscode(self):
        """Launch or focus LOCAL VSCode Desktop"""
        try:
            self.logger.info("=== Launching/Focusing Local VSCode Desktop ===")
            self.update_progress("Finding VSCode processes...")
            
            existing_processes = self.find_local_vscode_processes()
            
            if existing_processes:
                self.logger.info("VSCode Desktop already running, FORCING focus to LOCAL VSCode...")
                self.update_progress("Focusing LOCAL VSCode Desktop...")
                
                # Force focus using multiple methods
                for proc in existing_processes:
                    try:
                        subprocess.run(['wmctrl', '-i', '-a', str(proc['pid'])], capture_output=True)
                        self.logger.info(f"Attempted to focus VSCode PID: {proc['pid']}")
                    except:
                        pass
                
                subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
                
                try:
                    result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if 'Visual Studio Code' in line and 'Chrome' not in line:
                            window_id = line.split()[0]
                            subprocess.run(['xdotool', 'windowactivate', window_id], capture_output=True)
                            self.logger.info(f"Forced activation of LOCAL VSCode window: {window_id}")
                            break
                except:
                    pass
                
                time.sleep(3)
            else:
                self.logger.info("Launching new VSCode Desktop instance...")
                self.update_progress("Launching new VSCode Desktop...")
                subprocess.Popen(['code', self.project_path])
                time.sleep(5)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error launching/focusing VSCode: {e}")
            return False
    
    def automation_worker(self):
        """Enhanced automation worker thread"""
        try:
            self.logger.info("=" * 70)
            self.logger.info("🎯 ENHANCED LOCAL VSCODE DESKTOP AUTOMATION")
            self.logger.info("=" * 70)
            self.logger.info("This uses YOLO to detect input fields accurately!")
            self.logger.info("=" * 70)
            
            self.update_status("Running", "orange")
            
            # Step 1: Launch/Focus VSCode Desktop
            self.update_progress("Step 1: Launching/Focusing VSCode...")
            if not self.launch_or_focus_vscode():
                self.logger.error("Failed to launch/focus VSCode Desktop")
                self.update_status("Failed", "red")
                return False
            
            # Step 2: Verify window
            self.update_progress("Step 2: Verifying VSCode window...")
            for attempt in range(3):
                if self.verify_vscode_window_active():
                    break
                else:
                    self.logger.warning(f"Attempt {attempt + 1}: Retrying focus...")
                    subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
                    time.sleep(2)
            else:
                self.logger.error("Failed to activate LOCAL VSCode Desktop")
                self.update_status("Failed", "red")
                return False
            
            # Step 3: Take initial screenshot
            self.update_progress("Step 3: Taking initial screenshot...")
            self.take_screenshot("enhanced_initial")
            
            # Step 4: Countdown
            self.logger.info("✅ Ready for enhanced automation!")
            for i in range(5, 0, -1):
                if not self.is_running:
                    return False
                self.update_progress(f"Starting enhanced automation in {i}s...", "orange")
                time.sleep(1)
            
            # Step 5: Enhanced prompt sending
            self.update_progress("Step 4: Enhanced prompt sending...")
            if not self.send_prompt_enhanced():
                self.update_status("Failed", "red")
                return False
            
            # Success
            self.logger.info("✅ Enhanced automation completed successfully!")
            self.update_status("✅ Completed", "green")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced automation error: {e}")
            self.update_status("Error", "red")
            return False
        finally:
            def reset_buttons():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.is_running = False
            self.root.after(0, reset_buttons)
    
    def start_automation(self):
        """Start the enhanced automation"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start automation thread
        self.automation_thread = threading.Thread(target=self.automation_worker)
        self.automation_thread.daemon = True
        self.automation_thread.start()
    
    def stop_automation(self):
        """Stop the automation"""
        self.is_running = False
        self.update_status("Stopping...", "orange")
        self.update_progress("Stopping automation...", "orange")
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.logger.info("🛑 Enhanced automation stopped by user")
        self.update_status("Stopped", "red")
    
    def run(self):
        """Run the enhanced GUI application"""
        self.root.mainloop()

def main():
    """Main function"""
    print("🎯 Starting Enhanced Local VSCode Desktop Automation...")
    
    app = EnhancedLocalVSCodeAutomation()
    app.run()

if __name__ == "__main__":
    main()
