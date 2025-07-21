#!/usr/bin/env python3
"""
System Health Check - VSCode Copilot Automation System
システム全体の動作状況を迅速に確認する診断スクリプト

Usage:
    python3 scripts/health_check.py
"""
import json
import os
import time
import uuid
import logging
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.base_dir = "/tmp/copilot-evaluation"
        self.requests_dir = f"{self.base_dir}/requests"
        self.responses_dir = f"{self.base_dir}/responses"
        self.failed_dir = f"{self.base_dir}/failed"
        self.db_path = "simple_continuous_execution.db"
        self.extension_path = "vscode-copilot-automation-extension"
        
        self.checks_passed = 0
        self.checks_total = 0
        self.issues = []
    
    def check_mark(self, passed):
        """チェック結果のマーク"""
        self.checks_total += 1
        if passed:
            self.checks_passed += 1
            return "✅"
        else:
            return "❌"
    
    def add_issue(self, issue):
        """問題を記録"""
        self.issues.append(issue)
        logger.warning(f"ISSUE: {issue}")
    
    def check_directories(self):
        """IPCディレクトリ構造確認"""
        logger.info("=== Directory Structure Check ===")
        
        required_dirs = [self.base_dir, self.requests_dir, self.responses_dir, self.failed_dir]
        all_exist = True
        
        for dir_path in required_dirs:
            exists = os.path.exists(dir_path) and os.path.isdir(dir_path)
            logger.info(f"{self.check_mark(exists)} {dir_path}")
            if not exists:
                all_exist = False
                self.add_issue(f"Missing directory: {dir_path}")
        
        return all_exist
    
    def check_vscode_extension(self):
        """VSCode拡張の存在確認"""
        logger.info("=== VSCode Extension Check ===")
        
        # 拡張ディレクトリ
        ext_exists = os.path.exists(self.extension_path) and os.path.isdir(self.extension_path)
        logger.info(f"{self.check_mark(ext_exists)} Extension directory: {self.extension_path}")
        
        # VSIX パッケージ
        vsix_path = f"{self.extension_path}/copilot-automation-extension-0.0.1.vsix"
        vsix_exists = os.path.exists(vsix_path)
        logger.info(f"{self.check_mark(vsix_exists)} VSIX package: {vsix_path}")
        
        # コンパイル済みJS
        js_exists = os.path.exists(f"{self.extension_path}/out/extension.js")
        logger.info(f"{self.check_mark(js_exists)} Compiled extension: out/extension.js")
        
        if not ext_exists:
            self.add_issue("VSCode extension directory not found")
        if not vsix_exists:
            self.add_issue("VSIX package not found")
        if not js_exists:
            self.add_issue("Extension not compiled")
        
        return ext_exists and vsix_exists and js_exists
    
    def check_vscode_process(self):
        """VSCode プロセス確認"""
        logger.info("=== VSCode Process Check ===")
        
        try:
            # extensionHost プロセス確認
            result = subprocess.run(
                ["pgrep", "-f", "extensionHost"], 
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\\n')
                logger.info(f"{self.check_mark(True)} VSCode extension host running (PIDs: {', '.join(pids)})")
                return True
            else:
                logger.info(f"{self.check_mark(False)} VSCode extension host not running")
                self.add_issue("VSCode extension host process not found")
                return False
                
        except Exception as e:
            logger.info(f"{self.check_mark(False)} Process check failed: {e}")
            self.add_issue(f"Process check error: {e}")
            return False
    
    def check_copilot_extensions(self):
        """GitHub Copilot拡張確認"""
        logger.info("=== GitHub Copilot Extensions Check ===")
        
        try:
            # インストール済み拡張一覧取得
            result = subprocess.run(
                ["code", "--list-extensions"], 
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                extensions = result.stdout.strip().split('\\n')
                
                # GitHub Copilot 拡張確認
                copilot_found = any("github.copilot" in ext for ext in extensions)
                copilot_chat_found = any("github.copilot-chat" in ext for ext in extensions)
                automation_found = any("copilot-automation-extension" in ext for ext in extensions)
                
                logger.info(f"{self.check_mark(copilot_found)} GitHub Copilot extension")
                logger.info(f"{self.check_mark(copilot_chat_found)} GitHub Copilot Chat extension")
                logger.info(f"{self.check_mark(automation_found)} Copilot Automation extension")
                
                if not copilot_found:
                    self.add_issue("GitHub Copilot extension not installed")
                if not copilot_chat_found:
                    self.add_issue("GitHub Copilot Chat extension not installed")
                if not automation_found:
                    self.add_issue("Copilot Automation extension not installed")
                
                return copilot_found and automation_found
            else:
                logger.info(f"{self.check_mark(False)} Cannot list extensions")
                self.add_issue("Cannot list VSCode extensions")
                return False
                
        except Exception as e:
            logger.info(f"{self.check_mark(False)} Extension check failed: {e}")
            self.add_issue(f"Extension check error: {e}")
            return False
    
    def check_ping_connectivity(self):
        """Ping接続性テスト"""
        logger.info("=== Ping Connectivity Test ===")
        
        request_id = str(uuid.uuid4())
        request = {
            "request_id": request_id,
            "command": "ping",
            "params": {}
        }
        
        request_path = f"{self.requests_dir}/{request_id}.json"
        response_path = f"{self.responses_dir}/{request_id}.json"
        
        try:
            # リクエスト送信
            with open(request_path, 'w') as f:
                json.dump(request, f, indent=2)
            
            # 応答待機 (10秒)
            for i in range(10):
                if os.path.exists(response_path):
                    with open(response_path, 'r') as f:
                        response = json.load(f)
                    
                    # クリーンアップ
                    try:
                        os.remove(response_path)
                    except:
                        pass
                    
                    success = response.get('final_status') == 'success'
                    logger.info(f"{self.check_mark(success)} Ping response received in {i+1}s")
                    
                    if not success:
                        self.add_issue(f"Ping failed: {response}")
                    
                    return success
                
                time.sleep(1)
            
            # タイムアウト
            logger.info(f"{self.check_mark(False)} Ping timeout (10s)")
            self.add_issue("Ping request timed out")
            return False
            
        except Exception as e:
            logger.info(f"{self.check_mark(False)} Ping test error: {e}")
            self.add_issue(f"Ping test error: {e}")
            return False
    
    def check_database_structure(self):
        """データベース構造確認"""
        logger.info("=== Database Structure Check ===")
        
        try:
            if not os.path.exists(self.db_path):
                logger.info(f"{self.check_mark(False)} Database file not found: {self.db_path}")
                # データベースが無い場合は警告だけ
                return True
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブル存在確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_results'")
            table_exists = cursor.fetchone() is not None
            logger.info(f"{self.check_mark(table_exists)} execution_results table exists")
            
            if table_exists:
                # カラム構造確認
                cursor.execute("PRAGMA table_info(execution_results)")
                columns = {row[1] for row in cursor.fetchall()}
                
                required_columns = {
                    'id', 'instruction_id', 'request_id', 'instruction_text', 
                    'mode', 'model', 'response', 'execution_time', 'status', 
                    'timestamp', 'error_message', 'metrics'
                }
                
                missing_columns = required_columns - columns
                if missing_columns:
                    logger.info(f"{self.check_mark(False)} Missing columns: {missing_columns}")
                    self.add_issue(f"Database missing columns: {missing_columns}")
                    conn.close()
                    return False
                else:
                    logger.info(f"{self.check_mark(True)} All required columns present")
            
            conn.close()
            return table_exists
            
        except Exception as e:
            logger.info(f"{self.check_mark(False)} Database check error: {e}")
            self.add_issue(f"Database error: {e}")
            return False
    
    def check_instructions_file(self):
        """指示ファイル確認"""
        logger.info("=== Instructions Files Check ===")
        
        files = ["instructions.json", "final_test_instructions.json"]
        found_files = 0
        
        for filename in files:
            exists = os.path.exists(filename)
            logger.info(f"{self.check_mark(exists)} {filename}")
            
            if exists:
                found_files += 1
                try:
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        instructions = data.get('instructions', [])
                        logger.info(f"    📋 {len(instructions)} instructions loaded")
                except Exception as e:
                    self.add_issue(f"Invalid JSON in {filename}: {e}")
            
        if found_files == 0:
            self.add_issue("No instruction files found")
            
        return found_files > 0
    
    def run_full_health_check(self):
        """完全ヘルスチェック実行"""
        logger.info("🏥 === SYSTEM HEALTH CHECK START ===")
        start_time = datetime.now()
        
        # 各チェック実行
        self.check_directories()
        self.check_vscode_extension()
        self.check_vscode_process()
        self.check_copilot_extensions()
        self.check_database_structure()
        self.check_instructions_file()
        self.check_ping_connectivity()
        
        # 結果サマリー
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\\n" + "="*50)
        logger.info("🏥 HEALTH CHECK SUMMARY")
        logger.info("="*50)
        logger.info(f"⏱️  Duration: {duration:.1f}s")
        logger.info(f"✅ Checks Passed: {self.checks_passed}/{self.checks_total}")
        
        if self.issues:
            logger.info(f"⚠️  Issues Found ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                logger.info(f"   {i}. {issue}")
        
        # 総合判定
        health_percentage = (self.checks_passed / self.checks_total * 100) if self.checks_total > 0 else 0
        
        if health_percentage >= 90:
            status = "🟢 HEALTHY"
        elif health_percentage >= 70:
            status = "🟡 DEGRADED"
        else:
            status = "🔴 CRITICAL"
        
        logger.info(f"\\n🏥 SYSTEM STATUS: {status} ({health_percentage:.0f}%)")
        logger.info("="*50)
        
        return health_percentage >= 70


def main():
    """メイン実行関数"""
    checker = HealthChecker()
    healthy = checker.run_full_health_check()
    
    # 終了コード
    exit_code = 0 if healthy else 1
    exit(exit_code)


if __name__ == "__main__":
    main()