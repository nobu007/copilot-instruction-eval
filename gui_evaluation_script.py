import logging
import os
import time
import subprocess
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

def main():
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
            main_iframe_selector = (By.CSS_SELECTOR, 'iframe.webview.ready')
            wait.until(EC.frame_to_be_available_and_switch_to_it(main_iframe_selector))
            logger.info("SUCCESS: Switched to the main iframe.")

            # 5. Now, find the Copilot chat iframe within the main iframe.
            try:
                # A small wait can help ensure nested elements are ready.
                time.sleep(5)
                
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

if __name__ == "__main__":
    main()
