import os
import sys
import time
import json
import logging
import threading
import subprocess
from datetime import datetime
import argparse

# --- Tkinter Imports ---
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException

# --- Constants ---
AGENT_VERSION = "1.0.2"
LOG_DIR = "evaluation_logs"
DEFAULT_CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_USER_DATA_DIR = r"C:\Chrome_dev_session"

DEFAULT_SELECTORS = {
    "chat": {
        "launcher": "a.codicon-copilot-chat",
        "iframe": "iframe.webview.ready",
        "input": "div.native-edit-context[role='textbox']",
        "submit": "a.codicon-send",
        "responseContainer": "div.monaco-list-row[aria-label*='Copilot']",
        "welcomeMessage": "div.welcome-view-content"
    }
}

# --- Logger Setup ---
def setup_logger(agent_version):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_filename = os.path.join(LOG_DIR, f"evaluation_log_{agent_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

# --- Data Loading ---
def load_selectors(file_path='selectors.json'):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Could not load or parse {file_path}: {e}. Using hardcoded default selectors.")
        return DEFAULT_SELECTORS

def load_prompts(file_path='prompts.csv'):
    # This function is not used when a single prompt is provided via CLI
    pass

# --- Selenium WebDriver Setup ---
def launch_chrome_for_debugging(port, user_data_dir, chrome_path):
    if not os.path.exists(chrome_path):
        logging.error(f"Chrome executable not found at: {chrome_path}")
        return None
    command = f'"{chrome_path}" --remote-debugging-port={port} --user-data-dir="{user_data_dir}"'
    logging.info(f"Launching Chrome with command: {command}")
    process = subprocess.Popen(command, shell=True)
    time.sleep(3) # Give Chrome a moment to start
    return process

def setup_driver(port):
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info(f"Successfully connected to the existing Chrome browser.")
        return driver
    except WebDriverException as e:
        logging.error(f"Failed to connect to Chrome. Is it running with remote debugging on port {port}? Error: {e}")
        return None

# --- Core Automation Logic ---
def wait_for_app_to_load(driver, max_wait_seconds=30):
    logging.info("Checking application readiness...")
    try:
        # A reliable indicator that the main VSCode UI has loaded.
        launcher_selector = DEFAULT_SELECTORS['chat']['launcher']
        WebDriverWait(driver, max_wait_seconds).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, launcher_selector))
        )
        logging.info("Application is ready.")
        return True
    except TimeoutException:
        logging.error("Timeout: The main application UI did not appear to load in time.")
        return False

def wait_for_response_with_progress(driver, timeout, selector, initial_count, shared_state):
    start_time = time.time()
    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        shared_state.progress = f"{int(elapsed)}s / {timeout}s"
        try:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, selector))
            if current_count > initial_count:
                return True
        except StaleElementReferenceException:
            # The DOM is changing, which is expected. Just continue polling.
            pass
        time.sleep(1)
    return False

def evaluate_prompt(driver, prompt_id, prompt_text, shared_state, selectors, root):
    shared_state.status = f"Prompt {prompt_id}: Starting..."
    start_time = time.time()

    input_selector = selectors.get('chat', {}).get('input', DEFAULT_SELECTORS['chat']['input'])
    response_container_selector = selectors.get('chat', {}).get('responseContainer', DEFAULT_SELECTORS['chat']['responseContainer'])
    initial_response_count = len(driver.find_elements(By.CSS_SELECTOR, response_container_selector))

    # HYPOTHESIS: The entire chat widget is in an iframe. Let's switch to it.
    try:
        iframe_selector = selectors.get('chat', {}).get('iframe', DEFAULT_SELECTORS['chat']['iframe'])
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, iframe_selector))
        )
        logging.info("Successfully switched to chat iframe.")
    except TimeoutException:
        logging.warning("Could not find or switch to an iframe. Assuming content is in the main document.")
        driver.switch_to.default_content()

    # --- ULTIMATE SIMPLIFICATION ---
    # 1. Assume panel is closed. Click the launcher icon to open it.
    logging.info("Executing simplified sequence: Clicking launcher icon.")
    launcher_selector = selectors.get('chat', {}).get('launcher', DEFAULT_SELECTORS['chat']['launcher'])
    launcher_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, launcher_selector))
    )
    driver.execute_script("arguments[0].click();", launcher_icon)

    # 2. Wait for the input element to appear.
    logging.info("Waiting for chat input to appear after opening panel.")
    input_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, input_selector))
    )

    # 3. Perform clipboard paste and send keys to the fresh element reference
    root.clipboard_clear()
    root.clipboard_append(prompt_text)
    root.update()
    
    input_element.send_keys(Keys.CONTROL, 'v')
    time.sleep(0.5) # Allow a moment for UI to update, e.g., send button to become enabled

    # 4. Find and click the correct send button
    logging.info("Finding and clicking the send button...")
    submit_selector = selectors.get('chat', {}).get('submit', DEFAULT_SELECTORS['chat']['submit'])
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector))
    )
    driver.execute_script("arguments[0].click();", submit_button)

    shared_state.status = f"Prompt {prompt_id}: Waiting for response..."
    if not wait_for_response_with_progress(driver, 90, response_container_selector, initial_response_count, shared_state):
        raise TimeoutException("Timeout waiting for new response.")
    
    end_time = time.time()
    response_time = end_time - start_time
    
    response_elements = driver.find_elements(By.CSS_SELECTOR, response_container_selector)
    response_text = response_elements[-1].text if response_elements else ""
    
    logging.info(f"Successfully processed prompt ID {prompt_id} in {response_time:.2f}s.")
    return response_text, response_time

# --- GUI ---
class SharedState:
    def __init__(self):
        self.status = "Initializing..."
        self.progress = ""
        self.stop_event = threading.Event()
        self.task_done = threading.Event()

def create_gui(shared_state):
    root = tk.Tk()
    root.title(f"Copilot Evaluation Agent v{AGENT_VERSION}")
    root.geometry("500x400")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    status_label = ttk.Label(main_frame, text="Status:", font=("Segoe UI", 10, "bold"))
    status_label.pack(anchor='w')

    status_var = tk.StringVar(value=shared_state.status)
    status_display = ttk.Label(main_frame, textvariable=status_var, wraplength=480)
    status_display.pack(anchor='w', fill=tk.X, pady=5)

    progress_label = ttk.Label(main_frame, text="Progress:", font=("Segoe UI", 10, "bold"))
    progress_label.pack(anchor='w', pady=(10, 0))

    progress_var = tk.StringVar(value=shared_state.progress)
    progress_display = ttk.Label(main_frame, textvariable=progress_var)
    progress_display.pack(anchor='w', fill=tk.X, pady=5)

    log_label = ttk.Label(main_frame, text="Log:", font=("Segoe UI", 10, "bold"))
    log_label.pack(anchor='w', pady=(10, 0))
    
    log_text = scrolledtext.ScrolledText(main_frame, height=10, wrap=tk.WORD, state='disabled')
    log_text.pack(fill=tk.BOTH, expand=True, pady=5)

    def stop_script():
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to stop the evaluation?"):
            shared_state.stop_event.set()
            shared_state.status = "Stopping..."

    stop_button = ttk.Button(main_frame, text="Stop Evaluation", command=stop_script)
    stop_button.pack(pady=10)

    def update_ui():
        status_var.set(shared_state.status)
        progress_var.set(shared_state.progress)
        if shared_state.task_done.is_set() and not shared_state.stop_event.is_set():
            root.after(2000, root.destroy)
        elif shared_state.stop_event.is_set():
             root.destroy()
        else:
            root.after(100, update_ui)

    root.protocol("WM_DELETE_WINDOW", stop_script)
    return root, update_ui

# --- Main Task Thread ---
def selenium_task(shared_state, cli_args, root):
    driver = None
    chrome_process = None
    try:
        log_filename = setup_logger(AGENT_VERSION)
        shared_state.status = f"Log file: {log_filename}"
        selectors = load_selectors()

        if not cli_args.prompt:
            logging.error("No prompt provided. Please use the --prompt argument.")
            shared_state.status = "Error: No prompt provided."
            return

        driver = setup_driver(cli_args.port)
        if not driver:
            shared_state.status = f"Launching new Chrome session on port {cli_args.port}..."
            chrome_process = launch_chrome_for_debugging(cli_args.port, cli_args.user_data_dir, cli_args.chrome_path)
            driver = setup_driver(cli_args.port)
            if not driver:
                raise Exception("Failed to start or connect to Chrome.")

        shared_state.status = "Navigating to target URL..."
        driver.get(cli_args.url)
        
        logging.info("Initiating a 10-second hard sleep immediately after navigation to allow the app to fully stabilize...")
        time.sleep(10)

        if not wait_for_app_to_load(driver):
            raise Exception("Application did not load correctly.")

        evaluate_prompt(driver, "cli_prompt", cli_args.prompt, shared_state, selectors, root)

        shared_state.status = "Evaluation finished successfully!"
        logging.info("Script finished successfully.")

    except Exception as e:
        logging.error(f"A critical error occurred in the main task: {e}")
        shared_state.status = f"Critical Error: {e}"
        if driver:
            try:
                os.makedirs(LOG_DIR, exist_ok=True)
                screenshot_path = os.path.join(LOG_DIR, f"critical_error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                driver.save_screenshot(screenshot_path)
                logging.info(f"Saved error screenshot to {screenshot_path}")
            except Exception as se:
                logging.error(f"Failed to save screenshot: {se}")

    finally:
        shared_state.task_done.set()
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logging.warning(f"Error quitting driver: {e}")
        if chrome_process:
            try:
                chrome_process.terminate()
            except Exception as e:
                logging.warning(f"Error terminating Chrome process: {e}")
        logging.info("Cleaned up WebDriver and Chrome process.")

# --- Entry Point ---
def parse_args():
    parser = argparse.ArgumentParser(description="Copilot Evaluation Agent")
    parser.add_argument('--prompt', type=str, required=True, help='The single prompt to evaluate.')
    parser.add_argument('--url', type=str, default="https://vscode.dev/tunnel/s10610n20/home/jinno/copilot-instruction-eval?vscode-lang=ja", help='The URL to open.')
    parser.add_argument('--port', type=int, default=9222, help='The remote debugging port for Chrome.')
    parser.add_argument('--chrome-path', type=str, default=DEFAULT_CHROME_PATH, help='Path to the Chrome executable.')
    parser.add_argument('--user-data-dir', type=str, default=DEFAULT_USER_DATA_DIR, help='Path to the Chrome user data directory.')
    return parser.parse_args()

def main():
    args = parse_args()
    shared_state = SharedState()
    
    root, update_ui_func = create_gui(shared_state)

    worker_thread = threading.Thread(target=selenium_task, args=(shared_state, args, root), daemon=True)
    worker_thread.start()

    update_ui_func()
    root.mainloop()

    worker_thread.join() # Ensure thread is finished before exiting
    logging.info("Script finished.")

if __name__ == "__main__":
    main()
