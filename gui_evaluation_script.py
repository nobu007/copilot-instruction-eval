import logging
import os
import time
import subprocess
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import socket
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import queue

# --- Configuration ---
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"full_auto_test_{TIMESTAMP}.txt")

# --- Setup Logging ---
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

# Global variables for GUI control
stop_event = threading.Event()
log_queue = queue.Queue()
gui_root = None

class TkinterLogHandler(logging.Handler):
    """Custom logging handler that sends logs to GUI queue"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)

def create_gui():
    """Create the main GUI window"""
    global gui_root
    
    gui_root = tk.Tk()
    gui_root.title("VSCode Web Automation - GUI Evaluation")
    gui_root.geometry("800x600")
    
    # Main frame
    main_frame = ttk.Frame(gui_root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Control buttons frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Start/Stop buttons
    start_button = ttk.Button(control_frame, text="Start Automation", command=start_automation)
    start_button.pack(side=tk.LEFT, padx=(0, 10))
    
    stop_button = ttk.Button(control_frame, text="Stop Automation", command=stop_automation)
    stop_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Status label
    status_var = tk.StringVar(value="Ready to start automation")
    status_label = ttk.Label(control_frame, textvariable=status_var, font=("Arial", 10, "bold"))
    status_label.pack(side=tk.LEFT, padx=(20, 0))
    
    # Log display area
    log_label = ttk.Label(main_frame, text="Automation Log:", font=("Arial", 10, "bold"))
    log_label.pack(anchor='w', pady=(0, 5))
    
    log_text = scrolledtext.ScrolledText(main_frame, height=25, wrap=tk.WORD, state='disabled')
    log_text.pack(fill=tk.BOTH, expand=True)
    
    # Store references for updating
    gui_root.status_var = status_var
    gui_root.log_text = log_text
    gui_root.start_button = start_button
    gui_root.stop_button = stop_button
    
    # Handle window close
    def on_closing():
        if messagebox.askyesno("Quit", "Do you want to quit the automation?"):
            stop_event.set()
            gui_root.destroy()
    
    gui_root.protocol("WM_DELETE_WINDOW", on_closing)
    
    return gui_root

def update_gui():
    """Update GUI with log messages from queue"""
    global gui_root
    
    if gui_root is None:
        return
    
    try:
        # Process all queued log messages
        while not log_queue.empty():
            try:
                log_message = log_queue.get_nowait()
                
                # Update log display
                gui_root.log_text.config(state='normal')
                gui_root.log_text.insert(tk.END, log_message + '\n')
                gui_root.log_text.see(tk.END)
                gui_root.log_text.config(state='disabled')
                
            except queue.Empty:
                break
        
        # Schedule next update
        if not stop_event.is_set():
            gui_root.after(100, update_gui)
            
    except tk.TclError:
        # GUI has been destroyed
        pass

def start_automation():
    """Start the automation process in a separate thread"""
    global gui_root
    
    if gui_root:
        gui_root.status_var.set("Starting automation...")
        gui_root.start_button.config(state='disabled')
        gui_root.stop_button.config(state='normal')
    
    # Start automation in separate thread
    automation_thread = threading.Thread(target=run_automation, daemon=True)
    automation_thread.start()

def stop_automation():
    """Stop the automation process"""
    global gui_root
    
    stop_event.set()
    
    if gui_root:
        gui_root.status_var.set("Stopping automation...")
        gui_root.stop_button.config(state='disabled')
        
        # Re-enable start button after a delay
        def reset_buttons():
            if gui_root:
                gui_root.start_button.config(state='normal')
                gui_root.status_var.set("Automation stopped")
        
        gui_root.after(2000, reset_buttons)

def run_automation():
    """Main automation logic (extracted from original main function)"""
    global gui_root
    
    if gui_root:
        gui_root.status_var.set("Running automation...")
    
    try:
        main_automation_logic()
    except Exception as e:
        logger.error(f"Automation failed: {e}", exc_info=True)
    finally:
        if gui_root and not stop_event.is_set():
            gui_root.status_var.set("Automation completed")
            gui_root.start_button.config(state='normal')
            gui_root.stop_button.config(state='disabled')

def main_automation_logic():
    """Core automation logic (original main function content)"""
    logger.info("--- Starting Fully Automated WebDriver Test ---")
    browser_process = None
    driver = None
    
    try:
        # 1. Launch Chrome with remote debugging as a background process
        host = "127.0.0.1"
        port = 9222
        user_data_dir = os.path.expanduser("~/chrome-dev-session")
        url = "https://vscode.dev/github/nobu007/copilot-instruction-eval"
        command = (
            f'google-chrome-stable --remote-debugging-port={port} '
            f'--user-data-dir="{user_data_dir}" {url}'
        )
        logger.info(f"Executing browser launch command: {command}")
        browser_process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Browser process started with PID: {browser_process.pid}")

        # 2. Wait for the debug port to become available
        max_wait_time = 60
        start_time = time.time()
        logger.info(f"Waiting for port {port} to open...")
        while time.time() - start_time < max_wait_time:
            if stop_event.is_set():
                logger.info("Automation stopped by user")
                return
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex((host, port)) == 0:
                    logger.info(f"SUCCESS: Port {port} is now open.")
                    break
            time.sleep(1)
        else:
            raise ConnectionRefusedError(f"Port {port} did not open within {max_wait_time} seconds.")

        # 3. Attach Selenium to the browser with verbose logging
        options = Options()
        options.add_experimental_option("debuggerAddress", f"{host}:{port}")
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

        chromedriver_log_path = os.path.join(LOG_DIR, f"chromedriver_{TIMESTAMP}.log")
        service = ChromeService(
            executable_path=ChromeDriverManager().install(),
            service_args=["--verbose"],
            log_path=chromedriver_log_path
        )
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f"ChromeDriver logs will be saved to: {chromedriver_log_path}")

        logger.info("SUCCESS: Successfully attached to browser.")
        logger.info(f"Page title: {driver.title}")

        # 4. Find and switch to the main workbench iframe
        wait = WebDriverWait(driver, 120)
        try:
            logger.info("Attempting to find and switch to the main iframe...")
            
            # Check for stop event during wait
            def check_stop_condition(driver):
                if stop_event.is_set():
                    raise TimeoutException("Stopped by user")
                return True
            
            main_iframe_selector = (By.CSS_SELECTOR, 'iframe.webview.ready')
            
            # Custom wait with stop event check
            start_time = time.time()
            while time.time() - start_time < 120:
                if stop_event.is_set():
                    logger.info("Automation stopped by user during iframe search")
                    return
                
                try:
                    iframe = driver.find_element(*main_iframe_selector)
                    driver.switch_to.frame(iframe)
                    logger.info("SUCCESS: Switched to the main iframe.")
                    break
                except:
                    time.sleep(1)
            else:
                raise TimeoutException("Main iframe not found within timeout")

            # 5. Now, find the Copilot chat iframe within the main iframe.
            try:
                # A small wait can help ensure nested elements are ready.
                for i in range(5):
                    if stop_event.is_set():
                        logger.info("Automation stopped by user during wait")
                        return
                    time.sleep(1)
                
                copilot_iframe_xpath = (
                    "//iframe[contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'chat') or "
                    "contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'copilot')]"
                )
                
                logger.info(f"Waiting for Copilot iframe with robust XPath...")
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, copilot_iframe_xpath)))
                logger.info("SUCCESS: Switched to the Copilot chat iframe.")

                logger.info("Successfully inside the Copilot chat frame. Ready for interaction.")
                # Interaction logic (e.g., sending prompts, reading responses) will be added here.
                
                driver.switch_to.parent_frame() # Exit the copilot iframe
                logger.info("Switched back to the main iframe.")

            except TimeoutException:
                logger.error("TIMEOUT: Copilot chat iframe was not found within the main iframe.")
                # Diagnostic step: save the HTML of the main iframe's body to see what's inside.
                try:
                    main_iframe_content = driver.find_element(By.TAG_NAME, 'body').get_attribute('innerHTML')
                    diag_html_path = os.path.join(LOG_DIR, f"diagnostic_main_iframe_{TIMESTAMP}.html")
                    with open(diag_html_path, "w", encoding="utf-8") as f:
                        f.write(main_iframe_content)
                    logger.info(f"Saved main iframe content for diagnostics to: {diag_html_path}")
                except Exception as e:
                    logger.error(f"Could not get or save main iframe content: {e}")

            # Switch back to the main document before finishing
            driver.switch_to.default_content()
            logger.info("Switched back to the main document.")

        except TimeoutException:
            logger.error("TIMEOUT: The main iframe was not found within the 120-second limit.")
            # Save diagnostics
            screenshot_path = os.path.join(LOG_DIR, f"iframe_error_screenshot_{TIMESTAMP}.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Saved error screenshot to: {screenshot_path}")
            with open(os.path.join(LOG_DIR, f"iframe_error_source_{TIMESTAMP}.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info("Saved page source for error analysis.")

    except Exception as e:
        logger.error(f"An unexpected error occurred in main execution: {e}", exc_info=True)

    finally:
        if driver:
            logger.info("--- Capturing Final Browser State ---")
            try:
                console_logs = driver.get_log('browser')
                if console_logs:
                    logger.info("--- Browser Console Logs ---")
                    for log in console_logs:
                        logger.info(f"- LEVEL: {log.get('level')}, MESSAGE: {log.get('message')}")
                else:
                    logger.info("No browser console logs found.")
            except Exception as log_e:
                logger.error(f"Failed to retrieve browser console logs: {log_e}")
            
            logger.info("Detaching from browser.")
            driver.quit()
        
        if browser_process:
            logger.info(f"Terminating browser process (PID: {browser_process.pid}).")
            browser_process.terminate()
            browser_process.wait(timeout=5)
            if browser_process.poll() is None: # still running
                logger.warning(f"Browser process {browser_process.pid} did not terminate gracefully, killing it.")
                browser_process.kill()
        logger.info("--- Test Complete ---")

def main():
    """Main function that sets up GUI and starts the application"""
    global gui_root
    
    # Setup GUI logging handler
    gui_log_handler = TkinterLogHandler(log_queue)
    gui_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(gui_log_handler)
    
    # Create and setup GUI
    gui_root = create_gui()
    
    # Start GUI update loop
    update_gui()
    
    # Start the GUI main loop
    try:
        gui_root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    finally:
        stop_event.set()
        if gui_root:
            try:
                gui_root.destroy()
            except:
                pass

if __name__ == "__main__":
    main()
