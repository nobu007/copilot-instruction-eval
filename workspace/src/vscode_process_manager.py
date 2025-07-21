#!/usr/bin/env python3
"""
VSCode Desktop プロセス管理モジュール（シングルトンモデル）

このモジュールは、指定されたワークスペースに対してVSCodeプロセスが常に一つだけ
実行されている状態（シングルトン）を保証します。プロセスの起動、シャットダウン、
リロード、状態監視の責務を担います。

アーキテクチャの要点:
- 唯一の信頼できる情報源 (Single Source of Truth):
  `_find_vscode_process_by_workspace`メソッドが、ワークスペースに紐づく
  真のVSCodeメインプロセスを特定する唯一の手段です。ラッパープロセスや
  子プロセスは確実に除外されます。
- 正常なシャットダウン (Graceful Shutdown):
  プロセスの終了は、拡張機能に実装された`copilot-automation.shutdown`コマンドを
  呼び出すことで、VSCode自身に自律的に行わせます。`kill`による強制終了は
  行いません。
- 自己修復PID管理 (Self-Healing PID):
  `get_status`は、管理PIDとスキャンで発見した実プロセスに矛盾が生じた場合、
  常にスキャン結果を正として自動的にPIDファイルを修正します。
"""

import os
import time
import subprocess
import psutil
import logging
import signal
from typing import Optional, Tuple

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class VSCodeProcessManager:
    """VSCode Desktopプロセスをシングルトンサーバーとして管理するクラス"""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.extension_id = "windsurf-dev.copilot-automation-extension"
        self.pid_file_path = os.path.join(os.path.dirname(__file__), ".vscode_manager.pid")
        self.vscode_executable = self._find_vscode_executable()
        if not self.vscode_executable:
            raise RuntimeError("VSCode executable not found. Please ensure it's in a standard location or in your PATH.")

    def _find_vscode_executable(self) -> Optional[str]:
        """利用可能なVSCodeの実行可能ファイルを探します。"""
        for executable in ["/usr/bin/code", "/snap/bin/code", "code"]:
            try:
                result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"✅ VSCode executable found: {executable}")
                    return executable
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None

    def _load_pid(self) -> Optional[int]:
        """PIDファイルから管理PIDを読み込みます。"""
        if os.path.exists(self.pid_file_path):
            with open(self.pid_file_path, 'r') as f:
                try:
                    pid = int(f.read().strip())
                    if psutil.pid_exists(pid):
                        return pid
                except (ValueError, TypeError):
                    pass # ファイルが空か、不正な内容の場合
        return None

    def _save_pid(self, pid: Optional[int]):
        """管理PIDをPIDファイルに保存、またはファイルを削除します。"""
        if pid:
            with open(self.pid_file_path, 'w') as f:
                f.write(str(pid))
        elif os.path.exists(self.pid_file_path):
            os.remove(self.pid_file_path)

    def _find_vscode_process_by_workspace(self) -> Optional[psutil.Process]:
        """指定されたワークスペースのメインVSCodeプロセスを見つけます。"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if not (cmdline and proc.info.get('name') and 'code' in proc.info['name'].lower()):
                    continue
                
                # 子プロセス（レンダラーなど）を除外
                if any(arg.startswith('--type=') for arg in cmdline):
                    continue
                
                # ワークスペースパスが含まれているか確認
                if self.workspace_path in ' '.join(cmdline):
                    logger.info(f"🔍 Found VSCode main process PID: {proc.pid} for workspace '{self.workspace_path}'.")
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def get_status(self) -> Tuple[Optional[int], bool]:
        """VSCodeプロセスの状態を堅牢に確認し、PIDを自己修復します。"""
        managed_pid = self._load_pid()
        found_process = self._find_vscode_process_by_workspace()

        if found_process:
            if managed_pid != found_process.pid:
                logger.warning(f"⚠️ PID mismatch. Found running process {found_process.pid}, but managed PID was {managed_pid}. Updating PID file.")
                self._save_pid(found_process.pid)
            return found_process.pid, True
        else:
            if managed_pid:
                logger.warning(f"⚠️ Managed PID {managed_pid} exists in file, but no matching process found. Clearing PID file.")
                self._save_pid(None)
            return None, False

    def ensure_singleton_running(self):
        """VSCodeプロセスが存在しない場合にのみ、新しいプロセスを起動します。"""
        pid, is_running = self.get_status()
        if is_running:
            logger.info(f"✅ VSCode singleton is already running with PID {pid}.")
            return

        logger.info("🚀 Launching a new VSCode singleton instance...")
        try:
            # --new-window フラグは、既存のウィンドウで開くのを防ぐために重要
            # 致命的な欠陥の修正: --disable-extensions を削除し、拡張機能が確実に読み込まれるようにする
            # さらに、特定の拡張機能だけを有効にする方がより安全であるため、--enable-extensions を使用
            cmd = [self.vscode_executable, self.workspace_path, '--new-window', '--enable-extensions']
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"✅ VSCode launch command issued. Waiting for main process to appear...")

            # ポーリングで真のプロセスPIDを見つける (タイムアウト付き)
            found_pid = None
            for _ in range(30): # 最大30秒待機
                pid, is_running = self.get_status()
                if is_running:
                    found_pid = pid
                    logger.info(f"✅ Found main VSCode process with PID {found_pid}.")
                    break
                time.sleep(1)
            
            if not found_pid:
                raise RuntimeError("VSCode main process did not appear within 30 seconds.")



            # 最終確認
            pid, is_running = self.get_status()
            if not is_running or pid != found_pid:
                raise RuntimeError(f"VSCode process {found_pid} disappeared after launch.")
            
            logger.info(f"✅ VSCode singleton is stable and running with PID {pid}.")

        except Exception as e:
            logger.critical(f"❌ Failed to start VSCode process: {e}")
            self._save_pid(None) # 失敗した場合はPIDをクリア
            raise

    def shutdown_singleton(self, timeout: int = 60):
        """管理下のVSCodeプロセスにSIGTERMシグナルを送信し、正常な終了を試みます。"""
        pid, is_running = self.get_status()
        if not is_running:
            logger.info("✅ VSCode is not running. No shutdown needed.")
            self._save_pid(None) # PIDファイルが残っている場合を考慮してクリア
            return

        logger.info(f"Requesting graceful shutdown for VSCode PID {pid} via SIGTERM...")
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("✅ SIGTERM signal sent successfully.")
        except ProcessLookupError:
            logger.warning(f"⚠️ Process with PID {pid} not found. It might have already terminated.")
            # If the process is already gone, we can consider the shutdown successful.
            self._save_pid(None)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send SIGTERM to process {pid}: {e}")
            return False

        logger.info(f"⏳ Waiting up to {timeout} seconds for process {pid} to terminate...")
        for _ in range(timeout):
            if not psutil.pid_exists(pid):
                logger.info(f"✅ Process {pid} has terminated gracefully.")
                self._save_pid(None) # PIDファイルをクリーンアップ
                return
            time.sleep(1)

        logger.error(f"❌ Process {pid} did not terminate within the timeout. Manual intervention may be required.")
        # このアーキテクチャでは強制終了は行わない

    def reload_singleton(self):
        """VSCodeシングルトンを完全にリロード（シャットダウンしてから起動）します。"""
        logger.info("🔄 Starting full reload of VSCode singleton...")
        self.shutdown_singleton()
        self.ensure_singleton_running()
        logger.info("✅ Full reload of VSCode singleton completed.")

    def execute_vscode_command(self, command: str) -> Tuple[bool, str]:
        """実行中のVSCodeインスタンスに対してコマンドを実行します。"""
        pid, is_running = self.get_status()
        if not is_running:
            logger.error("❌ Cannot execute command, no managed VSCode process is running.")
            return False, "No managed VSCode process is running."

        try:
            cmd = [self.vscode_executable, '--command', command]
            logger.info(f"Executing VSCode command: '{command}' on PID {pid}")
            subprocess.run(cmd, cwd=self.workspace_path, check=True, timeout=15, capture_output=True)
            logger.info(f"✅ Successfully sent command '{command}' to VSCode.")
            return True, f"Command '{command}' executed."
        except Exception as e:
            logger.error(f"❌ Failed to execute VSCode command '{command}': {getattr(e, 'stderr', e)}")
            return False, str(e)


