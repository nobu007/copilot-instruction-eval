#!/usr/bin/env python3
"""
File-based Copilot Evaluation Client

ファイル方式によるVSCode Copilot評価システム
リクエストファイルを作成し、レスポンスファイルを監視して結果を収集
"""

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import queue
from dataclasses import dataclass, asdict


@dataclass
class EvaluationRequest:
    """評価リクエスト"""
    request_id: str
    timestamp: str
    test_id: str
    prompt: str
    model: str
    mode: str
    timeout: int
    expected_elements: List[str]
    category: str


@dataclass
class EvaluationResponse:
    """評価レスポンス"""
    request_id: str
    timestamp: str
    success: bool
    execution_time: float
    response: str
    model_used: str
    mode_used: str
    response_length: int
    error_message: Optional[str]


@dataclass
class TestCase:
    """テストケース"""
    test_id: str
    prompt: str
    category: str
    expected_elements: List[str]
    description: str = ""


class FileBasedEvaluationClient:
    """ファイルベース評価クライアント"""
    
    def __init__(self, base_dir: str = "/tmp/copilot-evaluation"):
        self.base_dir = Path(base_dir)
        self.requests_dir = self.base_dir / "requests"
        self.responses_dir = self.base_dir / "responses"
        self.config_dir = self.base_dir / "config"
        self.results_dir = self.base_dir / "results"
        
        # 結果待ちキュー
        self.pending_requests: Dict[str, EvaluationRequest] = {}
        self.completed_responses: Dict[str, EvaluationResponse] = {}
        
        # 監視スレッド
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """ディレクトリ作成"""
        for dir_path in [self.requests_dir, self.responses_dir, self.config_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Ensured directory: {dir_path}")
    
    def start_monitoring(self):
        """レスポンス監視開始"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            print("⚠️ Monitoring already started")
            return
        
        self.stop_monitoring.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_responses, daemon=True)
        self.monitor_thread.start()
        print("🔍 Started response monitoring")
    
    def stop_monitoring(self):
        """レスポンス監視停止"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.stop_monitoring.set()
            self.monitor_thread.join(timeout=5)
            print("🛑 Stopped response monitoring")
    
    def _monitor_responses(self):
        """レスポンスファイル監視スレッド"""
        print(f"👀 Monitoring responses in: {self.responses_dir}")
        
        while not self.stop_monitoring.is_set():
            try:
                # レスポンスファイルをチェック
                for response_file in self.responses_dir.glob("resp_*.json"):
                    request_id = f"req_{response_file.stem.replace('resp_', '')}"
                    
                    if request_id in self.pending_requests and request_id not in self.completed_responses:
                        try:
                            # レスポンス読み込み
                            with open(response_file, 'r', encoding='utf-8') as f:
                                response_data = json.load(f)
                            
                            response = EvaluationResponse(**response_data)
                            self.completed_responses[request_id] = response
                            
                            print(f"📥 Response received: {request_id}")
                            print(f"✅ Success: {response.success}")
                            print(f"⏱️ Execution time: {response.execution_time:.2f}s")
                            
                            if response.error_message:
                                print(f"❌ Error: {response.error_message}")
                            
                            # レスポンスファイル削除（オプション）
                            # response_file.unlink()
                            
                        except Exception as e:
                            print(f"❌ Error reading response file {response_file}: {e}")
                
                time.sleep(0.5)  # 0.5秒間隔でチェック
                
            except Exception as e:
                print(f"❌ Error in monitoring thread: {e}")
                time.sleep(1)
    
    def submit_request(self, 
                      prompt: str, 
                      model: str = "copilot/gpt-4", 
                      mode: str = "agent",
                      test_id: str = None,
                      category: str = "general",
                      expected_elements: List[str] = None,
                      timeout: int = 60) -> str:
        """評価リクエスト送信"""
        
        # リクエストID生成
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        if test_id is None:
            test_id = f"test_{uuid.uuid4().hex[:6]}"
        
        # リクエスト作成
        request = EvaluationRequest(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            test_id=test_id,
            prompt=prompt,
            model=model,
            mode=mode,
            timeout=timeout,
            expected_elements=expected_elements or [],
            category=category
        )
        
        # リクエストファイル保存
        request_file = self.requests_dir / f"{request_id}.json"
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(request), f, indent=2, ensure_ascii=False)
        
        # 待ちキューに追加
        self.pending_requests[request_id] = request
        
        print(f"📤 Request submitted: {request_id}")
        print(f"📝 Test ID: {test_id}")
        print(f"🤖 Model: {model}, Mode: {mode}")
        print(f"📝 Prompt: {prompt[:100]}...")
        
        return request_id
    
    def wait_for_response(self, request_id: str, timeout: int = 120) -> Optional[EvaluationResponse]:
        """レスポンス待機"""
        start_time = time.time()
        
        print(f"⏳ Waiting for response: {request_id} (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            if request_id in self.completed_responses:
                response = self.completed_responses[request_id]
                print(f"✅ Response received for {request_id}")
                return response
            
            time.sleep(0.5)
        
        print(f"⏰ Timeout waiting for response: {request_id}")
        return None
    
    def run_test_case(self, test_case: TestCase, model: str, mode: str) -> Optional[EvaluationResponse]:
        """テストケース実行"""
        print(f"\n🧪 Running test case: {test_case.test_id}")
        print(f"📝 Description: {test_case.description}")
        print(f"🏷️ Category: {test_case.category}")
        
        request_id = self.submit_request(
            prompt=test_case.prompt,
            model=model,
            mode=mode,
            test_id=test_case.test_id,
            category=test_case.category,
            expected_elements=test_case.expected_elements
        )
        
        return self.wait_for_response(request_id)
    
    def run_batch_evaluation(self, 
                           test_cases: List[TestCase], 
                           models: List[str], 
                           modes: List[str]) -> Dict[str, Any]:
        """バッチ評価実行"""
        print(f"\n🚀 Starting batch evaluation")
        print(f"📊 Test cases: {len(test_cases)}")
        print(f"🤖 Models: {models}")
        print(f"⚙️ Modes: {modes}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_cases_count": len(test_cases),
            "models": models,
            "modes": modes,
            "results": [],
            "summary": {}
        }
        
        total_tests = len(test_cases) * len(models) * len(modes)
        completed_tests = 0
        
        for test_case in test_cases:
            for model in models:
                for mode in modes:
                    print(f"\n📈 Progress: {completed_tests + 1}/{total_tests}")
                    
                    response = self.run_test_case(test_case, model, mode)
                    
                    if response:
                        test_result = {
                            "test_id": test_case.test_id,
                            "model": model,
                            "mode": mode,
                            "success": response.success,
                            "execution_time": response.execution_time,
                            "response_length": response.response_length,
                            "error_message": response.error_message,
                            "category": test_case.category,
                            "expected_elements": test_case.expected_elements,
                            "response_preview": response.response[:200] if response.response else ""
                        }
                        results["results"].append(test_result)
                    else:
                        # タイムアウトの場合
                        test_result = {
                            "test_id": test_case.test_id,
                            "model": model,
                            "mode": mode,
                            "success": False,
                            "execution_time": 0,
                            "response_length": 0,
                            "error_message": "Timeout",
                            "category": test_case.category,
                            "expected_elements": test_case.expected_elements,
                            "response_preview": ""
                        }
                        results["results"].append(test_result)
                    
                    completed_tests += 1
                    
                    # 少し待機（VSCodeの負荷軽減）
                    time.sleep(1)
        
        # サマリー計算
        results["summary"] = self._calculate_summary(results["results"])
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"evaluation_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved: {results_file}")
        
        return results
    
    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """結果サマリー計算"""
        if not results:
            return {}
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        
        # モデル別統計
        model_stats = {}
        for result in results:
            model = result["model"]
            if model not in model_stats:
                model_stats[model] = {"total": 0, "success": 0, "avg_time": 0}
            
            model_stats[model]["total"] += 1
            if result["success"]:
                model_stats[model]["success"] += 1
            model_stats[model]["avg_time"] += result["execution_time"]
        
        # 平均時間計算
        for model in model_stats:
            if model_stats[model]["total"] > 0:
                model_stats[model]["avg_time"] /= model_stats[model]["total"]
                model_stats[model]["success_rate"] = model_stats[model]["success"] / model_stats[model]["total"]
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "model_statistics": model_stats
        }
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス取得"""
        return {
            "base_directory": str(self.base_dir),
            "monitoring_active": self.monitor_thread and self.monitor_thread.is_alive(),
            "pending_requests": len(self.pending_requests),
            "completed_responses": len(self.completed_responses),
            "directories": {
                "requests": str(self.requests_dir),
                "responses": str(self.responses_dir),
                "config": str(self.config_dir),
                "results": str(self.results_dir)
            }
        }


def create_sample_test_cases() -> List[TestCase]:
    """サンプルテストケース作成"""
    return [
        TestCase(
            test_id="code_gen_001",
            prompt="Create a Python function that calculates fibonacci numbers recursively",
            category="code_generation",
            expected_elements=["def", "fibonacci", "return", "recursive"],
            description="Basic recursive fibonacci function generation"
        ),
        TestCase(
            test_id="code_gen_002", 
            prompt="Write a JavaScript function to sort an array of objects by a specific property",
            category="code_generation",
            expected_elements=["function", "sort", "property", "array"],
            description="JavaScript array sorting function"
        ),
        TestCase(
            test_id="debug_001",
            prompt="Find and fix the bug in this code: def add(a, b): return a + b + 1",
            category="debugging",
            expected_elements=["bug", "fix", "return a + b"],
            description="Simple bug fixing task"
        ),
        TestCase(
            test_id="explain_001",
            prompt="Explain what this Python code does: [1, 2, 3, 4, 5][::2]",
            category="explanation",
            expected_elements=["slice", "step", "every", "second"],
            description="Code explanation task"
        )
    ]


if __name__ == "__main__":
    # サンプル実行
    client = FileBasedEvaluationClient()
    client.start_monitoring()
    
    try:
        # サンプルテストケース
        test_cases = create_sample_test_cases()
        
        # 評価実行
        results = client.run_batch_evaluation(
            test_cases=test_cases,
            models=["copilot/gpt-4", "copilot/gpt-3.5-turbo"],
            modes=["agent", "chat"]
        )
        
        # 結果表示
        print(f"\n📊 Evaluation Summary:")
        print(f"Total tests: {results['summary']['total_tests']}")
        print(f"Successful tests: {results['summary']['successful_tests']}")
        print(f"Success rate: {results['summary']['success_rate']:.2%}")
        
        print(f"\n🤖 Model Statistics:")
        for model, stats in results['summary']['model_statistics'].items():
            print(f"  {model}:")
            print(f"    Success rate: {stats['success_rate']:.2%}")
            print(f"    Average time: {stats['avg_time']:.2f}s")
    
    finally:
        client.stop_monitoring()
