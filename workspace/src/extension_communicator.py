#!/usr/bin/env python3
"""
VSCode拡張機能通信モジュール

このモジュールはVSCode拡張機能との実通信を行い、
偽陽性を排除するため実際の通信成功を厳密に検証します。
"""

import os
import json
import time
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CommunicationStatus:
    """通信状態を表すデータクラス"""
    connection_established: bool
    handshake_successful: bool
    extension_version: Optional[str] = None
    last_heartbeat: Optional[str] = None
    command_queue_active: bool = False
    result_monitoring_active: bool = False

class ExtensionCommunicator:
    """VSCode拡張機能通信クラス"""
    
    def __init__(self, workspace_path: str = "/home/jinno/copilot-instruction-eval"):
        self.workspace_path = workspace_path
        self.extension_dir = Path(workspace_path) / ".vscode" / "copilot-automation"
        self.command_file = self.extension_dir / "command.json"
        self.result_file = self.extension_dir / "execution_result.json"
        self.status_file = self.extension_dir / "status.json"
        self.heartbeat_file = self.extension_dir / "heartbeat.json"
        
        # 通信用ディレクトリ作成
        self.extension_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_command_id(self) -> str:
        """一意のコマンドIDを生成"""
        timestamp = str(time.time())
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def _write_json_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """JSONファイルを安全に書き込み"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"📝 Written to {file_path.name}: {len(str(data))} chars")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to write {file_path.name}: {e}")
            return False
    
    def _read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """JSONファイルを安全に読み込み"""
        try:
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"📖 Read from {file_path.name}: {len(str(data))} chars")
            return data
        except Exception as e:
            logger.error(f"❌ Failed to read {file_path.name}: {e}")
            return None
    
    def _wait_for_file_change(self, file_path: Path, initial_mtime: float, timeout: int = 30) -> bool:
        """ファイルの変更を待機"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if file_path.exists():
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime > initial_mtime:
                        logger.debug(f"✅ File changed: {file_path.name}")
                        return True
            except Exception as e:
                logger.debug(f"⚠️ File check error: {e}")
            
            time.sleep(0.5)
        
        logger.warning(f"⏰ File change timeout: {file_path.name}")
        return False
    
    def send_heartbeat(self) -> bool:
        """ハートビート信号を送信"""
        heartbeat_data = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "sender": "python_executor",
            "sequence": int(time.time() * 1000)
        }
        
        success = self._write_json_file(self.heartbeat_file, heartbeat_data)
        if success:
            logger.debug("💓 Heartbeat sent")
        return success
    
    def check_extension_alive(self, timeout: int = 10) -> bool:
        """拡張機能の生存確認"""
        logger.info("🔍 Checking extension alive status...")
        
        # ハートビート送信
        if not self.send_heartbeat():
            return False
        
        # 応答待機
        initial_mtime = self.status_file.stat().st_mtime if self.status_file.exists() else 0
        
        if self._wait_for_file_change(self.status_file, initial_mtime, timeout):
            status_data = self._read_json_file(self.status_file)
            if status_data and status_data.get("alive", False):
                logger.info("✅ Extension is alive")
                return True
        
        logger.warning("❌ Extension not responding")
        return False
    
    def establish_connection(self) -> CommunicationStatus:
        """拡張機能との接続を確立"""
        logger.info("🤝 Establishing connection with extension...")
        
        status = CommunicationStatus(
            connection_established=False,
            handshake_successful=False
        )
        
        # 1. ハートビート確認
        if not self.send_heartbeat():
            logger.error("❌ Failed to send heartbeat")
            return status
        
        status.connection_established = True
        
        # 2. 拡張機能生存確認
        if not self.check_extension_alive():
            logger.error("❌ Extension not alive")
            return status
        
        # 3. ハンドシェイク実行
        handshake_data = {
            "type": "handshake",
            "timestamp": datetime.now().isoformat(),
            "client_version": "1.0.0",
            "workspace_path": self.workspace_path
        }
        
        if not self._write_json_file(self.command_file, handshake_data):
            logger.error("❌ Failed to send handshake")
            return status
        
        # 4. ハンドシェイク応答待機
        initial_mtime = self.result_file.stat().st_mtime if self.result_file.exists() else 0
        
        if self._wait_for_file_change(self.result_file, initial_mtime, 15):
            result_data = self._read_json_file(self.result_file)
            if result_data and result_data.get("type") == "handshake_response":
                status.handshake_successful = True
                status.extension_version = result_data.get("extension_version")
                status.last_heartbeat = datetime.now().isoformat()
                status.command_queue_active = True
                status.result_monitoring_active = True
                
                logger.info(f"✅ Handshake successful (Extension v{status.extension_version})")
            else:
                logger.error("❌ Invalid handshake response")
        else:
            logger.error("❌ Handshake timeout")
        
        return status
    
    def send_command(self, command_type: str, command_data: Dict[str, Any], timeout: int = 30) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """拡張機能にコマンドを送信"""
        command_id = self._generate_command_id()
        
        logger.info(f"📤 Sending command: {command_type} (ID: {command_id})")
        
        # コマンドデータ準備
        full_command = {
            "id": command_id,
            "type": command_type,
            "timestamp": datetime.now().isoformat(),
            "data": command_data
        }
        
        # 結果ファイルの初期状態記録
        initial_mtime = self.result_file.stat().st_mtime if self.result_file.exists() else 0
        
        # コマンド送信
        if not self._write_json_file(self.command_file, full_command):
            logger.error(f"❌ Failed to send command: {command_type}")
            return False, None
        
        # 応答待機
        logger.info(f"⏳ Waiting for response... (timeout: {timeout}s)")
        
        if self._wait_for_file_change(self.result_file, initial_mtime, timeout):
            result_data = self._read_json_file(self.result_file)
            
            if result_data and result_data.get("command_id") == command_id:
                logger.info(f"✅ Command response received: {command_type}")
                return True, result_data
            else:
                logger.warning(f"⚠️ Response ID mismatch or invalid data")
                return False, result_data
        else:
            logger.error(f"❌ Command timeout: {command_type}")
            return False, None
    
    def send_copilot_prompt(self, prompt: str, mode: str = "agent", model: str = "copilot/gpt-4") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Copilotプロンプトを送信"""
        logger.info(f"🤖 Sending Copilot prompt (mode: {mode}, model: {model})")
        logger.debug(f"📝 Prompt: {prompt[:100]}...")
        
        command_data = {
            "prompt": prompt,
            "mode": mode,
            "model": model,
            "instruction_id": f"prompt_{int(time.time())}"
        }
        
        return self.send_command("sendPrompt", command_data, timeout=60)
    
    def get_communication_status(self) -> CommunicationStatus:
        """現在の通信状態を取得"""
        logger.debug("🔍 Getting communication status...")
        
        # 基本的な状態確認
        status = CommunicationStatus(
            connection_established=self.extension_dir.exists(),
            handshake_successful=False
        )
        
        # ステータスファイル確認
        status_data = self._read_json_file(self.status_file)
        if status_data:
            status.extension_version = status_data.get("version")
            status.last_heartbeat = status_data.get("last_heartbeat")
            status.command_queue_active = status_data.get("command_queue_active", False)
            status.result_monitoring_active = status_data.get("result_monitoring_active", False)
            status.handshake_successful = status_data.get("handshake_successful", False)
        
        return status
    
    def cleanup(self):
        """通信リソースをクリーンアップ"""
        logger.info("🧹 Cleaning up communication resources...")
        
        # 一時ファイル削除
        temp_files = [self.command_file, self.heartbeat_file]
        for file_path in temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"🗑️ Deleted: {file_path.name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete {file_path.name}: {e}")

def main():
    """テスト実行"""
    communicator = ExtensionCommunicator()
    
    print("=== Extension Communicator Test ===")
    
    # 通信状態確認
    status = communicator.get_communication_status()
    print(f"Connection established: {status.connection_established}")
    print(f"Handshake successful: {status.handshake_successful}")
    
    # 接続確立テスト（コメントアウト）
    # connection_status = communicator.establish_connection()
    # print(f"Connection result: {connection_status}")

if __name__ == "__main__":
    main()
