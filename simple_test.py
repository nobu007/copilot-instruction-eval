#!/usr/bin/env python3
"""
Simple Test Script for Enhanced File-based Evaluation System

シンプルなテストスクリプト - 基本動作確認用
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime


def test_basic_file_system():
    """基本的なファイルシステムテスト"""
    print("🧪 Testing basic file system operations...")
    
    base_dir = Path("/tmp/copilot-evaluation")
    requests_dir = base_dir / "requests"
    responses_dir = base_dir / "responses"
    
    # ディレクトリ作成
    for dir_path in [requests_dir, responses_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Directory ready: {dir_path}")
    
    # テストリクエスト作成
    request_id = "req_test001"
    test_request = {
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
        "test_id": "simple_test",
        "prompt": "Write a simple Python hello world function",
        "model": "copilot/gpt-4",
        "mode": "agent",
        "timeout": 60,
        "expected_elements": ["def", "hello", "print"],
        "category": "basic_test",
        "retry_count": 0,
        "max_retries": 3,
        "priority": 0,
        "checksum": "test_checksum"
    }
    
    # リクエストファイル作成
    request_file = requests_dir / f"{request_id}.json"
    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(test_request, f, indent=2, ensure_ascii=False)
    
    print(f"📤 Test request created: {request_file}")
    print(f"📝 Request ID: {request_id}")
    print(f"📝 Prompt: {test_request['prompt']}")
    
    # レスポンス待機
    print(f"⏳ Waiting for response (max 60 seconds)...")
    
    response_file = responses_dir / f"resp_test001.json"
    start_time = time.time()
    timeout = 60
    
    while time.time() - start_time < timeout:
        if response_file.exists():
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)
                
                print(f"✅ Response received!")
                print(f"📊 Success: {response_data.get('success', 'unknown')}")
                print(f"⏱️ Execution time: {response_data.get('execution_time', 0):.2f}s")
                print(f"📝 Response length: {response_data.get('response_length', 0)} chars")
                
                if response_data.get('error_message'):
                    print(f"❌ Error: {response_data['error_message']}")
                else:
                    response_preview = response_data.get('response', '')[:200]
                    print(f"📄 Response preview: {response_preview}...")
                
                return True
                
            except Exception as e:
                print(f"❌ Error reading response: {e}")
                return False
        
        time.sleep(1)
        print(".", end="", flush=True)
    
    print(f"\n⏰ Timeout - no response received")
    return False


def check_directories():
    """ディレクトリ状況確認"""
    print("\n📁 Directory Status:")
    
    base_dir = Path("/tmp/copilot-evaluation")
    subdirs = ["requests", "responses", "processing", "failed", "config", "results"]
    
    for subdir in subdirs:
        dir_path = base_dir / subdir
        if dir_path.exists():
            file_count = len(list(dir_path.glob("*.json")))
            print(f"  ✅ {subdir}/: {file_count} files")
        else:
            print(f"  ❌ {subdir}/: not found")


def check_extension_logs():
    """拡張機能ログ確認"""
    print("\n📋 Checking VSCode extension status...")
    
    # VSCode開発者コンソールの出力を確認する方法を提案
    print("💡 To check extension logs:")
    print("   1. Open VSCode")
    print("   2. Press F1 and run 'Developer: Toggle Developer Tools'")
    print("   3. Check Console tab for extension logs")
    print("   4. Look for 'Enhanced File Request Handler started' message")


def main():
    """メイン実行"""
    print("🚀 Simple File-based Evaluation System Test")
    print("=" * 50)
    
    # ディレクトリ状況確認
    check_directories()
    
    # 拡張機能ログ確認方法の説明
    check_extension_logs()
    
    # 基本テスト実行
    print(f"\n🧪 Running basic file system test...")
    success = test_basic_file_system()
    
    if success:
        print(f"\n🎉 Test completed successfully!")
        print(f"✅ File-based evaluation system is working!")
    else:
        print(f"\n❌ Test failed or timed out")
        print(f"🔍 Check VSCode extension status and logs")
    
    # 最終ディレクトリ状況
    check_directories()
    
    print(f"\n📊 Test Summary:")
    print(f"   - Request file created: ✅")
    print(f"   - VSCode extension processing: {'✅' if success else '❌'}")
    print(f"   - Response received: {'✅' if success else '❌'}")


if __name__ == "__main__":
    main()
