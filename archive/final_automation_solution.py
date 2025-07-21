#!/usr/bin/env python3
"""
Final Local VSCode Desktop Automation Solution
確実なプロンプト投入とユーザーフィードバック統合
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import time
import subprocess
import psutil
import pyautogui
import logging
from datetime import datetime
from pathlib import Path

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

log_dir = Path("evaluation_logs")
log_dir.mkdir(exist_ok=True)

class FinalAutomationSolution:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 Final VSCode Automation Solution")
        self.root.geometry("900x700")
        
        self.is_running = False
        self.user_feedback = ""
        self.feedback_received = False
        
        self.setup_gui()
        self.setup_logging()
        
    def setup_gui(self):
        """Setup comprehensive GUI"""
        # Title
        title = tk.Label(self.root, text="🎯 Final Local VSCode Desktop Automation", 
                        font=("Arial", 16, "bold"), fg="darkblue")
        title.pack(pady=10)
        
        # Control panel
        control_frame = tk.LabelFrame(self.root, text="🎮 Control Panel", font=("Arial", 12, "bold"))
        control_frame.pack(pady=10, padx=10, fill=tk.X)
        
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        
        self.start_button = tk.Button(button_frame, text="🚀 Start Final Automation", 
                                     command=self.start_automation, 
                                     font=("Arial", 12, "bold"), 
                                     bg="darkgreen", fg="white", width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="⏹️ Stop", 
                                    command=self.stop_automation, 
                                    font=("Arial", 12, "bold"), 
                                    bg="darkred", fg="white", width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status panel
        status_frame = tk.LabelFrame(self.root, text="📊 Status", font=("Arial", 12, "bold"))
        status_frame.pack(pady=5, padx=10, fill=tk.X)
        
        status_row = tk.Frame(status_frame)
        status_row.pack(pady=5, fill=tk.X, padx=10)
        tk.Label(status_row, text="Status:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.status_label = tk.Label(status_row, text="Ready", font=("Arial", 11), fg="green")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        progress_row = tk.Frame(status_frame)
        progress_row.pack(pady=5, fill=tk.X, padx=10)
        tk.Label(progress_row, text="Progress:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.progress_label = tk.Label(progress_row, text="Waiting...", font=("Arial", 11), fg="blue")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        # User feedback panel
        feedback_frame = tk.LabelFrame(self.root, text="💬 User Feedback", font=("Arial", 12, "bold"))
        feedback_frame.pack(pady=5, padx=10, fill=tk.X)
        
        feedback_instruction = tk.Label(feedback_frame, 
                                       text="After automation, verify and provide feedback:",
                                       font=("Arial", 10), fg="darkblue")
        feedback_instruction.pack(pady=5)
        
        # Quick feedback buttons
        quick_frame = tk.Frame(feedback_frame)
        quick_frame.pack(pady=5)
        
        tk.Button(quick_frame, text="✅ SUCCESS - Prompt in Copilot", 
                 command=lambda: self.quick_feedback("SUCCESS"), 
                 font=("Arial", 9), bg="green", fg="white").pack(side=tk.LEFT, padx=2)
        
        tk.Button(quick_frame, text="❌ FAILED - No prompt in Copilot", 
                 command=lambda: self.quick_feedback("FAILED"), 
                 font=("Arial", 9), bg="red", fg="white").pack(side=tk.LEFT, padx=2)
        
        tk.Button(quick_frame, text="⚠️ PARTIAL - Copilot opened, no text", 
                 command=lambda: self.quick_feedback("PARTIAL"), 
                 font=("Arial", 9), bg="orange", fg="white").pack(side=tk.LEFT, padx=2)
        
        # Custom feedback
        custom_frame = tk.Frame(feedback_frame)
        custom_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(custom_frame, text="Custom:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.feedback_entry = tk.Entry(custom_frame, font=("Arial", 10), width=40)
        self.feedback_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        tk.Button(custom_frame, text="📝 Submit", command=self.submit_feedback, 
                 font=("Arial", 10, "bold"), bg="orange", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Log display
        log_frame = tk.LabelFrame(self.root, text="📋 Automation Log", font=("Arial", 12, "bold"))
        log_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=90, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
    def setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger("FinalAutomation")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        
        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"final_automation_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # GUI handler
        class GUIHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                self.text_widget.after(0, append)
        
        gui_handler = GUIHandler(self.log_text)
        gui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(gui_formatter)
        self.logger.addHandler(gui_handler)
        
    def update_status(self, status, color="black"):
        def update():
            self.status_label.config(text=status, fg=color)
        self.root.after(0, update)
        
    def update_progress(self, progress, color="blue"):
        def update():
            self.progress_label.config(text=progress, fg=color)
        self.root.after(0, update)
    
    def submit_feedback(self):
        feedback = self.feedback_entry.get().strip()
        if feedback:
            self.user_feedback = feedback
            self.feedback_received = True
            self.logger.info(f"📝 User feedback: {feedback}")
            self.feedback_entry.delete(0, tk.END)
            messagebox.showinfo("Feedback", f"Recorded: {feedback}")
    
    def quick_feedback(self, feedback_type):
        feedback_map = {
            "SUCCESS": "✅ SUCCESS: Prompt successfully appeared in GitHub Copilot chat",
            "FAILED": "❌ FAILED: No prompt appeared in GitHub Copilot chat", 
            "PARTIAL": "⚠️ PARTIAL: Copilot opened but prompt text was not entered"
        }
        
        self.user_feedback = feedback_map.get(feedback_type, feedback_type)
        self.feedback_received = True
        self.logger.info(f"📝 Quick feedback: {self.user_feedback}")
        messagebox.showinfo("Feedback", f"Recorded:\n{self.user_feedback}")
    
    def find_local_vscode_processes(self):
        """Find LOCAL VSCode Desktop processes"""
        self.logger.info("=== Finding Local VSCode Desktop Processes ===")
        vscode_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                pinfo = proc.info
                name = pinfo['name'] or ''
                cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                exe = pinfo['exe'] or ''
                
                # EXCLUDE Windsurf
                if 'windsurf' in exe.lower() or 'windsurf' in cmdline.lower():
                    self.logger.info(f"EXCLUDED Windsurf: PID={pinfo['pid']}")
                    continue
                
                # Find LOCAL VSCode Desktop
                is_local_vscode = False
                if '/usr/share/code/code' in exe or '/snap/code/' in exe:
                    if not any(web in cmdline.lower() for web in ['--remote', '--server', 'vscode.dev']):
                        is_local_vscode = True
                
                if is_local_vscode:
                    vscode_processes.append(pinfo)
                    self.logger.info(f"Found LOCAL VSCode: PID={pinfo['pid']}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        self.logger.info(f"Total LOCAL VSCode processes: {len(vscode_processes)}")
        return vscode_processes
    
    def focus_local_vscode(self):
        """Focus LOCAL VSCode Desktop window"""
        self.logger.info("=== Focusing LOCAL VSCode Desktop ===")
        
        # Multiple focus methods
        subprocess.run(['wmctrl', '-a', 'Visual Studio Code'], capture_output=True)
        
        # Get and activate non-Chrome VSCode window
        result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'Visual Studio Code' in line and 'Chrome' not in line:
                window_id = line.split()[0]
                subprocess.run(['xdotool', 'windowactivate', window_id], capture_output=True)
                self.logger.info(f"Activated LOCAL VSCode window: {window_id}")
                break
        
        time.sleep(3)
        return True
    
    def take_screenshot(self, stage):
        """Take and save screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"final_automation_{stage}_{timestamp}.png"
            filepath = log_dir / filename
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            self.logger.info(f"Screenshot: {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return None
    
    def send_final_prompt(self):
        """Send prompt with multiple strategies"""
        try:
            self.logger.info("🚀 Starting final prompt sending...")
            
            # Strategy 1: Standard Copilot shortcut
            self.logger.info("Trying Ctrl+Shift+I...")
            pyautogui.hotkey('ctrl', 'shift', 'i')
            time.sleep(3)
            self.take_screenshot("after_ctrl_shift_i")
            
            # Strategy 2: Command Palette
            self.logger.info("Trying Command Palette...")
            pyautogui.hotkey('ctrl', 'shift', 'p')
            time.sleep(1)
            pyautogui.typewrite("GitHub Copilot: Open Chat", interval=0.05)
            pyautogui.press('enter')
            time.sleep(3)
            self.take_screenshot("after_command_palette")
            
            # Strategy 3: Multiple click positions for input field
            screen_width, screen_height = pyautogui.size()
            
            click_positions = [
                (screen_width // 2, int(screen_height * 0.9)),  # Bottom center
                (screen_width // 2, int(screen_height * 0.85)), # Slightly higher
                (int(screen_width * 0.3), int(screen_height * 0.9)), # Bottom left area
                (int(screen_width * 0.7), int(screen_height * 0.9)), # Bottom right area
            ]
            
            for i, (x, y) in enumerate(click_positions):
                self.logger.info(f"Clicking position {i+1}: ({x}, {y})")
                pyautogui.click(x, y)
                time.sleep(1)
            
            # Clear and type prompt
            self.logger.info("💬 Typing final prompt...")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            
            prompt = f"""🎯 FINAL AUTOMATION TEST 🎯

Hello from the final local VSCode Desktop automation!

✅ Local VSCode Desktop targeted (NOT Web/Windsurf)
✅ Multiple Copilot opening methods tried
✅ Multiple input field click strategies used
✅ This prompt automatically typed and sent

Please confirm you received this in GitHub Copilot chat.

Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
            
            pyautogui.typewrite(prompt, interval=0.02)
            time.sleep(2)
            self.take_screenshot("after_typing")
            
            # Send prompt
            self.logger.info("⏎ Sending final prompt...")
            pyautogui.press('enter')
            time.sleep(2)
            self.take_screenshot("after_send")
            
            self.logger.info("✅ Final prompt sent!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending prompt: {e}")
            return False
    
    def automation_worker(self):
        """Main automation worker"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🎯 FINAL LOCAL VSCODE DESKTOP AUTOMATION")
            self.logger.info("=" * 60)
            
            self.update_status("Running", "orange")
            
            # Step 1: Find and focus VSCode
            self.update_progress("Finding LOCAL VSCode Desktop...")
            processes = self.find_local_vscode_processes()
            
            if not processes:
                self.logger.error("No LOCAL VSCode Desktop found!")
                self.update_status("Failed", "red")
                return False
            
            self.update_progress("Focusing LOCAL VSCode Desktop...")
            if not self.focus_local_vscode():
                self.logger.error("Failed to focus VSCode")
                self.update_status("Failed", "red")
                return False
            
            # Step 2: Take initial screenshot
            self.update_progress("Taking initial screenshot...")
            self.take_screenshot("initial")
            
            # Step 3: Countdown
            for i in range(5, 0, -1):
                if not self.is_running:
                    return False
                self.update_progress(f"Starting in {i}s...")
                time.sleep(1)
            
            # Step 4: Send prompt
            self.update_progress("Sending final prompt...")
            if not self.send_final_prompt():
                self.update_status("Failed", "red")
                return False
            
            # Step 5: Wait for feedback
            self.update_progress("✅ Automation complete! Please provide feedback.", "green")
            self.update_status("Waiting for feedback", "blue")
            
            self.logger.info("🔄 Waiting for user feedback...")
            
            # Wait for feedback with timeout
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while not self.feedback_received and self.is_running:
                if time.time() - start_time > timeout:
                    self.logger.warning("Feedback timeout reached")
                    break
                time.sleep(1)
            
            if self.feedback_received:
                self.logger.info("📝 Processing user feedback...")
                self.process_feedback()
            
            self.update_status("✅ Completed", "green")
            return True
            
        except Exception as e:
            self.logger.error(f"Automation error: {e}")
            self.update_status("Error", "red")
            return False
        finally:
            def reset_buttons():
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.is_running = False
            self.root.after(0, reset_buttons)
    
    def process_feedback(self):
        """Process user feedback and take action"""
        feedback = self.user_feedback.lower()
        
        if "success" in feedback:
            self.logger.info("🎉 SUCCESS! Automation achieved its goal!")
            self.update_progress("🎉 SUCCESS! Prompt successfully delivered!", "green")
            
        elif "failed" in feedback:
            self.logger.warning("❌ FAILED! Need to investigate and improve...")
            self.update_progress("❌ FAILED! Analysis needed for improvement.", "red")
            
        elif "partial" in feedback:
            self.logger.info("⚠️ PARTIAL SUCCESS! Some improvement needed...")
            self.update_progress("⚠️ PARTIAL! Copilot opened but text input failed.", "orange")
            
        else:
            self.logger.info(f"📝 Custom feedback received: {self.user_feedback}")
            self.update_progress("📝 Custom feedback processed.", "blue")
    
    def start_automation(self):
        """Start automation"""
        if self.is_running:
            return
            
        self.is_running = True
        self.feedback_received = False
        self.user_feedback = ""
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start automation thread
        self.automation_thread = threading.Thread(target=self.automation_worker)
        self.automation_thread.daemon = True
        self.automation_thread.start()
    
    def stop_automation(self):
        """Stop automation"""
        self.is_running = False
        self.update_status("Stopping...", "orange")
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.logger.info("🛑 Automation stopped by user")
        self.update_status("Stopped", "red")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

def main():
    print("🎯 Starting Final Local VSCode Desktop Automation...")
    app = FinalAutomationSolution()
    app.run()

if __name__ == "__main__":
    main()
