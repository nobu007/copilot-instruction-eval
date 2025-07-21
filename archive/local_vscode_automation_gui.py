#!/usr/bin/env python3
"""
Enhanced Local VSCode Desktop Automation with Tkinter GUI
ローカルVSCode Desktopのみを対象とした自動操作（進捗可視化付き）
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

class LocalVSCodeAutomationGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 Local VSCode Desktop Automation")
        self.root.geometry("800x600")
        
        # Status variables
        self.is_running = False
        self.automation_thread = None
        
        # Setup GUI
        self.setup_gui()
        
        # Setup logging
        self.setup_logging()
        
        # Project path
        self.project_path = "/home/jinno/copilot-instruction-eval"
        
    def setup_gui(self):
        """Setup the GUI components"""
        # Title
        title_label = tk.Label(self.root, text="🎯 Local VSCode Desktop Automation", 
                              font=("Arial", 16, "bold"), fg="blue")
        title_label.pack(pady=10)
        
        # Warning
        warning_text = """⚠️ IMPORTANT: This targets ONLY your LOCAL VSCode Desktop window.
It will NOT target Windsurf, Web VSCode, or any other editor."""
        warning_label = tk.Label(self.root, text=warning_text, 
                                font=("Arial", 10), fg="red", justify=tk.LEFT)
        warning_label.pack(pady=5)
        
        # Control buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # Start button
        self.start_button = tk.Button(button_frame, text="🚀 Start Automation", 
                                     command=self.start_automation, 
                                     font=("Arial", 12, "bold"), 
                                     bg="green", fg="white", width=15)
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
        
        # Log display
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(log_frame, text="📋 Automation Log:", 
                font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80,
                                                 font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Instructions
        instructions = """
📋 Instructions:
1. Make sure your LOCAL VSCode Desktop is running
2. Make sure it has the copilot-instruction-eval project open  
3. Make sure GitHub Copilot extension is installed
4. Click 'Start Automation' - it will automatically focus VSCode Desktop
5. Watch the progress in this window
        """
        instructions_label = tk.Label(self.root, text=instructions, 
                                     font=("Arial", 9), justify=tk.LEFT, fg="darkblue")
        instructions_label.pack(pady=5, padx=10, anchor=tk.W)
        
    def setup_logging(self):
        """Setup logging to both file and GUI"""
        # Create logger
        self.logger = logging.getLogger("LocalVSCodeAutomation")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"local_vscode_automation_{timestamp}.log"
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
    
    def launch_or_focus_vscode(self):
        """Launch or focus LOCAL VSCode Desktop"""
        try:
            self.logger.info("=== Launching/Focusing Local VSCode Desktop ===")
            self.update_progress("Finding VSCode processes...")
            
            existing_processes = self.find_local_vscode_processes()
            
            if existing_processes:
                self.logger.info("VSCode Desktop already running, FORCING focus to LOCAL VSCode...")
                self.update_progress("Focusing LOCAL VSCode Desktop...")
                
                # Force focus to LOCAL VSCode Desktop window (not Web version)
                # Try multiple methods to ensure we get the right window
                
                # Method 1: Focus by process ID
                for proc in existing_processes:
                    try:
                        subprocess.run(['wmctrl', '-i', '-a', str(proc['pid'])], capture_output=True)
                        self.logger.info(f"Attempted to focus VSCode PID: {proc['pid']}")
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
                            self.logger.info(f"Forced activation of LOCAL VSCode window: {window_id}")
                            break
                except:
                    pass
                
                time.sleep(3)  # Give more time for window switching
            else:
                self.logger.info("Launching new VSCode Desktop instance...")
                self.update_progress("Launching new VSCode Desktop...")
                # Launch VSCode Desktop with project path
                subprocess.Popen(['code', self.project_path])
                time.sleep(5)  # Wait for VSCode to start
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error launching/focusing VSCode: {e}")
            return False
    
    def take_screenshot(self, stage):
        """Take screenshot for verification"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"local_vscode_{stage}_{timestamp}.png"
            filepath = log_dir / filename
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            self.logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    def send_prompt_to_copilot(self):
        """Send prompt to GitHub Copilot in LOCAL VSCode Desktop"""
        try:
            self.logger.info("🎯 Opening Copilot chat in VSCode Desktop...")
            self.update_progress("Opening Copilot chat...")
            
            # Open Copilot chat with Ctrl+Shift+I
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(2)
            
            # Take screenshot after opening chat
            self.take_screenshot("after_chat_open")
            
            # Type the prompt
            prompt = "Hello from automated local VSCode Desktop! Please confirm you received this message."
            self.logger.info("💬 Typing prompt...")
            self.update_progress("Typing prompt...")
            
            # Clear any existing text and type new prompt
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            pyautogui.typewrite(prompt, interval=0.05)
            time.sleep(1)
            
            # Take screenshot after typing
            self.take_screenshot("after_typing")
            
            # Send the prompt
            self.logger.info("⏎ Sending prompt...")
            self.update_progress("Sending prompt...")
            pyautogui.press('enter')
            time.sleep(1)
            
            # Take screenshot after sending
            self.take_screenshot("after_send")
            
            self.logger.info("✅ Prompt sent to Local VSCode Desktop!")
            self.update_progress("✅ Prompt sent successfully!", "green")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending prompt: {e}")
            self.update_progress("❌ Error sending prompt", "red")
            return False
    
    def automation_worker(self):
        """Main automation worker thread"""
        try:
            self.logger.info("=" * 70)
            self.logger.info("🎯 LOCAL VSCODE DESKTOP AUTOMATION")
            self.logger.info("=" * 70)
            self.logger.info("This targets ONLY your local VSCode Desktop window.")
            self.logger.info("It will NOT target Windsurf or any other editor.")
            self.logger.info("=" * 70)
            
            self.update_status("Running", "orange")
            
            # Step 1: Launch/Focus VSCode Desktop
            self.update_progress("Step 1: Launching/Focusing VSCode...")
            if not self.launch_or_focus_vscode():
                self.logger.error("Failed to launch/focus VSCode Desktop")
                self.update_status("Failed", "red")
                self.update_progress("❌ Failed to launch/focus VSCode", "red")
                return False
            
            # Step 2: Verify correct window is active (with retry)
            self.update_progress("Step 2: Verifying VSCode window...")
            for attempt in range(3):
                if self.verify_vscode_window_active():
                    break
                else:
                    self.logger.warning(f"Attempt {attempt + 1}: LOCAL VSCode Desktop not active, retrying focus...")
                    self.update_progress(f"Retry {attempt + 1}: Focusing VSCode...")
                    # Try additional focus methods
                    subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
                    subprocess.run(['xdotool', 'search', '--name', 'Visual Studio Code', 'windowactivate'], capture_output=True)
                    time.sleep(2)
            else:
                self.logger.error("Failed to activate LOCAL VSCode Desktop window after 3 attempts")
                self.logger.error("Please manually focus your LOCAL VSCode Desktop window and try again")
                self.update_status("Failed", "red")
                self.update_progress("❌ Failed to activate VSCode window", "red")
                return False
            
            # Step 3: Take initial screenshot
            self.update_progress("Step 3: Taking initial screenshot...")
            self.take_screenshot("initial")
            
            # Step 4: Countdown before automation
            self.logger.info("✅ Local VSCode Desktop (NOT Windsurf) is focused!")
            self.logger.info("The automation will start in 5 seconds...")
            
            for i in range(5, 0, -1):
                if not self.is_running:  # Check if stopped
                    return False
                self.update_progress(f"Starting in {i} seconds... (LOCAL VSCode focused)", "orange")
                print(f"Starting in {i} seconds... (Make sure VSCode Desktop is focused, NOT Windsurf)")
                time.sleep(1)
            
            # Step 5: Send prompt to Copilot
            self.update_progress("Step 4: Sending prompt to Copilot...")
            if not self.send_prompt_to_copilot():
                self.update_status("Failed", "red")
                return False
            
            # Success
            self.logger.info("✅ Local VSCode Desktop automation completed!")
            self.logger.info("📸 Check evaluation_logs/ for screenshots to verify results")
            self.update_status("✅ Completed", "green")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Automation error: {e}")
            self.update_status("Error", "red")
            self.update_progress(f"❌ Error: {e}", "red")
            return False
        finally:
            # Reset button states
            def reset_buttons():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.is_running = False
            self.root.after(0, reset_buttons)
    
    def start_automation(self):
        """Start the automation in a separate thread"""
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
        
        # Reset buttons
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.logger.info("🛑 Automation stopped by user")
        self.update_status("Stopped", "red")
        self.update_progress("Stopped by user", "red")
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

def main():
    """Main function"""
    print("🎯 Starting Local VSCode Desktop Automation GUI...")
    
    # Create and run the GUI application
    app = LocalVSCodeAutomationGUI()
    app.run()

if __name__ == "__main__":
    main()
