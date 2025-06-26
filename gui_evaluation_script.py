import os
import json
import time
import logging
import sys
import pandas as pd
import subprocess
from datetime import datetime, timezone
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, InvalidElementStateException, NoSuchElementException
import tkinter as tk
from tkinter import ttk
import threading

# --- Custom Exception for interruption ---
class InterruptedException(Exception):
    pass

# --- Shared State & GUI Control ---
class SharedState:
    """A simple class to share state between the main and GUI threads."""
    def __init__(self):
        self.status = "Initializing..."
        self.progress = ""
        self.stop_event = threading.Event()  # For GUI to signal main thread
        self.gui_shutdown_event = threading.Event() # For main thread to command GUI shutdown

def create_gui(shared_state, selenium_thread):
    """
    Creates and runs the Tkinter GUI in the main thread.
    """
    root = tk.Tk()
    root.title("Script Control")
    root.geometry("350x150")

    def on_stop():
        """Handles stop button click or window close."""
        if not shared_state.stop_event.is_set():
            logger.info("STOP signal received. Notifying Selenium thread.")
            shared_state.stop_event.set()
        # The GUI will be destroyed after the selenium thread is joined.

    root.protocol("WM_DELETE_WINDOW", on_stop)

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    status_label = ttk.Label(main_frame, text="Initializing...", font=("Segoe UI", 10))
    status_label.pack(pady=5, anchor='w')

    progress_label = ttk.Label(main_frame, text="", font=("Segoe UI", 10))
    progress_label.pack(pady=5, anchor='w')

    stop_button = ttk.Button(main_frame, text="STOP SCRIPT", command=on_stop)
    stop_button.pack(pady=20)

    def update_labels():
        """Periodically updates GUI labels from shared state."""
        if not selenium_thread.is_alive():
            # Worker thread is done, so we can close the GUI.
            if root.winfo_exists():
                root.destroy()
            return

        try:
            if root.winfo_exists():
                status_label.config(text=shared_state.status)
                progress_label.config(text=shared_state.progress)
                root.after(250, update_labels)
        except tk.TclError:
            pass # Window was destroyed.

    # Start the polling loop and the main event loop.
    update_labels()
    root.mainloop()

# --- 初期設定 ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# --- 定数定義 ---
PROMPTS_FILE = 'prompts.csv'
SELECTORS_FILE = 'selectors.json'
LOG_FILE = 'gui_evaluation_logs.jsonl'
GITHUB_BASE_URL = 'https://vscode.dev/tunnel/s10610n20/home/jinno/copilot-instruction-eval?vscode-lang=ja'

with open(SELECTORS_FILE, 'r', encoding='utf-8') as f:
    SELECTORS = json.load(f)

# --- WebDriverのセットアップ ---
def launch_chrome_for_debugging(port, chrome_path):
    """指定されたポートでリモートデバッグを有効にしてChromeを起動する"""
    command = f'"{chrome_path}" --remote-debugging-port={port} --user-data-dir="C:\\Chrome_dev_session"'
    logger.info(f"Launching Chrome with command: {command}")
    try:
        subprocess.Popen(command, shell=True)
        logger.info(f"Chrome launched. Waiting a few seconds for it to initialize...")
        time.sleep(3)
    except FileNotFoundError:
        logger.error(f"Chrome executable not found at {chrome_path}. Please specify the correct path using --chrome-path.")
        return False
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")
        return False
    return True

def setup_driver(port):
    """既存のChromeブラウザに接続するためのWebDriverをセットアップする"""
    logger.info(f"Connecting to Chrome browser on port {port}...")
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Successfully connected to the existing Chrome browser.")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to browser on port {port}. Is Chrome running with --remote-debugging-port={port}?")
        logger.error(f"Error details: {e}")
        return None

# --- Copilot Agent操作 ---
def safe_find_and_act(driver, selector, action_func, shared_state, retries=3, delay=1, wait_condition=EC.element_to_be_clickable):
    for i in range(retries):
        try:
            if shared_state.stop_event.is_set(): raise InterruptedException("Stop signal received during action.")
            element = WebDriverWait(driver, 5).until(wait_condition((By.CSS_SELECTOR, selector)))
            action_func(element)
            return True
        except (StaleElementReferenceException, InvalidElementStateException, TimeoutException, NoSuchElementException) as e:
            if shared_state.stop_event.is_set(): raise InterruptedException("Stop signal received during action.")
            logger.warning(f"Action on selector '{selector}' failed (attempt {i+1}/{retries}): {type(e).__name__}. Retrying...")
            time.sleep(delay)
    logger.error(f"Action on selector '{selector}' failed after {retries} retries.")
    return False

def wait_for_response_with_progress(driver, timeout, selector, initial_count, shared_state):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shared_state.stop_event.is_set():
            raise InterruptedException("Stop signal received during wait.")
        elapsed = int(time.time() - start_time)
        shared_state.status = f"Waiting for response... {elapsed}s / {timeout}s"
        current_count = len(driver.find_elements(By.CSS_SELECTOR, selector))
        if current_count > initial_count:
            logger.info(f"New element found. Total count: {current_count}")
            return True
        time.sleep(0.5)
    return False

def evaluate_prompt(driver, prompt_id, prompt_text, shared_state, debug_pause=False, prompt_index=0, total_prompts=0):
    shared_state.progress = f"Prompt ({prompt_index}/{total_prompts})"
    logger.info(f"--- Starting evaluation for prompt ID: {prompt_id} {shared_state.progress} ---")
    start_time = time.time()
    try:
        shared_state.status = "Step 1/3: Checking chat panel..."
        try:
            driver.find_element(By.CSS_SELECTOR, SELECTORS['chat']['input'])
            logger.info("...Chat panel is already open.")
        except NoSuchElementException:
            logger.info("...Chat panel is closed. Attempting to open.")
            if not safe_find_and_act(driver, SELECTORS['chat']['launcher'], lambda el: el.click(), shared_state):
                raise Exception("Failed to click chat launcher to open panel.")
            logger.info("...Chat panel opened successfully.")

        shared_state.status = "Step 2/3: Inputting prompt..."
        initial_response_count = len(driver.find_elements(By.CSS_SELECTOR, SELECTORS['chat']['responseContainer']))

        def js_input_and_submit_action(element):
            driver.execute_script("arguments[0].value = arguments[1];", element, prompt_text)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            time.sleep(0.5)
            element.send_keys(Keys.ENTER)

        if not safe_find_and_act(driver, SELECTORS['chat']['input'], js_input_and_submit_action, shared_state, wait_condition=EC.presence_of_element_located):
            raise Exception("Failed to input prompt and submit with Enter key.")
        logger.info("...Prompt text input and submitted successfully.")

        if debug_pause:
            shared_state.status = "Debug pause: inspect browser."
            input("\n>>> DEBUG MODE: Prompt submitted. Please inspect the browser now. Press Enter to continue...\n")

        shared_state.status = f"Step 3/3: Waiting for response... (max 60s)"
        if not wait_for_response_with_progress(driver, 60, SELECTORS['chat']['responseContainer'], initial_response_count, shared_state):
            raise TimeoutException(f"Timeout while waiting for response to prompt ID: {prompt_id}")
        
        logger.info("...New response container detected.")
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        response_elements = driver.find_elements(By.CSS_SELECTOR, SELECTORS['chat']['responseContainer'])
        latest_response_element = response_elements[-1]
        response_text = latest_response_element.text

        logger.info(f"Successfully evaluated prompt ID: {prompt_id}")
        return response_text, response_time_ms, None

    except InterruptedException as e:
        logger.error(f"An error occurred for prompt ID {prompt_id}: {e}")
        driver.save_screenshot(f'error_prompt_{prompt_id}_interrupted.png')
        raise e # Re-raise to stop the main loop
    except TimeoutException:
        error_message = f"Timeout while waiting for response to prompt ID: {prompt_id}"
        logger.error(error_message)
        driver.save_screenshot(f'error_prompt_{prompt_id}_timeout.png')
        return None, None, error_message
    except Exception as e:
        logger.error(f"An error occurred for prompt ID {prompt_id}: {e}")
        shared_state.status = f"Error on prompt {prompt_id}"
        driver.save_screenshot(f'error_prompt_{prompt_id}_exception.png')
        return None, 0, str(e)

# --- ログ書き込み ---
def log_result(result):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')

# --- アプリケーション状態確認 ---
def wait_for_app_to_load(driver, max_wait_seconds=30):
    logger.info("Checking application readiness...")
    if GITHUB_BASE_URL not in driver.current_url:
        logger.info(f"Navigating to the target URL: {GITHUB_BASE_URL}")
        driver.get(GITHUB_BASE_URL)
    else:
        logger.info("Already on the target URL. Verifying readiness...")
    try:
        WebDriverWait(driver, max_wait_seconds).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS['chat']['launcher']))
        )
        logger.info("Application is ready.")
        return True
    except TimeoutException:
        logger.error("Application failed to load within the time limit.")
        driver.save_screenshot('error_app_load_timeout.png')
        return False

# --- メイン処理 ---
def run_selenium_task(shared_state, args):
    """Runs the entire Selenium process in a background thread."""
    driver = None
    try:
        if not args.no_launch:
            if not launch_chrome_for_debugging(args.port, args.chrome_path): return
        
        driver = setup_driver(args.port)
        if not driver: return

        if not wait_for_app_to_load(driver): return

        logger.info(f"Targeting agent: {args.agent_version} on port: {args.port}")
        
        try:
            prompts_df = pd.read_csv(PROMPTS_FILE)
        except FileNotFoundError:
            logger.error(f"Prompts file not found at {PROMPTS_FILE}")
            return

        if args.max_prompts:
            prompts_df = prompts_df.head(args.max_prompts)

        logger.info(f"--- Starting evaluation for {args.agent_version} with {len(prompts_df)} prompts ---")
        
        results = []
        for index, row in prompts_df.iterrows():
            if shared_state.stop_event.is_set():
                logger.info("Stop signal received. Halting evaluation loop.")
                break

            prompt_id = row['id']
            prompt_text = row['prompt']
            
            response_text, response_time, error = evaluate_prompt(
                driver, prompt_id, prompt_text, shared_state, 
                debug_pause=args.debug_pause, prompt_index=index + 1, total_prompts=len(prompts_df)
            )

            result = {
                'prompt_id': prompt_id, 'prompt_text': prompt_text, 'response_text': response_text,
                'response_time_ms': response_time, 'error': error, 'agent_version': args.agent_version,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            results.append(result)
            log_result(result)

            if error:
                if shared_state.stop_event.is_set():
                    logger.info("Recovery halted by user.")
                    break
                logger.warning(f"Error on prompt {prompt_id}. Attempting to recover.")
                if not wait_for_app_to_load(driver):
                    logger.error("Failed to recover page after error. Exiting.")
                    driver.save_screenshot('error_recovery_failed.png')
                    break
                logger.info("Recovery successful. Continuing with next evaluation.")

        logger.info(f"--- Finished evaluation for {args.agent_version} ---")
        
        if results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'evaluation_results_{args.agent_version}_{timestamp}.csv'
            pd.DataFrame(results).to_csv(filename, index=False)
            logger.info(f"Results saved to {filename}")

    except InterruptedException as e:
        logger.info(f"Script interrupted by user: {e}")
    except Exception as e:
        logger.error(f"An unhandled exception occurred in the Selenium thread: {e}", exc_info=True)
    finally:
        logger.info("Selenium thread cleanup initiated.")
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}")
        logger.info("Selenium thread finished.")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run Selenium evaluation script with GUI.")
    parser.add_argument('--port', type=int, default=9222, help='Port for Chrome remote debugging.')
    parser.add_argument('--agent-version', type=str, required=True, choices=['v1', 'v2'], help='Agent version to test.')
    parser.add_argument('--max-prompts', type=int, help='Maximum number of prompts to evaluate.')
    parser.add_argument('--chrome-path', type=str, default='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', help='Path to Chrome executable.')
    parser.add_argument('--no-launch', action='store_true', help="Don't launch a new Chrome instance.")
    parser.add_argument('--debug-pause', action='store_true', help='Pause script after submitting a prompt for debugging.')
    args = parser.parse_args()

    shared_state = SharedState()
    
    # The Selenium task runs in a background thread.
    selenium_thread = threading.Thread(target=run_selenium_task, args=(shared_state, args))
    selenium_thread.start()

    # The GUI runs in the main thread.
    create_gui(shared_state, selenium_thread)

    # mainloop has finished, which means the GUI was closed or the worker thread finished.
    # We now wait for the worker thread to be completely done.
    logger.info("GUI closed. Waiting for Selenium thread to terminate...")
    selenium_thread.join()

    logger.info("Script finished.")

if __name__ == '__main__':
    main()