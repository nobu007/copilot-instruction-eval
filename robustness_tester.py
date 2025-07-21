import os
import json
import uuid
import time
import subprocess
import shutil

REQUESTS_DIR = '/tmp/copilot-evaluation/requests'
RESPONSES_DIR = '/tmp/copilot-evaluation/responses'
PROCESSING_DIR = '/tmp/copilot-evaluation/processing'
PROCESSED_DIR = '/tmp/copilot-evaluation/processed'
LOG_FILE = '/tmp/copilot-evaluation/robustness_test.log'

def log(message):
    """Logs a message to the console and a log file."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'[{timestamp}] {message}'
    print(log_message)
    with open(LOG_FILE, 'a') as f:
        f.write(log_message + '\n')

def clear_ipc_dirs():
    """Clears all IPC directories to ensure a clean state."""
    log('Clearing IPC directories...')
    for directory in [REQUESTS_DIR, RESPONSES_DIR, PROCESSING_DIR, PROCESSED_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
    log('IPC directories cleared.')

def create_request_file(content: dict) -> str:
    """Creates a valid request file and returns its path."""
    request_id = content['request_id']
    filepath = os.path.join(REQUESTS_DIR, f'{request_id}.json')
    with open(filepath, 'w') as f:
        json.dump(content, f)
    log(f'Created request file: {filepath}')
    return filepath

def run_executor():
    """Runs the main executor script and waits for it to complete."""
    log('Running simple_continuous_executor.py...')
    try:
        process = subprocess.run(
            ['python3', 'simple_continuous_executor.py', '--run-once'],
            capture_output=True, text=True, timeout=30
        )
        log(f'Executor finished with code {process.returncode}')
        if process.stdout:
            log(f'STDOUT:\n{process.stdout}')
        if process.stderr:
            log(f'STDERR:\n{process.stderr}')
        return process.returncode == 0
    except subprocess.TimeoutExpired as e:
        log('Executor timed out after 30 seconds.')
        if e.stdout:
            log(f'STDOUT at timeout:\n{e.stdout}')
        if e.stderr:
            log(f'STDERR at timeout:\n{e.stderr}')
        return False

def test_case_1_invalid_json():
    """Tests handling of a syntactically incorrect JSON file."""
    log('\n--- Running Test Case 1: Invalid JSON ---')
    clear_ipc_dirs()
    request_id = f'req_{uuid.uuid4()}'
    filepath = os.path.join(REQUESTS_DIR, f'{request_id}.json')
    with open(filepath, 'w') as f:
        f.write('{"request_id": "' + request_id + '",,}') # Invalid JSON
    log(f'Created invalid request file: {filepath}')
    run_executor()
    response_path = os.path.join(RESPONSES_DIR, f'resp_{request_id.replace("req_", "")}.json')
    if not os.path.exists(response_path):
        log('PASS: No response file was created for an invalid request.')
    else:
        log('FAIL: A response file was created for an invalid request.')

def test_case_2_duplicate_request():
    """Tests if the system correctly skips an already processed request."""
    log('\n--- Running Test Case 2: Duplicate Request ---')
    clear_ipc_dirs()
    request_id_val = f'req_{uuid.uuid4()}'
    request_content = {
        'id': request_id_val,
        'request_id': request_id_val,
        'test_id': 'duplicate_test',
        'instruction': 'This is a test for duplicate handling.',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'model': 'mock-model',
        'mode': 'default'
    }
    # 1. First run
    log('First run...')
    create_request_file(request_content)
    run_executor()
    
    # 2. Second run (duplicate)
    log('Second run (duplicate)...')
    create_request_file(request_content)
    run_executor()
    
    # Verification
    response_files = os.listdir(RESPONSES_DIR)
    if len(response_files) == 1:
        log(f'PASS: Exactly one response file exists ({response_files[0]}).')
    else:
        log(f'FAIL: Found {len(response_files)} response files. Expected 1.')

def test_case_3_stuck_request_recovery():
    """Tests if the system can recover from a request stuck in the 'processing' state."""
    log('\n--- Running Test Case 3: Stuck Request Recovery ---')
    clear_ipc_dirs()
    request_id_val = f'req_{uuid.uuid4()}'
    request_content = {
        'id': request_id_val,
        'request_id': request_id_val,
        'test_id': 'stuck_test',
        'instruction': 'This is a test for stuck request recovery.',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'model': 'mock-model',
        'mode': 'default'
    }
    # Simulate a stuck request by placing it directly in the processing dir
    stuck_file_path = os.path.join(PROCESSING_DIR, f'{request_content["request_id"]}.json')
    with open(stuck_file_path, 'w') as f:
        json.dump(request_content, f)
    log(f'Created stuck request file: {stuck_file_path}')
    
    # Run the executor, which should handle the stale file on startup
    run_executor()
    
    # Verification
    processed_file_path = os.path.join(PROCESSED_DIR, f'{request_content["request_id"]}.json')
    if os.path.exists(processed_file_path):
        log('PASS: Stuck request was moved to the processed directory.')
    else:
        log('FAIL: Stuck request was not handled correctly.')

def main():
    """Main function to run the test suite."""
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE))
    
    log('Starting robustness test suite...')
    test_case_1_invalid_json()
    test_case_2_duplicate_request()
    test_case_3_stuck_request_recovery()
    log('\nRobustness test suite finished.')

if __name__ == '__main__':
    main()
