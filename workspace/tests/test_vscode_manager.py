#!/usr/bin/env python3
"""
VSCode Process Manager Unit Tests
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import time
from unittest.mock import patch, MagicMock
from vscode_process_manager import VSCodeProcessManager, VSCodeStatus

class TestVSCodeProcessManager(unittest.TestCase):
    """VSCode Process Manager テストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        self.manager = VSCodeProcessManager()
    
    def test_init(self):
        """初期化テスト"""
        self.assertIsNotNone(self.manager.workspace_path)
        self.assertIsInstance(self.manager.vscode_executables, list)
        self.assertTrue(len(self.manager.vscode_executables) > 0)
    
    @patch('subprocess.run')
    def test_find_vscode_executable_success(self, mock_run):
        """VSCode実行可能ファイル検索成功テスト"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1.85.0"
        
        result = self.manager._find_vscode_executable()
        self.assertIsNotNone(result)
    
    @patch('subprocess.run')
    def test_find_vscode_executable_failure(self, mock_run):
        """VSCode実行可能ファイル検索失敗テスト"""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.manager._find_vscode_executable()
        self.assertIsNone(result)
    
    @patch('psutil.process_iter')
    def test_get_vscode_processes(self, mock_process_iter):
        """VSCodeプロセス取得テスト"""
        # モックプロセス作成
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 12345,
            'name': 'code',
            'cmdline': ['/usr/bin/code', '--new-window'],
            'create_time': time.time()
        }
        mock_process_iter.return_value = [mock_proc]
        
        processes = self.manager._get_vscode_processes()
        self.assertIsInstance(processes, list)
    
    def test_get_status_json(self):
        """ステータスJSON取得テスト"""
        json_str = self.manager.get_status_json()
        self.assertIsInstance(json_str, str)
        self.assertIn('vscode_status', json_str)
    
    def test_vscode_status_dataclass(self):
        """VSCodeStatusデータクラステスト"""
        status = VSCodeStatus(is_running=True, process_id=12345)
        self.assertTrue(status.is_running)
        self.assertEqual(status.process_id, 12345)

if __name__ == '__main__':
    unittest.main()
