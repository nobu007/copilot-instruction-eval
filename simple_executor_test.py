#!/usr/bin/env python3
"""
Simplified Executor Test - 基本機能のみテスト実行
"""
import json
import os
import sqlite3
import time
import uuid
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database(db_path):
    """データベーステーブル作成"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instruction_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            instruction_text TEXT NOT NULL,
            mode TEXT NOT NULL,
            model TEXT NOT NULL,
            response TEXT NOT NULL,
            execution_time REAL NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            error_message TEXT,
            metrics TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info(f"📊 Database initialized: {db_path}")

def send_prompt_request(prompt):
    """プロンプトリクエスト送信"""
    request_id = str(uuid.uuid4())
    request = {
        "request_id": request_id,
        "command": "submitPrompt",
        "params": {"prompt": prompt}
    }
    
    # リクエストファイル作成
    request_path = f"/tmp/copilot-evaluation/requests/{request_id}.json"
    response_path = f"/tmp/copilot-evaluation/responses/{request_id}.json"
    
    logger.info(f"Executing instruction: {prompt}")
    start_time = time.time()
    
    with open(request_path, 'w') as f:
        json.dump(request, f, indent=2)
    
    # 応答待機 (最大60秒)
    for i in range(60):
        if os.path.exists(response_path):
            with open(response_path, 'r') as f:
                response = json.load(f)
            
            execution_time = time.time() - start_time
            
            # クリーンアップ
            try:
                os.remove(response_path)
            except:
                pass
            
            return request_id, response, execution_time
        
        time.sleep(1)
    
    execution_time = time.time() - start_time
    logger.error(f"Timeout waiting for response to {request_id}")
    return request_id, None, execution_time

def save_result(db_path, instruction_id, request_id, instruction_text, response, execution_time):
    """結果をデータベースに保存"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if response and response.get('final_status') == 'success':
        status = 'success'
        response_text = json.dumps(response.get('attempts', [{}])[0].get('data', {}))
        error_message = None
    else:
        status = 'failed'
        response_text = json.dumps(response) if response else 'timeout'
        error_message = response.get('attempts', [{}])[0].get('error') if response else 'timeout'
    
    cursor.execute('''
        INSERT INTO execution_results 
        (instruction_id, request_id, instruction_text, mode, model, response, 
         execution_time, status, timestamp, error_message, metrics)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        instruction_id,
        request_id,
        instruction_text,
        'chat',
        'default',
        response_text,
        execution_time,
        status,
        datetime.now().isoformat(),
        error_message,
        None
    ))
    
    conn.commit()
    conn.close()
    logger.info(f"✅ Result saved: {status}")

def main():
    """メイン実行関数"""
    db_path = 'simple_continuous_execution.db'
    instructions_file = 'final_test_instructions.json'
    
    logger.info("🚀 Simple Executor Test Starting...")
    
    # データベース初期化
    setup_database(db_path)
    
    # 指示ファイル読み込み
    with open(instructions_file, 'r') as f:
        data = json.load(f)
    instructions = data['instructions']
    
    logger.info(f"📝 Loaded {len(instructions)} instructions")
    
    # 各指示を実行
    for instruction in instructions:
        instruction_id = instruction['id']
        instruction_text = instruction['description']
        
        request_id, response, execution_time = send_prompt_request(instruction_text)
        save_result(db_path, instruction_id, request_id, instruction_text, response, execution_time)
    
    logger.info("🎉 All instructions processed successfully!")

if __name__ == "__main__":
    main()