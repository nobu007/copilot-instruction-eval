#!/usr/bin/env python3
"""
Copilot応答検証モジュール

このモジュールは実際のCopilot応答を取得・検証し、
偽陽性を排除するため実際の応答内容を厳密にチェックします。
"""

import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CopilotResponse:
    """Copilot応答を表すデータクラス"""
    success: bool
    instruction_id: str
    actual_response: str
    model: str
    execution_time: float
    timestamp: str
    verification_hash: str
    response_length: int
    is_mock: bool = False
    error_message: Optional[str] = None

class CopilotVerifier:
    """Copilot応答検証クラス"""
    
    def __init__(self, workspace_path: str = "/home/jinno/copilot-instruction-eval"):
        self.workspace_path = workspace_path
        self.extension_dir = Path(workspace_path) / ".vscode" / "copilot-automation"
        self.result_file = self.extension_dir / "execution_result.json"
        
        # 既知のモック応答パターン
        self.mock_patterns = [
            "This is a mock response",
            "mock response from Copilot",
            "test response",
            "placeholder response",
            "dummy response"
        ]
        
        # 最小応答長（実際の応答と判断する基準）
        self.min_real_response_length = 20
        
    def _calculate_verification_hash(self, response_data: Dict[str, Any]) -> str:
        """応答データの検証ハッシュを計算"""
        # ハッシュ計算用の正規化データ
        normalized_data = {
            "response": response_data.get("response", ""),
            "timestamp": response_data.get("timestamp", ""),
            "model": response_data.get("model", ""),
            "instruction_id": response_data.get("instruction_id", "")
        }
        
        data_str = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _is_mock_response(self, response_text: str) -> bool:
        """モック応答かどうかを判定"""
        if not response_text:
            return True
        
        response_lower = response_text.lower()
        
        # 既知のモックパターンチェック
        for pattern in self.mock_patterns:
            if pattern.lower() in response_lower:
                logger.warning(f"🎭 Mock pattern detected: {pattern}")
                return True
        
        # 応答長チェック
        if len(response_text) < self.min_real_response_length:
            logger.warning(f"📏 Response too short ({len(response_text)} chars)")
            return True
        
        # 繰り返しパターンチェック
        words = response_text.split()
        if len(set(words)) < len(words) * 0.3:  # 30%未満がユニークな単語
            logger.warning("🔄 Repetitive response pattern detected")
            return True
        
        return False
    
    def _validate_response_structure(self, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        """応答データ構造の検証"""
        required_fields = ["success", "response", "timestamp", "model"]
        
        for field in required_fields:
            if field not in response_data:
                return False, f"Missing required field: {field}"
        
        # タイムスタンプ検証
        try:
            timestamp = response_data["timestamp"]
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                response_time = datetime.fromtimestamp(timestamp)
            else:
                # ISO format
                response_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 応答が新しいかチェック（過去1時間以内）
            time_diff = datetime.now() - response_time.replace(tzinfo=None)
            if time_diff.total_seconds() > 3600:  # 1時間
                return False, f"Response too old: {time_diff}"
                
        except Exception as e:
            return False, f"Invalid timestamp format: {e}"
        
        return True, "Valid structure"
    
    def _analyze_response_quality(self, response_text: str, instruction: str = "") -> Dict[str, Any]:
        """応答品質の分析"""
        analysis = {
            "length": len(response_text),
            "word_count": len(response_text.split()),
            "has_code": "```" in response_text or "def " in response_text or "function " in response_text,
            "has_explanation": len(response_text.split('.')) > 2,
            "relevance_score": 0.0
        }
        
        # 関連性スコア計算（簡易版）
        if instruction:
            instruction_words = set(instruction.lower().split())
            response_words = set(response_text.lower().split())
            common_words = instruction_words.intersection(response_words)
            if instruction_words:
                analysis["relevance_score"] = len(common_words) / len(instruction_words)
        
        return analysis
    
    def verify_copilot_response(self, instruction_id: str, instruction_text: str = "", timeout: int = 60) -> CopilotResponse:
        """Copilot応答を検証"""
        logger.info(f"🔍 Verifying Copilot response for: {instruction_id}")
        
        start_time = time.time()
        
        # 結果ファイル待機
        wait_start = time.time()
        while time.time() - wait_start < timeout:
            if self.result_file.exists():
                try:
                    with open(self.result_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    # 指示IDマッチング確認
                    if response_data.get("instruction_id") == instruction_id:
                        break
                    
                except Exception as e:
                    logger.debug(f"⚠️ Error reading result file: {e}")
            
            time.sleep(1)
        else:
            # タイムアウト
            logger.error(f"❌ Response timeout for {instruction_id}")
            return CopilotResponse(
                success=False,
                instruction_id=instruction_id,
                actual_response="",
                model="unknown",
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                verification_hash="",
                response_length=0,
                error_message="Response timeout"
            )
        
        # 応答データ検証
        try:
            execution_time = time.time() - start_time
            
            # 構造検証
            is_valid, validation_message = self._validate_response_structure(response_data)
            if not is_valid:
                logger.error(f"❌ Invalid response structure: {validation_message}")
                return CopilotResponse(
                    success=False,
                    instruction_id=instruction_id,
                    actual_response="",
                    model="unknown",
                    execution_time=execution_time,
                    timestamp=datetime.now().isoformat(),
                    verification_hash="",
                    response_length=0,
                    error_message=f"Invalid structure: {validation_message}"
                )
            
            # 応答内容取得
            response_text = response_data.get("response", "")
            model = response_data.get("model", "unknown")
            timestamp = response_data.get("timestamp", datetime.now().isoformat())
            
            # モック応答チェック
            is_mock = self._is_mock_response(response_text)
            if is_mock:
                logger.warning(f"🎭 Mock response detected for {instruction_id}")
            
            # 検証ハッシュ計算
            verification_hash = self._calculate_verification_hash(response_data)
            
            # 応答品質分析
            quality_analysis = self._analyze_response_quality(response_text, instruction_text)
            
            # 成功判定
            success = (
                response_data.get("success", False) and
                not is_mock and
                len(response_text) >= self.min_real_response_length and
                quality_analysis["relevance_score"] > 0.1
            )
            
            logger.info(f"{'✅' if success else '❌'} Response verification: {instruction_id}")
            logger.info(f"📊 Quality: Length={quality_analysis['length']}, Relevance={quality_analysis['relevance_score']:.2f}, Mock={is_mock}")
            
            return CopilotResponse(
                success=success,
                instruction_id=instruction_id,
                actual_response=response_text,
                model=model,
                execution_time=execution_time,
                timestamp=str(timestamp),
                verification_hash=verification_hash,
                response_length=len(response_text),
                is_mock=is_mock,
                error_message=None if success else "Response quality insufficient"
            )
            
        except Exception as e:
            logger.error(f"❌ Response verification error: {e}")
            return CopilotResponse(
                success=False,
                instruction_id=instruction_id,
                actual_response="",
                model="unknown",
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                verification_hash="",
                response_length=0,
                error_message=f"Verification error: {e}"
            )
    
    def batch_verify_responses(self, instruction_ids: List[str], timeout_per_response: int = 60) -> List[CopilotResponse]:
        """複数の応答を一括検証"""
        logger.info(f"🔍 Batch verifying {len(instruction_ids)} responses...")
        
        results = []
        for instruction_id in instruction_ids:
            response = self.verify_copilot_response(instruction_id, timeout=timeout_per_response)
            results.append(response)
            
            # 進捗ログ
            success_count = sum(1 for r in results if r.success)
            logger.info(f"📊 Progress: {len(results)}/{len(instruction_ids)} ({success_count} successful)")
        
        return results
    
    def get_verification_summary(self, responses: List[CopilotResponse]) -> Dict[str, Any]:
        """検証結果のサマリーを生成"""
        if not responses:
            return {"total": 0, "successful": 0, "success_rate": 0.0}
        
        successful = [r for r in responses if r.success]
        mock_responses = [r for r in responses if r.is_mock]
        
        total_length = sum(r.response_length for r in successful)
        avg_length = total_length / len(successful) if successful else 0
        
        avg_execution_time = sum(r.execution_time for r in responses) / len(responses)
        
        summary = {
            "total": len(responses),
            "successful": len(successful),
            "failed": len(responses) - len(successful),
            "mock_detected": len(mock_responses),
            "success_rate": len(successful) / len(responses) * 100,
            "average_response_length": avg_length,
            "average_execution_time": avg_execution_time,
            "verification_timestamp": datetime.now().isoformat()
        }
        
        return summary

def main():
    """テスト実行"""
    verifier = CopilotVerifier()
    
    print("=== Copilot Verifier Test ===")
    
    # 単一応答検証テスト（コメントアウト）
    # response = verifier.verify_copilot_response("test_001")
    # print(f"Verification result: {response}")

if __name__ == "__main__":
    main()
