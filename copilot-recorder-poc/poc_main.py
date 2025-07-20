# poc_main.py
import os
import sys
import time
import json
import logging
import threading
import argparse
import queue

from gui import create_gui, process_action_queue
from recorder import (
    launch_chrome_for_debugging, 
    setup_driver, 
    inject_listeners, 
    remove_listeners, 
    poll_browser_logs_for_actions, 
    playback_actions, 
    RECORDING_FILE
)

# --- Constants ---
DEFAULT_CHROME_PATH = "google-chrome"
DEFAULT_USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "Chrome_dev_session_poc")

# --- Shared State ---
class SharedState:
    def __init__(self):
        self.status_var = None
        self.log_text_widget = None
        self.buttons = {}
        self.is_recording = False
        self.recorded_actions = []
        self.action_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.driver = None
        self.log_poller_thread = None
        self.log_poller_thread_stop_event = threading.Event()

# --- Logging Setup ---
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    file_handler = logging.FileHandler("recorder_debug.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)
    logging.info("Logging configured.")

# --- Core Handlers ---
def start_recording_handler(shared_state):
    if shared_state.is_recording:
        return
    
    shared_state.is_recording = True
    shared_state.recorded_actions.clear()
    shared_state.status_var.set("Recording started...")
    shared_state.buttons["start"].config(state='disabled')
    shared_state.buttons["stop"].config(state='normal')
    shared_state.buttons["play"].config(state='disabled')
    shared_state.log_text_widget.config(state='normal')
    shared_state.log_text_widget.delete('1.0', 'end')
    shared_state.log_text_widget.config(state='disabled')

    if not inject_listeners(shared_state.driver):
        shared_state.status_var.set("Error: Failed to start recording.")
        stop_recording_handler(shared_state)
        return

    shared_state.log_poller_thread_stop_event.clear()
    shared_state.log_poller_thread = threading.Thread(
        target=poll_browser_logs_for_actions, 
        args=(shared_state.driver, shared_state.action_queue, shared_state.log_poller_thread_stop_event), 
        daemon=True
    )
    shared_state.log_poller_thread.start()

def stop_recording_handler(shared_state):
    if not shared_state.is_recording:
        return
    
    shared_state.is_recording = False
    shared_state.status_var.set("Stopping recording...")
    
    if shared_state.log_poller_thread:
        shared_state.log_poller_thread_stop_event.set()
        shared_state.log_poller_thread.join(timeout=3)

    remove_listeners(shared_state.driver)

    # Final processing of any remaining logs from the queue
    process_action_queue(shared_state) 

    if shared_state.recorded_actions:
        try:
            with open(RECORDING_FILE, 'w', encoding='utf-8') as f:
                # Filter out error actions before saving
                actions_to_save = [a for a in shared_state.recorded_actions if a.get('action_type') != 'error']
                json.dump(actions_to_save, f, indent=4)
            shared_state.status_var.set(f"Recording stopped. {len(actions_to_save)} actions saved.")
            shared_state.buttons["play"].config(state='normal')
        except IOError as e:
            shared_state.status_var.set("Error: Could not save recording.")
            logging.error(f"Failed to save recording file: {e}")
    else:
        shared_state.status_var.set("Recording stopped. No actions were recorded.")

    shared_state.buttons["start"].config(state='normal')
    shared_state.buttons["stop"].config(state='disabled')

def playback_actions_handler(shared_state):
    shared_state.buttons["play"].config(state='disabled')
    shared_state.buttons["start"].config(state='disabled')
    
    try:
        with open(RECORDING_FILE, 'r', encoding='utf-8') as f:
            actions = json.load(f)
    except FileNotFoundError:
        shared_state.status_var.set(f"Error: Recording file not found.")
        logging.error(f"Recording file not found: {RECORDING_FILE}")
        shared_state.buttons["play"].config(state='normal')
        shared_state.buttons["start"].config(state='normal')
        return

    def run_playback():
        shared_state.status_var.set(f"Starting playback of {len(actions)} actions...")
        result = playback_actions(shared_state.driver, actions)
        shared_state.status_var.set(result)
        shared_state.buttons["play"].config(state='normal')
        shared_state.buttons["start"].config(state='normal')

    playback_thread = threading.Thread(target=run_playback, daemon=True)
    playback_thread.start()

# --- Main Application Logic ---
def main_task(shared_state, args):
    chrome_process = None
    try:
        shared_state.status_var.set("Connecting to browser...")
        shared_state.driver = setup_driver(args.port)
        
        if not shared_state.driver:
            shared_state.status_var.set(f"Could not connect. Launching Chrome on port {args.port}...")
            chrome_process = launch_chrome_for_debugging(args.port, args.user_data_dir, args.chrome_path)
            time.sleep(5)
            shared_state.driver = setup_driver(args.port)

        if not shared_state.driver:
            raise RuntimeError("Failed to setup WebDriver.")

        shared_state.driver.get(args.url)
        shared_state.status_var.set("Ready. Waiting for user action.")
        shared_state.buttons['play'].config(state='normal' if os.path.exists(RECORDING_FILE) else 'disabled')
        
        shared_state.stop_event.wait()

    except Exception as e:
        logging.critical(f"Critical error in main task: {e}", exc_info=True)
        if shared_state.status_var:
            shared_state.status_var.set(f"Fatal Error: {e}")
    finally:
        if shared_state.driver:
            logging.info("Closing WebDriver.")
            shared_state.driver.quit()
        if chrome_process:
            logging.info("Terminating Chrome process.")
            chrome_process.terminate()
        logging.info("Main task finished.")

def main():
    setup_logging()
    args = parse_args()
    shared_state = SharedState()
    
    handlers = {
        "start": lambda: start_recording_handler(shared_state),
        "stop": lambda: stop_recording_handler(shared_state),
        "play": lambda: playback_actions_handler(shared_state),
    }
    
    root = create_gui(shared_state, handlers)
    
    main_thread = threading.Thread(target=main_task, args=(shared_state, args), daemon=True)
    main_thread.start()
    
    process_action_queue(shared_state)
    
    root.mainloop()
    
    logging.info("GUI closed. Signaling main task to stop.")
    shared_state.stop_event.set()
    main_thread.join(timeout=5)
    logging.info("Application shutdown complete.")

def parse_args():
    parser = argparse.ArgumentParser(description="POC Recorder")
    parser.add_argument('--url', type=str, default="https://vscode.dev/tunnel/s10610n20/home/jinno/copilot-instruction-eval?vscode-lang=ja", help='The URL to open.')
    parser.add_argument('--port', type=int, default=9222, help='The remote debugging port.')
    parser.add_argument('--chrome-path', type=str, default=DEFAULT_CHROME_PATH, help='Path to Chrome executable.')
    parser.add_argument('--user-data-dir', type=str, default=DEFAULT_USER_DATA_DIR, help='Path to Chrome user data directory.')
    return parser.parse_args()

if __name__ == "__main__":
    main()