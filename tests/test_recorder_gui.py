import os
import sys
import time
import threading
import socketserver
import http.server
import tempfile
import shutil
import pytest

# Add recorder module to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'copilot-recorder-poc'))
import recorder
import json
from selenium.webdriver.common.by import By

# Constants for testing
HTTP_PORT = 8000
DEBUG_PORT = 9222

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

@pytest.fixture(scope='module')
def test_page_url(tmp_path_factory):
    # Prepare a temporary directory to serve the test page
    serve_dir = tmp_path_factory.mktemp('serve')
    src_html = os.path.join(os.path.dirname(__file__), 'recorder_test_page.html')
    dst_html = os.path.join(serve_dir, 'recorder_test_page.html')
    shutil.copy(src_html, dst_html)
    # Start HTTP server
    os.chdir(serve_dir)
    httpd = socketserver.TCPServer(('127.0.0.1', HTTP_PORT), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{HTTP_PORT}/recorder_test_page.html'
    httpd.shutdown()
    thread.join()

def test_recorder_gui_records_actions(test_page_url, tmp_path):
    # Launch Chrome with remote debugging
    user_data = tmp_path / 'chrome_user_data'
    user_data.mkdir()
    chrome_path = shutil.which('google-chrome') or shutil.which('chrome') or 'google-chrome'
    chrome_proc = recorder.launch_chrome_for_debugging(
        DEBUG_PORT, str(user_data), chrome_path
    )
    # Wait for Chrome to be ready
    driver = None
    start = time.time()
    while time.time() - start < 15:
        driver = recorder.setup_driver(DEBUG_PORT)
        if driver:
            break
        time.sleep(0.5)
    if not driver:
        pytest.skip('Could not connect to Chrome for recording test')
    try:
        # Navigate to test page
        driver.get(test_page_url)
        time.sleep(1)
        # Inject listeners
        assert recorder.inject_listeners(driver), 'Failed to inject listeners'

        # Perform actions: click and input
        btn = driver.find_element(By.ID, 'testButton')
        btn.click()
        time.sleep(0.5)
        inp = driver.find_element(By.ID, 'testInput')
        inp.send_keys('hello')
        time.sleep(1)

        # Retrieve browser logs
        logs = driver.get_log('browser')
        # Filter our action logs
        prefix = 'CASCADE_ACTION_LOG:'
        recorded = []
        for entry in logs:
            msg = entry.get('message', '')
            if prefix in msg:
                try:
                    data = msg.split(prefix, 1)[1]
                    action = json.loads(data)
                    recorded.append(action)
                except Exception:
                    continue
        # Clean up listeners
        recorder.remove_listeners(driver)
        # Validate that we recorded at least click and input actions
        types = [a.get('action_type') for a in recorded]
        assert 'click' in types, f'Click action not recorded, found types: {types}'
        assert 'input' in types, f'Input action not recorded, found types: {types}'
    finally:
        driver.quit()
        chrome_proc.terminate()
