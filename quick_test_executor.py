#!/usr/bin/env python3
"""
Quick Test Executor - VSCodeプロセス管理をスキップして直接テスト実行
"""
import json
import os
import time
import uuid
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_test_request(command, params=None):
    """IPCリクエストを送信して応答を取得"""
    if params is None:
        params = {}
        
    request_id = str(uuid.uuid4())
    request = {
        "request_id": request_id,
        "command": command,
        "params": params
    }
    
    # リクエストファイル作成
    request_path = f"/tmp/copilot-evaluation/requests/{request_id}.json"
    response_path = f"/tmp/copilot-evaluation/responses/{request_id}.json"
    
    logger.info(f"Sending {command} request: {request_id}")
    
    with open(request_path, 'w') as f:
        json.dump(request, f, indent=2)
    
    # 応答待機 (最大30秒)
    for i in range(30):
        if os.path.exists(response_path):
            with open(response_path, 'r') as f:
                response = json.load(f)
            
            # クリーンアップ
            try:
                os.remove(response_path)
            except:
                pass
                
            logger.info(f"Response received: {response.get('final_status', 'unknown')}")
            return response
        
        time.sleep(1)
    
    logger.error(f"Timeout waiting for response to {request_id}")
    return None

def main():
    """メイン実行関数"""
    logger.info("=== Quick Test Executor ===")
    
    # 1. Ping テスト
    logger.info("1. Testing Ping...")
    ping_response = send_test_request("ping")
    if ping_response and ping_response.get('final_status') == 'success':
        logger.info("✅ Ping test passed")
    else:
        logger.error("❌ Ping test failed")
        return
    
    # 2. Submit Prompt テスト
    logger.info("2. Testing Submit Prompt...")
    prompt_response = send_test_request("submitPrompt", {
        "prompt": "hello"
    })
    if prompt_response and prompt_response.get('final_status') == 'success':
        logger.info("✅ Submit prompt test passed")
    else:
        logger.error("❌ Submit prompt test failed")
        return
    
    # 3. Get Current State テスト
    logger.info("3. Testing Get Current State...")
    state_response = send_test_request("getCurrentState")
    if state_response and state_response.get('final_status') == 'success':
        logger.info("✅ Get current state test passed")
    else:
        logger.error("❌ Get current state test failed")
        return
    
    logger.info("🎉 All tests passed! VSCode Copilot automation system is working correctly.")

if __name__ == "__main__":
    main()