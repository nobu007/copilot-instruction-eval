#!/usr/bin/env python3
"""
Comprehensive Validation Script - VSCode Copilot Automation System
システム全体の包括的検証・テスト実行スクリプト

Usage:
    python3 scripts/comprehensive_validation.py [--quick] [--report-only]
"""
import json
import os
import time
import uuid
import logging
import argparse
import sqlite3
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveValidator:
    def __init__(self):
        self.base_dir = "/tmp/copilot-evaluation"
        self.requests_dir = f"{self.base_dir}/requests"
        self.responses_dir = f"{self.base_dir}/responses"
        self.db_path = "validation_results.db"
        
        # テストケースカテゴリ
        self.test_categories = {
            "connectivity": "Basic connectivity and system responsiveness",
            "functionality": "Core Copilot functionality",
            "error_handling": "Error conditions and edge cases",
            "performance": "Response time and throughput",
            "reliability": "Consistency and failure recovery"
        }
        
        # 包括的テストケース
        self.test_cases = [
            # 接続性テスト
            {
                "id": "conn_ping_basic",
                "category": "connectivity",
                "command": "ping",
                "params": {},
                "expected_status": "success",
                "timeout": 10,
                "description": "Basic ping connectivity test"
            },
            {
                "id": "conn_current_state",
                "category": "connectivity", 
                "command": "getCurrentState",
                "params": {},
                "expected_status": "success",
                "timeout": 10,
                "description": "Current state retrieval test"
            },
            
            # 機能テスト
            {
                "id": "func_simple_prompt",
                "category": "functionality",
                "command": "submitPrompt",
                "params": {"prompt": "hello"},
                "expected_status": "success",
                "timeout": 30,
                "description": "Simple prompt submission"
            },
            {
                "id": "func_code_generation",
                "category": "functionality",
                "command": "submitPrompt",
                "params": {"prompt": "write a function that adds two numbers"},
                "expected_status": "success",
                "timeout": 45,
                "description": "Code generation request"
            },
            {
                "id": "func_explanation",
                "category": "functionality",
                "command": "submitPrompt",
                "params": {"prompt": "explain what is a variable in programming"},
                "expected_status": "success",
                "timeout": 45,
                "description": "Explanation request"
            },
            
            # エラーハンドリングテスト
            {
                "id": "error_unknown_command",
                "category": "error_handling",
                "command": "unknownCommand",
                "params": {},
                "expected_status": "failed",
                "timeout": 10,
                "description": "Unknown command handling"
            },
            {
                "id": "error_empty_prompt",
                "category": "error_handling", 
                "command": "submitPrompt",
                "params": {"prompt": ""},
                "expected_status": "failed",
                "timeout": 20,
                "description": "Empty prompt handling"
            },
            
            # パフォーマンステスト
            {
                "id": "perf_quick_response",
                "category": "performance",
                "command": "ping",
                "params": {},
                "expected_status": "success",
                "timeout": 5,
                "max_response_time": 3.0,
                "description": "Quick response performance test"
            },
            
            # 信頼性テスト
            {
                "id": "reliability_repeated_ping",
                "category": "reliability",
                "command": "ping",
                "params": {},
                "expected_status": "success",
                "timeout": 10,
                "repeat_count": 5,
                "description": "Repeated ping reliability test"
            }
        ]
        
        self.setup_validation_database()
        self.results = []
    
    def setup_validation_database(self):
        """検証用データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                category TEXT NOT NULL,
                command TEXT NOT NULL,
                expected_status TEXT NOT NULL,
                actual_status TEXT NOT NULL,
                execution_time REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                response_data TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"📊 Validation database initialized: {self.db_path}")
    
    def send_test_request(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """テストリクエスト送信"""
        request_id = str(uuid.uuid4())
        request = {
            "request_id": request_id,
            "command": test_case["command"],
            "params": test_case.get("params", {})
        }
        
        request_path = f"{self.requests_dir}/{request_id}.json"
        response_path = f"{self.responses_dir}/{request_id}.json"
        
        logger.info(f"🧪 Testing {test_case['id']}: {test_case['description']}")
        
        start_time = time.time()
        
        # リクエスト送信
        with open(request_path, 'w') as f:
            json.dump(request, f, indent=2)
        
        # 応答待機
        timeout = test_case.get("timeout", 30)
        for i in range(timeout):
            if os.path.exists(response_path):
                with open(response_path, 'r') as f:
                    response = json.load(f)
                
                execution_time = time.time() - start_time
                
                # クリーンアップ
                try:
                    os.remove(response_path)
                except:
                    pass
                
                return {
                    "request_id": request_id,
                    "response": response,
                    "execution_time": execution_time,
                    "timeout": False
                }
            
            time.sleep(1)
        
        # タイムアウト
        execution_time = time.time() - start_time
        return {
            "request_id": request_id,
            "response": None,
            "execution_time": execution_time,
            "timeout": True
        }
    
    def evaluate_test_result(self, test_case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """テスト結果評価"""
        success = True
        error_message = None
        
        if result["timeout"]:
            success = False
            error_message = f"Request timed out after {test_case.get('timeout', 30)}s"
            actual_status = "timeout"
        else:
            response = result["response"]
            actual_status = response.get("final_status", "unknown") if response else "error"
            
            # ステータス期待値チェック
            expected_status = test_case["expected_status"]
            if actual_status != expected_status:
                success = False
                error_message = f"Expected status '{expected_status}' but got '{actual_status}'"
            
            # パフォーマンスチェック
            max_response_time = test_case.get("max_response_time")
            if max_response_time and result["execution_time"] > max_response_time:
                success = False
                error_message = f"Response time {result['execution_time']:.1f}s exceeded limit {max_response_time}s"
        
        return {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "command": test_case["command"],
            "expected_status": test_case["expected_status"],
            "actual_status": actual_status,
            "execution_time": result["execution_time"],
            "success": success,
            "error_message": error_message,
            "response_data": json.dumps(result.get("response")) if result.get("response") else None,
            "description": test_case["description"]
        }
    
    def save_test_result(self, evaluation: Dict[str, Any]):
        """テスト結果保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO validation_results 
            (test_id, category, command, expected_status, actual_status, 
             execution_time, success, error_message, response_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            evaluation["test_id"],
            evaluation["category"],
            evaluation["command"],
            evaluation["expected_status"],
            evaluation["actual_status"],
            evaluation["execution_time"],
            evaluation["success"],
            evaluation["error_message"],
            evaluation["response_data"],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """単一テスト実行"""
        repeat_count = test_case.get("repeat_count", 1)
        
        if repeat_count == 1:
            # 単一実行
            result = self.send_test_request(test_case)
            evaluation = self.evaluate_test_result(test_case, result)
            
            # 結果表示
            status_emoji = "✅" if evaluation["success"] else "❌"
            logger.info(f"   {status_emoji} {evaluation['actual_status']} ({evaluation['execution_time']:.1f}s)")
            if evaluation["error_message"]:
                logger.warning(f"      {evaluation['error_message']}")
            
            return evaluation
        else:
            # 繰り返し実行
            logger.info(f"   🔄 Running {repeat_count} iterations...")
            
            all_results = []
            success_count = 0
            total_time = 0
            
            for i in range(repeat_count):
                result = self.send_test_request(test_case)
                evaluation = self.evaluate_test_result(test_case, result)
                
                if evaluation["success"]:
                    success_count += 1
                total_time += evaluation["execution_time"]
                
                all_results.append(evaluation)
                
                # 簡潔な進捗表示
                status = "✅" if evaluation["success"] else "❌"
                logger.info(f"      {i+1}/{repeat_count}: {status} ({evaluation['execution_time']:.1f}s)")
            
            # 集約結果作成
            avg_time = total_time / repeat_count
            success_rate = success_count / repeat_count
            overall_success = success_rate >= 0.8  # 80%以上で成功とする
            
            aggregate_evaluation = {
                "test_id": test_case["id"],
                "category": test_case["category"],
                "command": test_case["command"],
                "expected_status": test_case["expected_status"],
                "actual_status": "success" if overall_success else "failed",
                "execution_time": avg_time,
                "success": overall_success,
                "error_message": f"Success rate: {success_rate:.0%}" if not overall_success else None,
                "response_data": f"Iterations: {repeat_count}, Success: {success_count}/{repeat_count}",
                "description": test_case["description"]
            }
            
            logger.info(f"   📊 Overall: {success_count}/{repeat_count} success ({success_rate:.0%}), Avg: {avg_time:.1f}s")
            
            return aggregate_evaluation
    
    def run_comprehensive_validation(self, quick_mode: bool = False):
        """包括的検証実行"""
        logger.info("🧪 === COMPREHENSIVE VALIDATION START ===")
        start_time = datetime.now()
        
        test_cases = self.test_cases
        if quick_mode:
            # クイックモードでは基本テストのみ
            test_cases = [tc for tc in test_cases if tc["category"] in ["connectivity", "functionality"]]
            logger.info("⚡ Quick mode: Running essential tests only")
        
        # カテゴリごとの進捗管理
        category_stats = {cat: {"total": 0, "passed": 0} for cat in self.test_categories.keys()}
        
        for test_case in test_cases:
            category = test_case["category"]
            category_stats[category]["total"] += 1
            
            # テスト実行
            evaluation = self.run_single_test(test_case)
            
            if evaluation["success"]:
                category_stats[category]["passed"] += 1
            
            # 結果保存
            self.save_test_result(evaluation)
            self.results.append(evaluation)
        
        # 結果サマリー
        self.print_validation_summary(category_stats, start_time)
    
    def print_validation_summary(self, category_stats: Dict, start_time: datetime):
        """検証結果サマリー表示"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\\n" + "="*60)
        print("🧪 COMPREHENSIVE VALIDATION SUMMARY")
        print("="*60)
        print(f"⏱️  Total Duration: {duration:.1f}s")
        print(f"📋 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print("\\n📈 Results by Category:")
        print("-"*40)
        
        for category, description in self.test_categories.items():
            stats = category_stats.get(category, {"total": 0, "passed": 0})
            if stats["total"] > 0:
                cat_rate = (stats["passed"] / stats["total"] * 100)
                status_emoji = "✅" if cat_rate == 100 else "⚠️" if cat_rate >= 80 else "❌"
                print(f"{status_emoji} {category.upper()}: {stats['passed']}/{stats['total']} ({cat_rate:.0f}%)")
                print(f"   {description}")
        
        # 失敗したテストの詳細
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            print("\\n❌ Failed Tests:")
            print("-"*40)
            for test in failed_tests:
                print(f"• {test['test_id']}: {test['error_message']}")
        
        # 総合判定
        if success_rate >= 95:
            overall_status = "🟢 EXCELLENT"
        elif success_rate >= 85:
            overall_status = "🟡 GOOD"  
        elif success_rate >= 70:
            overall_status = "🟠 ACCEPTABLE"
        else:
            overall_status = "🔴 CRITICAL"
        
        print(f"\\n🏆 OVERALL SYSTEM STATUS: {overall_status} ({success_rate:.1f}%)")
        print(f"💾 Detailed results saved to: {self.db_path}")
        print("="*60)
        
        return success_rate >= 70
    
    def generate_detailed_report(self):
        """詳細レポート生成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # データベースから結果取得
        cursor.execute('''
            SELECT test_id, category, command, expected_status, actual_status,
                   execution_time, success, error_message, timestamp
            FROM validation_results 
            ORDER BY timestamp DESC
        ''')
        
        results = cursor.fetchall()
        
        # レポート生成
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Comprehensive Validation Report\\n\\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\\n")
            f.write(f"**Total Tests:** {len(results)}\\n\\n")
            
            # カテゴリ別セクション
            for category in self.test_categories.keys():
                category_results = [r for r in results if r[1] == category]
                if not category_results:
                    continue
                    
                f.write(f"## {category.upper()}\\n\\n")
                f.write(f"**Description:** {self.test_categories[category]}\\n\\n")
                
                f.write("| Test ID | Command | Expected | Actual | Time | Status |\\n")
                f.write("|---------|---------|----------|--------|------|--------|\\n")
                
                for result in category_results:
                    status_icon = "✅" if result[6] else "❌"  # success field
                    f.write(f"| {result[0]} | {result[2]} | {result[3]} | {result[4]} | {result[5]:.1f}s | {status_icon} |\\n")
                
                f.write("\\n")
        
        conn.close()
        logger.info(f"📄 Detailed report generated: {report_file}")
        return report_file


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Comprehensive System Validation')
    parser.add_argument('--quick', action='store_true', help='Run only essential tests')
    parser.add_argument('--report-only', action='store_true', help='Generate report from existing results')
    
    args = parser.parse_args()
    
    validator = ComprehensiveValidator()
    
    if args.report_only:
        validator.generate_detailed_report()
    else:
        success = validator.run_comprehensive_validation(args.quick)
        validator.generate_detailed_report()
        
        # 終了コード
        exit_code = 0 if success else 1
        exit(exit_code)


if __name__ == "__main__":
    main()