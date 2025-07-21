#!/usr/bin/env python3
"""
Demo Script - VSCode Copilot Automation System
システムの機能を実演する対話的デモスクリプト

Usage:
    python3 scripts/demo.py [--mode interactive|automatic]
"""
import json
import os
import time
import uuid
import logging
import argparse
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CopilotDemo:
    def __init__(self):
        self.base_dir = "/tmp/copilot-evaluation"
        self.requests_dir = f"{self.base_dir}/requests"
        self.responses_dir = f"{self.base_dir}/responses"
        self.db_path = "demo_execution_results.db"
        
        # デモ用指示セット
        self.demo_instructions = [
            {
                "id": "demo_greeting",
                "description": "Say hello in a friendly way",
                "category": "Basic"
            },
            {
                "id": "demo_code_simple",
                "description": "Write a simple Python function to calculate factorial",
                "category": "Code Generation"
            },
            {
                "id": "demo_explain",
                "description": "Explain what is machine learning in simple terms",
                "category": "Explanation"
            },
            {
                "id": "demo_security",
                "description": "List 3 common web security best practices",
                "category": "Security"
            },
            {
                "id": "demo_review",
                "description": "Review this code: def divide(a, b): return a / b",
                "category": "Code Review"
            }
        ]
        
        self.setup_demo_database()
    
    def setup_demo_database(self):
        """デモ用データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS demo_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                instruction_text TEXT NOT NULL,
                category TEXT NOT NULL,
                response_content TEXT,
                execution_time REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    
    def print_banner(self):
        """デモバナー表示"""
        print("\\n" + "="*60)
        print("🤖 VSCode Copilot Automation System - LIVE DEMO")
        print("="*60)
        print("This demo will showcase the key features of our")
        print("automated GitHub Copilot integration system.")
        print("="*60 + "\\n")
    
    def send_demo_request(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """デモリクエスト送信"""
        request_id = str(uuid.uuid4())
        request = {
            "request_id": request_id,
            "command": "submitPrompt",
            "params": {
                "prompt": instruction["description"]
            }
        }
        
        request_path = f"{self.requests_dir}/{request_id}.json"
        response_path = f"{self.responses_dir}/{request_id}.json"
        
        print(f"📤 Sending request: {instruction['id']}")
        print(f"   Category: {instruction['category']}")
        print(f"   Prompt: {instruction['description']}")
        print(f"   Request ID: {request_id}")
        
        start_time = time.time()
        
        # リクエストファイル作成
        with open(request_path, 'w') as f:
            json.dump(request, f, indent=2)
        
        # 応答待機（プログレス表示付き）
        print("   ⏳ Waiting for Copilot response", end="", flush=True)
        
        for i in range(60):  # 最大60秒待機
            if os.path.exists(response_path):
                # 応答受信
                with open(response_path, 'r') as f:
                    response = json.load(f)
                
                execution_time = time.time() - start_time
                
                # クリーンアップ
                try:
                    os.remove(response_path)
                except:
                    pass
                
                print(f" ✅ ({execution_time:.1f}s)")
                return {
                    "request_id": request_id,
                    "response": response,
                    "execution_time": execution_time
                }
            
            # プログレス表示
            if i % 3 == 0:
                print(".", end="", flush=True)
            time.sleep(1)
        
        # タイムアウト
        execution_time = time.time() - start_time
        print(f" ❌ TIMEOUT ({execution_time:.1f}s)")
        return {
            "request_id": request_id,
            "response": None,
            "execution_time": execution_time
        }
    
    def display_response(self, instruction: Dict[str, Any], result: Dict[str, Any]):
        """応答内容表示"""
        print("\\n" + "-"*50)
        print(f"📋 RESULT for {instruction['id']}")
        print("-"*50)
        
        response = result.get("response")
        if response and response.get("final_status") == "success":
            # 成功時の応答表示
            attempts = response.get("attempts", [])
            if attempts:
                data = attempts[0].get("data", {})
                content = data.get("content", "No content")
                
                print(f"✅ Status: SUCCESS")
                print(f"⏱️  Time: {result['execution_time']:.1f}s")
                print(f"🤖 Copilot Response:")
                print("-" * 30)
                
                # 内容を適切に整形して表示
                if len(content) > 200:
                    print(content[:200] + "...")
                    print(f"\\n[Response truncated - Full length: {len(content)} chars]")
                else:
                    print(content)
        else:
            # エラー時の表示
            print(f"❌ Status: FAILED")
            print(f"⏱️  Time: {result['execution_time']:.1f}s")
            if response:
                attempts = response.get("attempts", [])
                if attempts:
                    error = attempts[0].get("error", "Unknown error")
                    print(f"🚨 Error: {error}")
            else:
                print("🚨 Error: Request timeout")
        
        print("-"*50 + "\\n")
    
    def save_demo_result(self, instruction: Dict[str, Any], result: Dict[str, Any]):
        """デモ結果をデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        response = result.get("response")
        if response and response.get("final_status") == "success":
            status = "success"
            attempts = response.get("attempts", [])
            content = attempts[0].get("data", {}).get("content", "") if attempts else ""
        else:
            status = "failed"
            content = str(response) if response else "timeout"
        
        cursor.execute('''
            INSERT INTO demo_results 
            (instruction_id, request_id, instruction_text, category, 
             response_content, execution_time, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            instruction["id"],
            result["request_id"],
            instruction["description"],
            instruction["category"],
            content,
            result["execution_time"],
            status,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def run_interactive_demo(self):
        """対話型デモ実行"""
        self.print_banner()
        
        print("🎯 INTERACTIVE MODE")
        print("Press Enter to execute each demo step, or 'q' to quit.\\n")
        
        for i, instruction in enumerate(self.demo_instructions, 1):
            print(f"\\n📍 Demo Step {i}/{len(self.demo_instructions)}")
            print(f"   {instruction['category']}: {instruction['description']}")
            
            user_input = input("\\n   Press [Enter] to continue, 's' to skip, 'q' to quit: ").strip().lower()
            
            if user_input == 'q':
                print("\\n👋 Demo terminated by user.")
                break
            elif user_input == 's':
                print("   ⏭️ Skipped")
                continue
            
            # リクエスト実行
            result = self.send_demo_request(instruction)
            self.display_response(instruction, result)
            self.save_demo_result(instruction, result)
        
        self.show_demo_summary()
    
    def run_automatic_demo(self):
        """自動デモ実行"""
        self.print_banner()
        
        print("🚀 AUTOMATIC MODE")
        print("All demo steps will run automatically.\\n")
        
        for i, instruction in enumerate(self.demo_instructions, 1):
            print(f"\\n📍 Demo Step {i}/{len(self.demo_instructions)}")
            
            # リクエスト実行
            result = self.send_demo_request(instruction)
            self.display_response(instruction, result)
            self.save_demo_result(instruction, result)
            
            # 次のステップまでの間隔
            if i < len(self.demo_instructions):
                print("   ⏸️ Pausing 2s before next step...")
                time.sleep(2)
        
        self.show_demo_summary()
    
    def show_demo_summary(self):
        """デモサマリー表示"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 結果集計
        cursor.execute("SELECT status, COUNT(*), AVG(execution_time) FROM demo_results GROUP BY status")
        results = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*), AVG(execution_time) FROM demo_results")
        total_count, avg_time = cursor.fetchone()
        
        conn.close()
        
        print("\\n" + "="*60)
        print("📊 DEMO SUMMARY REPORT")
        print("="*60)
        
        print(f"📋 Total Requests: {total_count}")
        print(f"⏱️  Average Response Time: {avg_time:.1f}s")
        
        for status, count, avg_exec_time in results:
            percentage = (count / total_count * 100) if total_count > 0 else 0
            emoji = "✅" if status == "success" else "❌"
            print(f"{emoji} {status.title()}: {count} ({percentage:.0f}%) - Avg: {avg_exec_time:.1f}s")
        
        print("\\n💾 Demo results saved to:", self.db_path)
        print("="*60)
        print("\\n🎉 Demo completed! Thank you for watching.")
        print("   The system is ready for production use.")
        print("="*60)


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='VSCode Copilot Automation Demo')
    parser.add_argument('--mode', choices=['interactive', 'automatic'], 
                       default='interactive', help='Demo mode')
    
    args = parser.parse_args()
    
    demo = CopilotDemo()
    
    if args.mode == 'interactive':
        demo.run_interactive_demo()
    else:
        demo.run_automatic_demo()


if __name__ == "__main__":
    main()