import os
import json
import time
import logging
import sys
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
COPILOT_AGENT_URL = 'https://github.com/features/copilot'

with open(SELECTORS_FILE, 'r') as f:
    SELECTORS = json.load(f)

# --- WebDriverのセットアップ (Remote Debugging版) ---
def setup_driver_remote(port):
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
def evaluate_prompt(driver, prompt_id, prompt_text):
    logger.info(f"Evaluating prompt ID: {prompt_id}")
    start_time = time.time()
    try:
        driver.get(COPILOT_AGENT_URL)
        input_area = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS['chat']['input']))
        )
        input_area.clear()
        input_area.send_keys(prompt_text)
        driver.find_element(By.CSS_SELECTOR, SELECTORS['chat']['submitButton']).click()

        WebDriverWait(driver, 120).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, SELECTORS['chat']['thinkingIndicator']))
        )

        response_elements = driver.find_elements(By.CSS_SELECTOR, f"{SELECTORS['chat']['responseContainer']}:last-child {SELECTORS['chat']['responseElement']}")
        response_text = "\n".join([elem.text for elem in response_elements])

        response_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Successfully received response for prompt ID: {prompt_id} in {response_time_ms:.0f}ms")
        return response_text, response_time_ms, None

    except TimeoutException:
        error_msg = f"Timeout while waiting for response to prompt ID: {prompt_id}"
        logger.error(error_msg)
        return None, (time.time() - start_time) * 1000, error_msg
    except Exception as e:
        error_msg = f"An error occurred for prompt ID {prompt_id}: {e}"
        logger.error(error_msg)
        return None, (time.time() - start_time) * 1000, error_msg

# --- ログ書き込み ---
def log_result(result):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')

# --- メイン処理 ---
def main():
    logger.info("Starting GUI evaluation script (Remote Debugging Mode).")

    args = {arg.split('=')[0]: arg.split('=')[1] for arg in sys.argv[1:] if '=' in arg}
    port = int(args.get('--port', 9222))
    agent_version = args.get('--agent-version')
    max_prompts = int(args.get('--max-prompts')) if args.get('--max-prompts') else None

    if not agent_version:
        logger.error("Missing required argument: --agent-version=<v1|v2>")
        logger.error("Example: python gui_evaluation_script.py --port=9222 --agent-version=v1")
        return

    logger.info(f"Targeting agent: {agent_version} on port: {port}")

    try:
        prompts_df = pd.read_csv(PROMPTS_FILE)
        if max_prompts:
            prompts_df = prompts_df.head(max_prompts)
    except FileNotFoundError:
        logger.error(f"Prompts file not found at: {PROMPTS_FILE}")
        return

    driver = setup_driver_remote(port)
    if not driver:
        return

    try:
        logger.info(f"--- Starting evaluation for {agent_version} ---")
        for index, row in prompts_df.iterrows():
            prompt_id = row['id']
            prompt_text = row['prompt']

            response_text, response_time_ms, error = evaluate_prompt(driver, prompt_id, prompt_text)

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
            time.sleep(1)

    except Exception as e:
        logger.error(f"An unexpected error occurred during the evaluation loop: {e}")
    finally:
        logger.info(f"--- Finished evaluation for {agent_version} ---")

    logger.info("Evaluation script finished.")

if __name__ == '__main__':
    main()
