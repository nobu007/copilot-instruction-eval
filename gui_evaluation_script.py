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

# --- GUI Stop Button --- 
def create_stop_button_window(stop_event):
    """Creates and runs a simple Tkinter window with a stop button."""
    def on_stop():
        logger.info("STOP button pressed. Signaling main thread to terminate.")
        stop_event.set()
        root.destroy()

    root = tk.Tk()
    root.title("Script Control")
    root.geometry("250x100")
    root.protocol("WM_DELETE_WINDOW", on_stop) # Handle window close

    label = ttk.Label(root, text="Selenium script is running.")
    label.pack(pady=10)

    stop_button = ttk.Button(root, text="STOP SCRIPT", command=on_stop)
    stop_button.pack(pady=10)
    
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
        time.sleep(3)  # ブラウザが起動するのを短時間待つ
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
def safe_find_and_act(driver, selector, action_func, stop_event, retries=3, delay=1, wait_condition=EC.element_to_be_clickable):
    """
    Safely finds an element and performs an action, with retries for common exceptions.
    """
    for i in range(retries):
        try:
            element = WebDriverWait(driver, 5).until(
                wait_condition((By.CSS_SELECTOR, selector))
            )
            action_func(element)
            return True
        except (StaleElementReferenceException, InvalidElementStateException, TimeoutException, NoSuchElementException) as e:
            if stop_event.is_set(): raise InterruptedException("Stop signal received during action.")
            logger.warning(f"Action on selector '{selector}' failed (attempt {i+1}/{retries}): {type(e).__name__}. Retrying in {delay}s...")
            time.sleep(delay)
    logger.error(f"Action on selector '{selector}' failed after {retries} retries.")
    return False

def wait_for_response_with_progress(driver, timeout, selector, initial_count, stop_event):
    """
    Waits for the number of elements matching the selector to be greater than initial_count.
    Provides progress logging and is interruptible.
    """
    logger.info(f"Waiting for new element to appear for selector: '{selector}'")
    start_time = time.time()
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        # Use carriage return to show progress on a single line in the terminal
        print(f"  ... waiting for response ... {elapsed}s / {timeout}s", end='\r')

        if stop_event.is_set():
            print()
            raise InterruptedException("Stop signal received during wait.")
        
        current_count = len(driver.find_elements(By.CSS_SELECTOR, selector))
        if current_count > initial_count:
            print() # Newline after progress bar
            logger.info(f"New element found. Total count: {current_count}")
            return True
        
        time.sleep(1)
    
    print() # Newline after progress bar
    return False

def evaluate_prompt(driver, prompt_id, prompt_text, stop_event, debug_pause=False, prompt_index=0, total_prompts=0):
    progress_str = f"({prompt_index}/{total_prompts})" if total_prompts > 0 else ""
    logger.info(f"--- Starting evaluation for prompt ID: {prompt_id} {progress_str} ---")
    start_time = time.time()
    try:
        # 1. Open the chat panel if not already open.
        logger.info("Step 1/3: Checking chat panel state...")
        try:
            driver.find_element(By.CSS_SELECTOR, SELECTORS['chat']['input'])
            logger.info("...Chat panel is already open.")
        except NoSuchElementException:
            logger.info("...Chat panel is closed. Attempting to open.")
            if not safe_find_and_act(driver, SELECTORS['chat']['launcher'], lambda el: el.click(), stop_event):
                raise Exception("Failed to click chat launcher to open panel.")
            logger.info("...Chat panel opened successfully.")

        # 2. Input the prompt and submit by sending the Enter key.
        logger.info("Step 2/3: Inputting prompt and submitting...")
        initial_response_count = len(driver.find_elements(By.CSS_SELECTOR, SELECTORS['chat']['responseContainer']))

        def js_input_and_submit_action(element):
            # Use JavaScript to directly set the value for robustness.
            driver.execute_script("arguments[0].value = arguments[1];", element, prompt_text)
            # Dispatch an 'input' event for the web app's framework to detect the change.
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            # Allow a moment for the app to process the input.
            time.sleep(0.5)
            # Submit by sending the Enter key, the most reliable method for chat inputs.
            element.send_keys(Keys.ENTER)

        if not safe_find_and_act(driver, SELECTORS['chat']['input'], js_input_and_submit_action, stop_event, wait_condition=EC.presence_of_element_located):
            raise Exception("Failed to input prompt and submit with Enter key.")
        logger.info("...Prompt text input and submitted successfully.")

        if debug_pause:
            input("\n>>> DEBUG MODE: Prompt submitted. Please inspect the browser now. Press Enter to continue...\n")

        # 3. Wait for and process the response.
        logger.info(f"Step 3/3: Waiting for new response (initial count: {initial_response_count})...")
        if not wait_for_response_with_progress(driver, 60, SELECTORS['chat']['responseContainer'], initial_response_count, stop_event):
            raise TimeoutException(f"Timeout while waiting for response to prompt ID: {prompt_id}")
        logger.info("...New response container detected.")
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000

        # 5. Extract the latest response.
        response_elements = driver.find_elements(By.CSS_SELECTOR, SELECTORS['chat']['responseContainer'])
        latest_response_element = response_elements[-1]
        response_text = latest_response_element.text

        logger.info(f"Successfully evaluated prompt ID: {prompt_id}")
        return response_text, response_time_ms, None

    except TimeoutException:
        error_message = f"Timeout while waiting for response to prompt ID: {prompt_id}"
        logger.error(error_message)
        driver.save_screenshot(f'error_prompt_{prompt_id}_timeout.png')
        logger.info(f"Saved screenshot to error_prompt_{prompt_id}_timeout.png")
        return None, None, error_message
    except Exception as e:
        error_message = f"An error occurred for prompt ID {prompt_id}: {e}"
        logger.error(error_message)
        driver.save_screenshot(f'error_prompt_{prompt_id}_exception.png')
        logger.info(f"Saved screenshot to error_prompt_{prompt_id}_exception.png")
        return None, None, str(e)

# --- ログ書き込み ---
def log_result(result):
    """ログファイルに結果を追記する"""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')

# --- セレクタダンプ機能 ---
def get_selector_for_element(element):
    """Selenium要素から一意のCSSセレクタを生成する（試行）"""
    parts = []
    tag = element.tag_name
    
    element_id = element.get_attribute('id')
    if element_id:
        return f"#{element_id}"

    parts.append(tag)
    
    class_attr = element.get_attribute('class')
    if class_attr:
        # スペースでクラスを分割し、最初のものを取る
        first_class = class_attr.split(' ')[0]
        if first_class:
            parts.append(f".{first_class}")

    for attr in ['aria-label', 'title', 'placeholder', 'name']:
        value = element.get_attribute(attr)
        if value:
            parts.append(f'[{attr}="{value}"]')
            break # 最初のユニークな属性で十分とする
            
    return ''.join(parts)

def wait_for_app_to_load(driver, max_wait_seconds=30, retry_interval=5):
    """
    Waits for the VSCode web application to be fully loaded, showing progress.
    Differentiates between first load and subsequent attachments.
    """
    logger.info("Checking application readiness...")

    # If not on the correct page, navigate there first.
    if GITHUB_BASE_URL not in driver.current_url:
        logger.info(f"Navigating to the target URL: {GITHUB_BASE_URL}")
        driver.get(GITHUB_BASE_URL)
    else:
        logger.info("Already on the target URL. Verifying readiness...")

    max_retries = max_wait_seconds // retry_interval
    for i in range(max_retries):
        try:
            if i == 0:
                logger.info(f"Waiting for application to become interactive (up to {max_wait_seconds}s)...")
            else:
                logger.info(f"Retrying... (Attempt {i + 1}/{max_retries})")

            WebDriverWait(driver, retry_interval).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS['chat']['launcher']))
            )
            logger.info("Application is ready.")
            return True
        except TimeoutException:
            if i < max_retries - 1:
                continue  # Go to next retry
            else:
                logger.error("Application failed to load within the time limit.")
                driver.save_screenshot('error_app_load_timeout.png')
                logger.info("Saved screenshot to error_app_load_timeout.png")
                return False
    return False


def dump_all_selectors(driver):
    """ページ上の操作可能な全要素のセレクタ情報をダンプする"""
    logger.info("Dumping all interactive selectors from the current page...")
    dump_file = 'dumped_selectors.txt'
    try:
        # 操作可能な要素を幅広く検索
        elements = driver.find_elements(By.CSS_SELECTOR, "a, button, input, textarea, [role='button'], [role='link']")
        logger.info(f"Found {len(elements)} potentially interactive elements.")
        
        with open(dump_file, 'w', encoding='utf-8') as f:
            f.write(f"Selector Dump from: {driver.current_url}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("="*40 + "\n")
            
            unique_selectors = set()
            for elem in elements:
                if not elem.is_displayed():
                    continue
                
                try:
                    tag = elem.tag_name
                    text = (elem.text or elem.get_attribute('value') or elem.get_attribute('aria-label') or '').strip()
                    selector = get_selector_for_element(elem)
                    
                    if selector in unique_selectors:
                        continue
                    unique_selectors.add(selector)

                    f.write(f"Tag      : {tag}\n")
                    f.write(f"Text/Label: {text}\n")
                    f.write(f"Selector : {selector}\n")
                    f.write(f"Outer HTML: {elem.get_attribute('outerHTML')}\n")
                    f.write("-"*20 + "\n")
                except Exception:
                    pass # Stale elementなど

        logger.info(f"Successfully dumped selectors to {dump_file}")
    except Exception as e:
        logger.error(f"Failed to dump selectors: {e}")

# --- メイン処理 ---
def main():
    stop_event = threading.Event()

    # Start the GUI in a separate thread
    gui_thread = threading.Thread(target=create_stop_button_window, args=(stop_event,), daemon=True)
    gui_thread.start()
    logger.info("Starting GUI evaluation script.")

    # --- Argument Parsing ---
    port = 9222
    agent_version = None
    max_prompts = None
    chrome_path = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
    no_launch = False
    dump_selectors_flag = False
    debug_pause_flag = False
    verify_startup_flag = False
    verify_input_flag = False
    verify_input_read_back_flag = False

    for arg in sys.argv[1:]:
        if arg.startswith('--port='):
            port = int(arg.split('=', 1)[1])
        elif arg.startswith('--agent-version='):
            agent_version = arg.split('=', 1)[1]
        elif arg.startswith('--max-prompts='):
            max_prompts = int(arg.split('=', 1)[1])
        elif arg.startswith('--chrome-path='):
            chrome_path = arg.split('=', 1)[1]
        elif arg == '--no-launch':
            no_launch = True
        elif arg == '--dump-selectors':
            dump_selectors_flag = True
        elif arg == '--debug-pause':
            debug_pause_flag = True
        elif arg == '--verify-startup':
            verify_startup_flag = True
        elif arg == '--verify-input':
            verify_input_flag = True
        elif arg == '--verify-input-and-read-back':
            verify_input_read_back_flag = True

    if not no_launch:
        if not launch_chrome_for_debugging(port, chrome_path):
            return
    else:
        logger.info("Skipping Chrome launch as per --no-launch flag.")

    driver = setup_driver(port)
    if not driver:
        return

    # Wait for the application to be ready before starting any action
    if not wait_for_app_to_load(driver):
        logger.error("Exiting script because the application failed to load.")
        return

    # Handle special modes that don't require an agent version
    if dump_selectors_flag:
        logger.info("Selector dump mode activated.")
        dump_all_selectors(driver)
        logger.info("Selector dump complete. Exiting script.")
        return

    if verify_startup_flag:
        logger.info("Startup verification successful. The application is ready.")
        logger.info("Exiting as per --verify-startup flag.")
        return

    if verify_input_flag:
        logger.info("Input verification mode activated.")
        try:
            logger.info("Attempting to input test string...")
            # Check if chat panel is already open, similar to the main evaluate_prompt logic.
            try:
                driver.find_element(By.CSS_SELECTOR, SELECTORS['chat']['input'])
                logger.info("Chat panel appears to be open already.")
            except NoSuchElementException:
                logger.info("Chat panel not open, clicking launcher.")
                if not safe_find_and_act(driver, SELECTORS['chat']['launcher'], lambda el: el.click(), stop_event):
                    raise Exception("Failed to click chat launcher to open panel.")

            # Input text using JavaScript
            def js_input_action(element):
                driver.execute_script("arguments[0].value = arguments[1];", element, "Hello, this is a test.")
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            
            if not safe_find_and_act(driver, SELECTORS['chat']['input'], js_input_action, stop_event, wait_condition=EC.presence_of_element_located):
                 raise Exception("Failed to input prompt text using JavaScript.")
            
            logger.info("Input verification successful. Test string was entered.")
        except Exception as e:
            logger.error(f"Input verification failed: {e}")
            driver.save_screenshot('error_input_verification.png')
            logger.info("Saved screenshot to error_input_verification.png")
        finally:
            logger.info("Exiting as per --verify-input flag.")
        return

    if verify_input_read_back_flag:
        logger.info("Input & Read-back verification mode activated.")
        try:
            # 1. Ensure panel is open
            try:
                driver.find_element(By.CSS_SELECTOR, SELECTORS['chat']['input'])
            except NoSuchElementException:
                if not safe_find_and_act(driver, SELECTORS['chat']['launcher'], lambda el: el.click(), stop_event):
                    raise Exception("Failed to open chat panel.")

            # 2. Write, Read, and Compare
            test_string = "VERIFICATION_STRING_123"
            def write_and_read_action(element):
                # Write
                driver.execute_script("arguments[0].value = arguments[1];", element, test_string)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
                time.sleep(0.5) # Allow UI to update
                # Read back
                read_back_value = element.get_attribute('value')
                # Compare
                if read_back_value != test_string:
                    raise Exception(f"Read-back value '{read_back_value}' did not match expected '{test_string}'.")
                logger.info(f"SUCCESS: Read-back value '{read_back_value}' matches expected string.")

            if not safe_find_and_act(driver, SELECTORS['chat']['input'], write_and_read_action, stop_event, wait_condition=EC.presence_of_element_located):
                raise Exception("Write/Read/Compare action failed.")

            logger.info("Input & Read-back verification successful.")
        except Exception as e:
            logger.error(f"Input & Read-back verification failed: {e}")
            driver.save_screenshot('error_read_back_verification.png')
            logger.info("Saved screenshot to error_read_back_verification.png")
        finally:
            logger.info("Exiting as per --verify-input-and-read-back flag.")
        return

    # If not in a special mode, agent version is required for evaluation
    if not agent_version:
        logger.error("Missing required argument: --agent-version=<v1|v2>")
        logger.error("Example: python gui_evaluation_script.py --port=9222 --agent-version=v1")
        stop_event.set() # Stop GUI thread
        return

    logger.info(f"Targeting agent: {agent_version} on port: {port}")

    try:
        prompts_df = pd.read_csv(PROMPTS_FILE)
        if max_prompts:
            prompts_df = prompts_df.head(max_prompts)
        
        total_prompts = len(prompts_df)
        logger.info(f"--- Starting evaluation for {agent_version} with {total_prompts} prompts ---")

        results = []
        for index, row in prompts_df.iterrows():
            if stop_event.is_set():
                logger.info("Evaluation loop halted by user.")
                break

            prompt_id = row['id']
            prompt_text = row['prompt']
            
            response_text, response_time_ms, error = evaluate_prompt(driver, prompt_id, prompt_text, stop_event, debug_pause_flag, index + 1, total_prompts)

            result = {
                "prompt_id": prompt_id,
                "prompt_text": prompt_text,
                "agent_version": agent_version,
                "response_text": response_text,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error
            }
            log_result(result)

            # エラーが発生した場合は、次のプロンプトのために状態をリセットする
            if error:
                if stop_event.is_set():
                    logger.info("Recovery halted by user.")
                    break
                logger.warning(f"Error on prompt {prompt_id}. Attempting to recover by re-navigating to the base URL.")
                try:
                    driver.get(GITHUB_BASE_URL)
                    logger.info("After re-navigation, waiting for page to settle...")
                    time.sleep(10) # Increased wait time for UI to stabilize after reload. # Allow SPA to initialize before polling.
                    logger.info("Waiting for UI to be ready...")
                    WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS['chat']['launcher']))
                    )
                    logger.info("UI is ready. Continuing with next evaluation.")
                except Exception as e:
                    logger.error(f"Failed to recover page after error: {e}. Exiting script.")
                    driver.save_screenshot('error_recovery_failed.png')
                    logger.info("Saved screenshot to error_recovery_failed.png")
                    break # Exit the loop

        logger.info(f"--- Finished evaluation for {agent_version} ---")

        # Save results to a CSV file
        output_filename = f"evaluation_results_{agent_version}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if results:
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_filename, index=False)
            logger.info(f"Results saved to {output_filename}")

    except FileNotFoundError:
        logger.error(f"Prompts file not found at: {PROMPTS_FILE}")
    except InterruptedException as e:
        logger.warning(f"Script interrupted by user: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during evaluation: {e}")
    finally:
        stop_event.set() # Ensure GUI thread will exit
        if driver:
            driver.quit()
        logger.info("Evaluation script finished.")

if __name__ == '__main__':
    main()
