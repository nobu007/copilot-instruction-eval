# recorder.py
import os
import sys
import time
import json
import logging
import threading
import subprocess
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

RECORDING_FILE = "recorded_actions.json"

# --- JavaScript for Event Recording ---
JS_EVENT_LISTENER_SCRIPT = """
if (window.CASCADE_LISTENERS_ACTIVE) {
    console.log('Cascade listeners already active.');
} else {
    window.CASCADE_LISTENERS_ACTIVE = true;
    console.log('Activating Cascade listeners.');

    window.getElementInfo = (el) => {
        if (!el) return null;
        return {
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            className: el.className || '',
            name: el.getAttribute('name') || '',
            'aria-label': el.getAttribute('aria-label') || '',
            innerText: (el.innerText || '').substring(0, 100).trim()
        };
    };

    window.cascadeClickListener = (e) => {
        if (!window.CASCADE_LISTENERS_ACTIVE) return;
        const action = {
            action_type: 'click',
            target_element: window.getElementInfo(e.target),
            timestamp: new Date().toISOString()
        };
        console.log('CASCADE_ACTION_LOG:' + JSON.stringify(action));
    };

    window.cascadeInputListener = (e) => {
        if (!window.CASCADE_LISTENERS_ACTIVE) return;
        const action = {
            action_type: 'input',
            target_element: window.getElementInfo(e.target),
            input_text: e.target.value,
            timestamp: new Date().toISOString()
        };
        console.log('CASCADE_ACTION_LOG:' + JSON.stringify(action));
    };

    const injectListenersIntoDoc = (doc) => {
        if (!doc || doc.cascadeListenersAttached) return;
        console.log('Injecting listeners into a document...');
        doc.addEventListener('click', window.cascadeClickListener, { capture: true });
        doc.addEventListener('input', window.cascadeInputListener, { capture: true });
        doc.cascadeListenersAttached = true;
    };

    const setupIframe = (iframe) => {
        try {
            const contentDoc = iframe.contentDocument;
            if (contentDoc && contentDoc.readyState === 'complete') {
                 injectListenersIntoDoc(contentDoc);
            } else {
                 iframe.onload = () => {
                    console.log('Iframe loaded, injecting listeners.');
                    injectListenersIntoDoc(iframe.contentDocument);
                 };
            }
        } catch (e) {
            console.warn('Cascade: Could not access iframe content. Likely cross-origin.', iframe);
        }
    };

    injectListenersIntoDoc(document);
    document.querySelectorAll('iframe').forEach(setupIframe);

    window.cascadeObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1 /* Node.ELEMENT_NODE */) {
                    if (node.tagName === 'IFRAME') {
                        console.log('New iframe detected, setting up listeners.');
                        setupIframe(node);
                    } else if (node.querySelectorAll) {
                        node.querySelectorAll('iframe').forEach(setupIframe);
                    }
                }
            });
        });
    });

    window.cascadeObserver.observe(document.body, { childList: true, subtree: true });
    console.log('Cascade iframe observer is now active.');
}
"""

JS_REMOVE_LISTENERS_SCRIPT = """
if (window.CASCADE_LISTENERS_ACTIVE) {
    if (window.cascadeObserver) {
        window.cascadeObserver.disconnect();
        window.cascadeObserver = null;
        console.log('Cascade iframe observer disconnected.');
    }

    const removeListenersFromDoc = (doc) => {
        if (!doc || !doc.cascadeListenersAttached) return;
        console.log('Removing listeners from a document...');
        doc.removeEventListener('click', window.cascadeClickListener, { capture: true });
        doc.removeEventListener('input', window.cascadeInputListener, { capture: true });
        doc.cascadeListenersAttached = false;
    };

    document.querySelectorAll('iframe').forEach(iframe => {
        try {
            removeListenersFromDoc(iframe.contentDocument);
        } catch (e) {
            // Ignore cross-origin iframes
        }
    });

    removeListenersFromDoc(document);
    
    window.CASCADE_LISTENERS_ACTIVE = false;
    console.log('All Cascade event listeners deactivated.');
}
"""

def launch_chrome_for_debugging(port, user_data_dir, chrome_path):
    command = f'{chrome_path} --remote-debugging-port={port} --user-data-dir="{user_data_dir}"'
    logging.info(f"Launching Chrome with command: {command}")
    return subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def setup_driver(port):
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.info("Successfully connected to the existing Chrome browser.")
        return driver
    except WebDriverException as e:
        logging.error(f"Failed to connect to Chrome. Is it running on port {port}? Error: {e}")
        return None

def generate_selector(element_info):
    if not element_info: return None
    if element_info.get('id'):
        return f"#{element_info['id']}"
    
    selector = element_info['tag']
    if element_info.get('aria-label'):
        selector += f"[aria-label='{element_info['aria-label']}']"
    elif element_info.get('name'):
        selector += f"[name='{element_info['name']}']"
    elif element_info.get('className'):
        first_class = element_info['className'].strip().split(' ')[0]
        if first_class:
            selector += f".{first_class}"
    return selector

def poll_browser_logs_for_actions(driver, action_queue, stop_event):
    logging.info("Log polling thread started.")
    log_prefix = 'CASCADE_ACTION_LOG:'
    while not stop_event.is_set():
        try:
            browser_logs = driver.get_log('browser')
            for entry in browser_logs:
                if log_prefix in entry['message']:
                    try:
                        message_json = entry['message'].split(log_prefix, 1)[1]
                        action = json.loads(json.loads(message_json))
                        action_queue.put(action)
                    except (json.JSONDecodeError, IndexError) as e:
                        logging.warning(f"Could not parse action log: {entry['message']}. Error: {e}")
        except WebDriverException as e:
            logging.error(f"Error polling browser logs: {e}")
            action_queue.put({"action_type": "error", "message": "Lost connection to browser."})
            break
        time.sleep(0.5)
    logging.info("Log polling thread stopped.")

def playback_actions(driver, actions):
    for i, action in enumerate(actions):
        if action['action_type'] == 'feedback':
            continue
        
        logging.info(f"Executing action {i+1}/{len(actions)}: {action['action_type']}")
        selector = generate_selector(action.get('target_element'))
        if not selector:
            logging.warning(f"Could not generate selector for action {i+1}. Skipping.")
            continue

        try:
            wait = WebDriverWait(driver, 20)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if action['action_type'] == 'click':
                driver.execute_script("arguments[0].click();", element)
            elif action['action_type'] == 'input':
                element.clear()
                element.send_keys(action['input_text'])
            time.sleep(1)
        except TimeoutException:
            msg = f"Timeout: Could not find element for action {i+1} with selector: {selector}"
            logging.error(msg)
            return f"Playback failed: {msg}"
            
    return "Playback finished successfully!"

def inject_listeners(driver):
    try:
        logging.info("Injecting master listener script...")
        driver.execute_script(JS_EVENT_LISTENER_SCRIPT)
        logging.info("Master listener script injected successfully.")
        return True
    except Exception as e:
        logging.error(f"Failed to inject master JavaScript listener: {e}")
        return False

def remove_listeners(driver):
    try:
        logging.info("Executing listener removal script...")
        driver.execute_script(JS_REMOVE_LISTENERS_SCRIPT)
        logging.info("Listener removal script executed successfully.")
    except Exception as e:
        logging.error(f"Error executing listener removal script: {e}")
