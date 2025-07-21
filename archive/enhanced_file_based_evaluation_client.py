#!/usr/bin/env python3
"""
Enhanced File-based Copilot Evaluation Client with Reprocessing & Timestamp Validation

再処理機能・タイムスタンプ整合性チェック付きファイルベース評価システム
"""

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class EvaluationRequest:
    """評価リクエスト（拡張版）"""
    request_id: str
    timestamp: str
    test_id: str
    prompt: str
    model: str
    mode: str
    timeout: int
    expected_elements: List[str]
    category: str
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0
    checksum: str = ""


@dataclass
class EvaluationResponse:
    """評価レスポンス（拡張版）"""
    request_id: str
    timestamp: str
    success: bool
    execution_time: float
    response: str
    model_used: str
    mode_used: str
    response_length: int
    error_message: Optional[str]
    retry_count: int
    request_timestamp: str
    checksum: str = ""


@dataclass
class TestCase:
    """テストケース"""
    test_id: str
    prompt: str
    category: str
    expected_elements: List[str]
    description: str = ""
    priority: int = 0
    timeout: int = 60


class EnhancedFileBasedEvaluationClient:
    """拡張ファイルベース評価クライアント"""
    
    def __init__(self, base_dir: str = "/tmp/copilot-evaluation"):
        self.base_dir = Path(base_dir)
        self.requests_dir = self.base_dir / "requests"
        self.responses_dir = self.base_dir / "responses"
        self.config_dir = self.base_dir / "config"
        self.results_dir = self.base_dir / "results"
        self.processing_dir = self.base_dir / "processing"
        self.failed_dir = self.base_dir / "failed"
        
        # 結果管理
        self.pending_requests: Dict[str, EvaluationRequest] = {}
        self.completed_responses: Dict[str, EvaluationResponse] = {}
        self.failed_requests: Dict[str, Dict[str, Any]] = {}
        
        # 監視スレッド
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # 状態ファイル
        self.client_state_file = self.config_dir / "client_state.json"
        
        self._ensure_directories()
        self._load_client_state()
    
    def _ensure_directories(self):
        """ディレクトリ作成"""
        for dir_path in [self.requests_dir, self.responses_dir, self.config_dir, 
                        self.results_dir, self.processing_dir, self.failed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Ensured directory: {dir_path}")
    
    def _load_client_state(self):
        """クライアント状態読み込み"""
        try:
            if self.client_state_file.exists():
                with open(self.client_state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # 未完了リクエストの復旧
                if 'pending_requests' in state_data:
                    for req_data in state_data['pending_requests']:
                        request = EvaluationRequest(**req_data)
                        self.pending_requests[request.request_id] = request
                
                print(f"📋 Loaded client state: {len(self.pending_requests)} pending requests")
        except Exception as e:
            print(f"⚠️ Error loading client state: {e}")
    
    def _save_client_state(self):
        """クライアント状態保存"""
        try:
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'pending_requests': [asdict(req) for req in self.pending_requests.values()],
                'completed_count': len(self.completed_responses),
                'failed_count': len(self.failed_requests)
            }
            
            with open(self.client_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving client state: {e}")
    
    def _calculate_checksum(self, data: str) -> str:
        """データのチェックサム計算"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def start_monitoring(self):
        """レスポンス監視開始（拡張版）"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            print("⚠️ Monitoring already started")
            return
        
        self.stop_monitoring.clear()
        self.monitor_thread = threading.Thread(target=self._enhanced_monitor_responses, daemon=True)
        self.monitor_thread.start()
        print("🔍 Started enhanced response monitoring")
    
    def stop_monitoring(self):
        """レスポンス監視停止"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.stop_monitoring.set()
            self.monitor_thread.join(timeout=5)
            print("🛑 Stopped response monitoring")
        
        self._save_client_state()
    
    def _enhanced_monitor_responses(self):
        """拡張レスポンス監視スレッド"""
        print(f"👀 Enhanced monitoring: responses, failed requests, and stale processing")
        
        while not self.stop_monitoring.is_set():
            try:
                # 1. レスポンスファイルをチェック
                self._check_responses()
                
                # 2. 失敗したリクエストをチェック
                self._check_failed_requests()
                
                # 3. 古い処理中リクエストをチェック
                self._check_stale_processing()
                
                # 4. タイムスタンプ整合性チェック
                self._validate_timestamps()
                
                time.sleep(2)  # 2秒間隔でチェック
                
            except Exception as e:
                print(f"❌ Error in enhanced monitoring thread: {e}")
                time.sleep(5)
    
    def _check_responses(self):
        """レスポンスファイルチェック"""
        for response_file in self.responses_dir.glob("*.json"):
            request_id = f"req_{response_file.stem.replace('resp_', '')}"
            
            if request_id in self.pending_requests and request_id not in self.completed_responses:
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    # Handle missing fields for backward compatibility
                    if 'retry_count' not in response_data:
                        response_data['retry_count'] = 0
                    if 'request_timestamp' not in response_data:
                        response_data['request_timestamp'] = response_data.get('timestamp', '')
                    if 'checksum' not in response_data:
                        response_data['checksum'] = ''
                    
                    response = EvaluationResponse(**response_data)
                    
                    # タイムスタンプ整合性チェック
                    if self._is_response_valid(request_id, response):
                        self.completed_responses[request_id] = response
                        
                        print(f"📥 Valid response received: {request_id}")
                        print(f"✅ Success: {response.success}")
                        print(f"⏱️ Execution time: {response.execution_time:.2f}s")
                        
                        if response.error_message:
                            print(f"❌ Error: {response.error_message}")
                    else:
                        print(f"⚠️ Invalid response timestamp: {request_id}")
                        # 再処理をトリガー
                        self._trigger_reprocessing(request_id, "Invalid response timestamp")
                    
                except Exception as e:
                    print(f"❌ Error reading response file {response_file}: {e}")
    
    def _check_failed_requests(self):
        """失敗リクエストチェック"""
        for failed_file in self.failed_dir.glob("req_*_failed_*.json"):
            try:
                with open(failed_file, 'r', encoding='utf-8') as f:
                    failed_data = json.load(f)
                
                request_id = failed_data.get('request_id')
                if request_id and request_id in self.pending_requests:
                    self.failed_requests[request_id] = {
                        'request': failed_data,
                        'failure_reason': failed_data.get('failure_reason', 'Unknown'),
                        'failed_at': failed_data.get('failed_at'),
                        'file_path': str(failed_file)
                    }
                    
                    print(f"💀 Request failed permanently: {request_id}")
                    print(f"   Reason: {failed_data.get('failure_reason', 'Unknown')}")
                    
            except Exception as e:
                print(f"❌ Error reading failed file {failed_file}: {e}")
    
    def _check_stale_processing(self):
        """古い処理中リクエストチェック"""
        now = datetime.now()
        stale_threshold = timedelta(minutes=10)  # 10分以上処理中のものは古いとみなす
        
        for processing_file in self.processing_dir.glob("req_*.json"):
            try:
                file_mtime = datetime.fromtimestamp(processing_file.stat().st_mtime)
                
                if now - file_mtime > stale_threshold:
                    request_id = processing_file.stem
                    print(f"⏰ Stale processing detected: {request_id}")
                    
                    # 再処理をトリガー
                    self._trigger_reprocessing(request_id, "Stale processing detected")
                    
            except Exception as e:
                print(f"❌ Error checking stale processing {processing_file}: {e}")
    
    def _validate_timestamps(self):
        """タイムスタンプ整合性チェック"""
        for request_id, request in self.pending_requests.items():
            if request_id in self.completed_responses:
                response = self.completed_responses[request_id]
                
                # リクエストとレスポンスのタイムスタンプ比較
                try:
                    request_time = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
                    response_time = datetime.fromisoformat(response.timestamp.replace('Z', '+00:00'))
                    
                    # レスポンスがリクエストより古い場合は無効
                    if response_time < request_time:
                        print(f"⚠️ Response older than request: {request_id}")
                        print(f"   Request: {request.timestamp}")
                        print(f"   Response: {response.timestamp}")
                        
                        # レスポンスを無効化して再処理
                        del self.completed_responses[request_id]
                        self._trigger_reprocessing(request_id, "Response older than request")
                except Exception as e:
                    print(f"❌ Error validating timestamps for {request_id}: {e}")
    
    def _is_response_valid(self, request_id: str, response: EvaluationResponse) -> bool:
        """レスポンス有効性チェック"""
        if request_id not in self.pending_requests:
            return False
        
        request = self.pending_requests[request_id]
        
        try:
            # タイムスタンプ比較
            request_time = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            response_time = datetime.fromisoformat(response.timestamp.replace('Z', '+00:00'))
            
            # レスポンスがリクエストより新しいかチェック
            if response_time < request_time:
                return False
            
            # リクエストIDの整合性チェック
            if response.request_id != request_id:
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error validating response: {e}")
            return False
    
    def _trigger_reprocessing(self, request_id: str, reason: str):
        """再処理トリガー"""
        if request_id not in self.pending_requests:
            return
        
        request = self.pending_requests[request_id]
        
        # リトライ回数チェック
        if request.retry_count >= request.max_retries:
            print(f"❌ Max retries exceeded for reprocessing: {request_id}")
            return
        
        print(f"🔄 Triggering reprocessing: {request_id}")
        print(f"   Reason: {reason}")
        
        # リトライ回数を増やして再送信
        request.retry_count += 1
        request.timestamp = datetime.now().isoformat()
        
        # 既存のレスポンス削除
        if request_id in self.completed_responses:
            del self.completed_responses[request_id]
        
        # 再送信
        self._submit_request_file(request)
    
    def submit_request(self, 
                      prompt: str, 
                      model: str = "copilot/gpt-4", 
                      mode: str = "agent",
                      test_id: str = None,
                      category: str = "general",
                      expected_elements: List[str] = None,
                      timeout: int = 60,
                      priority: int = 0,
                      max_retries: int = 3) -> str:
        """評価リクエスト送信（拡張版）"""
        
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
            category=category,
            retry_count=0,
            max_retries=max_retries,
            priority=priority,
            checksum=self._calculate_checksum(prompt)
        )
        
        # 待ちキューに追加
        self.pending_requests[request_id] = request
        
        # リクエストファイル送信
        self._submit_request_file(request)
        
        print(f"📤 Enhanced request submitted: {request_id}")
        print(f"📝 Test ID: {test_id}, Priority: {priority}")
        print(f"🤖 Model: {model}, Mode: {mode}")
        print(f"🔄 Max retries: {max_retries}")
        
        return request_id
    
    def _submit_request_file(self, request: EvaluationRequest):
        """リクエストファイル送信"""
        # 優先度に基づくファイル名
        priority_prefix = f"p{request.priority}_" if request.priority > 0 else ""
        filename = f"{priority_prefix}{request.request_id}.json"
        
        request_file = self.requests_dir / filename
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(request), f, indent=2, ensure_ascii=False)
        
        self._save_client_state()
    
    def wait_for_response(self, request_id: str, timeout: int = 120) -> Optional[EvaluationResponse]:
        """レスポンス待機（拡張版）"""
        start_time = time.time()
        
        print(f"⏳ Waiting for response: {request_id} (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            # 成功レスポンス
            if request_id in self.completed_responses:
                response = self.completed_responses[request_id]
                print(f"✅ Response received for {request_id}")
                return response
            
            # 失敗レスポンス
            if request_id in self.failed_requests:
                failed_info = self.failed_requests[request_id]
                print(f"❌ Request failed permanently: {request_id}")
                print(f"   Reason: {failed_info['failure_reason']}")
                return None
            
            time.sleep(0.5)
        
        print(f"⏰ Timeout waiting for response: {request_id}")
        
        # タイムアウト時の再処理トリガー
        self._trigger_reprocessing(request_id, "Client timeout")
        
        return None
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """拡張ステータス取得"""
        return {
            "base_directory": str(self.base_dir),
            "monitoring_active": self.monitor_thread and self.monitor_thread.is_alive(),
            "pending_requests": len(self.pending_requests),
            "completed_responses": len(self.completed_responses),
            "failed_requests": len(self.failed_requests),
            "features": {
                "reprocessing": True,
                "timestamp_validation": True,
                "retry_mechanism": True,
                "priority_support": True,
                "checksum_validation": True
            },
            "directories": {
                "requests": str(self.requests_dir),
                "responses": str(self.responses_dir),
                "config": str(self.config_dir),
                "results": str(self.results_dir),
                "processing": str(self.processing_dir),
                "failed": str(self.failed_dir)
            }
        }


def create_enhanced_test_cases() -> List[TestCase]:
    """拡張テストケース作成"""
    return [
        TestCase(
            test_id="critical_001",
            prompt="Fix this critical security vulnerability: SQL injection in user login",
            category="security",
            expected_elements=["parameterized", "prepared", "sanitize"],
            description="Critical security fix",
            priority=2,
            timeout=90
        ),
        TestCase(
            test_id="normal_001",
            prompt="Create a Python function that calculates fibonacci numbers",
            category="code_generation",
            expected_elements=["def", "fibonacci", "return"],
            description="Normal priority code generation",
            priority=0,
            timeout=60
        )
    ]


if __name__ == "__main__":
    # 拡張システムのサンプル実行
    client = EnhancedFileBasedEvaluationClient()
    client.start_monitoring()
    
    try:
        print("🧪 Testing enhanced evaluation system...")
        
        # 簡単なテスト
        request_id = client.submit_request(
            prompt="Write a simple hello world function",
            test_id="enhanced_test_001",
            priority=1
        )
        
        response = client.wait_for_response(request_id, timeout=60)
        
        if response:
            print(f"✅ Test successful!")
            print(f"   Response length: {response.response_length}")
            print(f"   Execution time: {response.execution_time:.2f}s")
            print(f"   Retry count: {response.retry_count}")
        else:
            print(f"❌ Test failed or timed out")
        
        # ステータス表示
        status = client.get_enhanced_status()
        print(f"\n📊 System Status:")
        print(f"   Monitoring: {status['monitoring_active']}")
        print(f"   Pending: {status['pending_requests']}")
        print(f"   Completed: {status['completed_responses']}")
        print(f"   Failed: {status['failed_requests']}")
        
    finally:
        client.stop_monitoring()
