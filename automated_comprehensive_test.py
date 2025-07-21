#!/usr/bin/env python3
"""
自律的GitHub Copilot評価フレームワーク 総合テストスクリプト
事実ベース自己修正機能付き

Phase 1-5の完全自動実行:
- プランニング → 実装 → テスト → フィードバック → 完成
"""

import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/copilot-evaluation/logs/automated_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FactBasedSelfHealingTester:
    """事実ベース自己修正機能付きテスター"""
    
    def __init__(self):
        self.base_dir = Path('/tmp/copilot-evaluation')
        self.test_results = []
        self.error_count = 0
        self.success_count = 0
        
        # ディレクトリ構造確認
        self.ensure_directory_structure()
        
    def ensure_directory_structure(self):
        """ディレクトリ構造の確認・作成"""
        required_dirs = [
            'requests', 'responses', 'processing', 'failed',
            'logs', 'config', 'state'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Directory ensured: {dir_path}")
    
    def collect_system_facts(self) -> Dict[str, Any]:
        """【事実確認】システム状態の客観的証拠収集"""
        facts = {
            'timestamp': datetime.now().isoformat(),
            'directory_structure': {},
            'file_counts': {},
            'vscode_processes': [],
            'extension_status': {},
            'logs': {}
        }
        
        try:
            # ディレクトリ構造調査
            for subdir in ['requests', 'responses', 'processing', 'failed', 'logs', 'config', 'state']:
                dir_path = self.base_dir / subdir
                if dir_path.exists():
                    files = list(dir_path.glob('*'))
                    facts['directory_structure'][subdir] = {
                        'exists': True,
                        'file_count': len(files),
                        'files': [f.name for f in files[:10]]  # 最初の10ファイル
                    }
                else:
                    facts['directory_structure'][subdir] = {'exists': False}
            
            # VSCodeプロセス確認
            try:
                result = subprocess.run(['pgrep', '-f', 'code'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    facts['vscode_processes'] = result.stdout.strip().split('\n')
            except Exception as e:
                facts['vscode_processes'] = f"Error: {e}"
            
            # 拡張機能状態確認
            try:
                result = subprocess.run(['code', '--list-extensions'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    extensions = result.stdout.strip().split('\n')
                    facts['extension_status']['installed'] = extensions
                    facts['extension_status']['copilot_automation_installed'] = any(
                        'copilot-automation' in ext for ext in extensions
                    )
            except Exception as e:
                facts['extension_status']['error'] = str(e)
            
            # 最新ログ収集
            log_files = ['system.log', 'automated_test.log']
            for log_file in log_files:
                log_path = self.base_dir / 'logs' / log_file
                if log_path.exists():
                    try:
                        with open(log_path, 'r') as f:
                            lines = f.readlines()
                            facts['logs'][log_file] = lines[-50:]  # 最新50行
                    except Exception as e:
                        facts['logs'][log_file] = f"Error reading: {e}"
            
            logger.info("📊 System facts collected successfully")
            return facts
            
        except Exception as e:
            logger.error(f"❌ Failed to collect system facts: {e}")
            facts['collection_error'] = str(e)
            return facts
    
    def analyze_root_cause(self, error: Exception, facts: Dict[str, Any]) -> Dict[str, Any]:
        """【根本原因分析】事実に基づく原因特定"""
        analysis = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'probable_causes': [],
            'evidence': [],
            'recommended_actions': []
        }
        
        # エラータイプ別分析
        if isinstance(error, FileNotFoundError):
            analysis['probable_causes'].append("Required file or directory missing")
            analysis['evidence'].append(f"Missing path: {error.filename}")
            analysis['recommended_actions'].append("Create missing directories/files")
            
        elif isinstance(error, subprocess.TimeoutExpired):
            analysis['probable_causes'].append("Process timeout - system overload or hanging")
            analysis['evidence'].append(f"Command: {error.cmd}, Timeout: {error.timeout}s")
            analysis['recommended_actions'].append("Retry with longer timeout or kill hanging processes")
            
        elif isinstance(error, subprocess.CalledProcessError):
            analysis['probable_causes'].append("External command failed")
            analysis['evidence'].append(f"Command: {error.cmd}, Return code: {error.returncode}")
            if error.stderr:
                analysis['evidence'].append(f"Stderr: {error.stderr}")
            analysis['recommended_actions'].append("Check command syntax and system dependencies")
        
        # ファクトベース追加分析
        if not facts['directory_structure'].get('requests', {}).get('exists'):
            analysis['probable_causes'].append("Evaluation directory structure not initialized")
            analysis['recommended_actions'].append("Initialize directory structure")
        
        if not facts['extension_status'].get('copilot_automation_installed'):
            analysis['probable_causes'].append("VSCode Copilot Automation extension not installed")
            analysis['recommended_actions'].append("Install VSCode extension")
        
        logger.info(f"🔍 Root cause analysis completed: {len(analysis['probable_causes'])} causes identified")
        return analysis
    
    def self_heal(self, analysis: Dict[str, Any]) -> bool:
        """【自己修正】根本原因分析に基づく自動修復"""
        logger.info("🔧 Starting self-healing process...")
        
        healing_success = True
        
        for action in analysis['recommended_actions']:
            try:
                if action == "Create missing directories/files":
                    self.ensure_directory_structure()
                    logger.info("✅ Directory structure recreated")
                    
                elif action == "Initialize directory structure":
                    self.ensure_directory_structure()
                    logger.info("✅ Directory structure initialized")
                    
                elif action == "Install VSCode extension":
                    result = subprocess.run(
                        ['make', 'install'], 
                        cwd='/home/jinno/copilot-instruction-eval/vscode-copilot-automation-extension',
                        capture_output=True, text=True, timeout=60
                    )
                    if result.returncode == 0:
                        logger.info("✅ VSCode extension reinstalled")
                    else:
                        logger.error(f"❌ Extension installation failed: {result.stderr}")
                        healing_success = False
                        
                elif "timeout" in action.lower():
                    logger.info("⏰ Will retry with extended timeout")
                    
            except Exception as heal_error:
                logger.error(f"❌ Self-healing action failed: {action} - {heal_error}")
                healing_success = False
        
        return healing_success
    
    def create_test_request(self, test_id: str, prompt: str) -> str:
        """テストリクエスト作成"""
        request = {
            "request_id": f"test_{test_id}_{int(time.time())}",
            "test_id": test_id,
            "prompt": prompt,
            "model": "copilot/gpt-4",
            "mode": "agent",
            "max_retries": 3,
            "retry_count": 0,
            "request_timestamp": datetime.now().isoformat()
        }
        
        request_file = self.base_dir / 'requests' / f"{request['request_id']}.json"
        with open(request_file, 'w') as f:
            json.dump(request, f, indent=2)
        
        logger.info(f"📝 Test request created: {request['request_id']}")
        return request['request_id']
    
    def wait_for_response(self, request_id: str, timeout: int = 30) -> Optional[Dict]:
        """レスポンス待機"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # レスポンスファイル確認
            response_file = self.base_dir / 'responses' / f"{request_id}.json"
            if response_file.exists():
                try:
                    with open(response_file, 'r') as f:
                        response = json.load(f)
                    logger.info(f"✅ Response received: {request_id}")
                    return response
                except Exception as e:
                    logger.error(f"❌ Failed to read response: {e}")
            
            # 失敗ファイル確認
            failed_file = self.base_dir / 'failed' / f"{request_id}.json"
            if failed_file.exists():
                logger.warning(f"⚠️ Request failed: {request_id}")
                return None
            
            time.sleep(1)
        
        logger.warning(f"⏰ Response timeout: {request_id}")
        return None
    
    def run_comprehensive_test(self):
        """総合テスト実行"""
        logger.info("🚀 Starting comprehensive automated test...")
        
        test_cases = [
            ("hello_world", "Write a simple Python hello world function"),
            ("fibonacci", "Create a Python function to calculate fibonacci numbers"),
            ("json_parser", "Write a Python function to parse JSON data safely")
        ]
        
        for test_id, prompt in test_cases:
            try:
                logger.info(f"🧪 Running test: {test_id}")
                
                # テストリクエスト作成
                request_id = self.create_test_request(test_id, prompt)
                
                # レスポンス待機
                response = self.wait_for_response(request_id, timeout=45)
                
                if response:
                    self.success_count += 1
                    self.test_results.append({
                        'test_id': test_id,
                        'request_id': request_id,
                        'status': 'success',
                        'response_length': len(response.get('response', '')),
                        'execution_time': response.get('execution_time', 0)
                    })
                    logger.info(f"✅ Test passed: {test_id}")
                else:
                    self.error_count += 1
                    self.test_results.append({
                        'test_id': test_id,
                        'request_id': request_id,
                        'status': 'failed',
                        'error': 'No response or failed'
                    })
                    logger.error(f"❌ Test failed: {test_id}")
                
                # テスト間隔
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Test execution error: {test_id} - {e}")
                
                # 【事実ベース自己修正】
                facts = self.collect_system_facts()
                analysis = self.analyze_root_cause(e, facts)
                
                if self.self_heal(analysis):
                    logger.info("🔧 Self-healing successful, retrying test...")
                    # リトライ
                    try:
                        request_id = self.create_test_request(f"{test_id}_retry", prompt)
                        response = self.wait_for_response(request_id, timeout=60)
                        if response:
                            self.success_count += 1
                            logger.info(f"✅ Test passed after self-healing: {test_id}")
                        else:
                            self.error_count += 1
                            logger.error(f"❌ Test still failed after self-healing: {test_id}")
                    except Exception as retry_error:
                        logger.error(f"❌ Retry failed: {retry_error}")
                        self.error_count += 1
                else:
                    logger.error("❌ Self-healing failed")
                    self.error_count += 1
    
    def generate_final_report(self) -> Dict[str, Any]:
        """最終レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self.test_results),
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': self.success_count / len(self.test_results) * 100 if self.test_results else 0
            },
            'test_results': self.test_results,
            'system_facts': self.collect_system_facts()
        }
        
        # レポート保存
        report_file = self.base_dir / 'logs' / f"comprehensive_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Final report saved: {report_file}")
        return report

def main():
    """メイン実行関数"""
    print("🚀 GitHub Copilot評価フレームワーク 自律的総合テスト開始")
    print("=" * 60)
    
    tester = FactBasedSelfHealingTester()
    
    try:
        # Phase 3: テスト実行
        tester.run_comprehensive_test()
        
        # Phase 5: 完了とレポート
        report = tester.generate_final_report()
        
        print("\n" + "=" * 60)
        print("📊 **最終テスト結果**")
        print(f"✅ 成功: {report['summary']['success_count']}")
        print(f"❌ 失敗: {report['summary']['error_count']}")
        print(f"📈 成功率: {report['summary']['success_rate']:.1f}%")
        print("=" * 60)
        
        if report['summary']['success_rate'] >= 80:
            print("🎉 総合テスト成功！フレームワークは正常に動作しています。")
            return 0
        else:
            print("⚠️ 総合テストで問題が検出されました。ログを確認してください。")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Critical error in main execution: {e}")
        print(f"❌ 致命的エラー: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
