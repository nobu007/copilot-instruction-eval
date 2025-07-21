#!/usr/bin/env python3
"""
GUI テストモニター - VSCode Activity Monitor連携
ユーザーフィードバック監視・自動修正ループ
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import subprocess
import logging
from typing import List, Dict

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CopilotTestGUI:
    """Copilot評価フレームワーク テストGUI"""
    
    def __init__(self):
        self.base_dir = Path('/tmp/copilot-evaluation')
        self.root = tk.Tk()
        self.root.title("🤖 Copilot評価フレームワーク テストモニター")
        self.root.geometry("800x600")
        
        self.monitoring = False
        self.test_results = []
        
        self.setup_gui()
        self.start_monitoring()
    
    def setup_gui(self):
        """GUI構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🤖 GitHub Copilot 評価フレームワーク", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # ステータス表示
        self.status_var = tk.StringVar(value="🔄 監視開始中...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                font=('Arial', 12))
        status_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # 統計情報フレーム
        stats_frame = ttk.LabelFrame(main_frame, text="📊 テスト統計", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.success_var = tk.StringVar(value="成功: 0")
        self.failed_var = tk.StringVar(value="失敗: 0")
        self.total_var = tk.StringVar(value="総数: 0")
        
        ttk.Label(stats_frame, textvariable=self.success_var, foreground="green").grid(row=0, column=0, padx=10)
        ttk.Label(stats_frame, textvariable=self.failed_var, foreground="red").grid(row=0, column=1, padx=10)
        ttk.Label(stats_frame, textvariable=self.total_var).grid(row=0, column=2, padx=10)
        
        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="📝 リアルタイムログ", padding="10")
        log_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # コントロールボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.start_test_btn = ttk.Button(button_frame, text="🚀 自動テスト開始", 
                                        command=self.start_automated_test)
        self.start_test_btn.grid(row=0, column=0, padx=5)
        
        self.reprocess_btn = ttk.Button(button_frame, text="🔄 失敗リクエスト再処理", 
                                       command=self.reprocess_failed)
        self.reprocess_btn.grid(row=0, column=1, padx=5)
        
        self.open_vscode_btn = ttk.Button(button_frame, text="📱 VSCode Activity Monitor", 
                                         command=self.open_vscode_monitor)
        self.open_vscode_btn.grid(row=0, column=2, padx=5)
        
        self.complete_btn = ttk.Button(button_frame, text="✅ テスト完了", 
                                      command=self.complete_test, 
                                      style="Accent.TButton")
        self.complete_btn.grid(row=0, column=3, padx=5)
        
        # フィードバック入力エリア
        feedback_frame = ttk.LabelFrame(main_frame, text="💬 フィードバック入力", padding="10")
        feedback_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.feedback_entry = ttk.Entry(feedback_frame, width=60)
        self.feedback_entry.grid(row=0, column=0, padx=(0, 10))
        
        feedback_btn = ttk.Button(feedback_frame, text="📤 送信", 
                                 command=self.send_feedback)
        feedback_btn.grid(row=0, column=1)
        
        # グリッド重み設定
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def log_message(self, message: str, level: str = "INFO"):
        """ログメッセージ表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        
        # ログファイルにも記録
        try:
            log_file = self.base_dir / 'logs' / 'gui_monitor.log'
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} [{level}] {message}\n")
        except Exception as e:
            print(f"Failed to write log: {e}")
    
    def update_stats(self):
        """統計情報更新"""
        success_count = len([r for r in self.test_results if r.get('status') == 'success'])
        failed_count = len([r for r in self.test_results if r.get('status') == 'failed'])
        total_count = len(self.test_results)
        
        self.success_var.set(f"成功: {success_count}")
        self.failed_var.set(f"失敗: {failed_count}")
        self.total_var.set(f"総数: {total_count}")
    
    def start_monitoring(self):
        """ファイル監視開始"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_files, daemon=True)
        self.monitor_thread.start()
        self.log_message("📁 ファイル監視を開始しました")
    
    def monitor_files(self):
        """ファイル監視ループ"""
        processed_files = set()
        
        while self.monitoring:
            try:
                # レスポンスファイル監視
                responses_dir = self.base_dir / 'responses'
                if responses_dir.exists():
                    for response_file in responses_dir.glob('*.json'):
                        if response_file.name not in processed_files:
                            try:
                                with open(response_file, 'r') as f:
                                    response_data = json.load(f)
                                
                                self.test_results.append({
                                    'request_id': response_data.get('request_id'),
                                    'status': 'success',
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                processed_files.add(response_file.name)
                                self.log_message(f"✅ レスポンス受信: {response_data.get('request_id')}")
                                self.update_stats()
                                
                            except Exception as e:
                                self.log_message(f"❌ レスポンス読み取りエラー: {e}", "ERROR")
                
                # 失敗ファイル監視
                failed_dir = self.base_dir / 'failed'
                if failed_dir.exists():
                    for failed_file in failed_dir.glob('*.json'):
                        if failed_file.name not in processed_files:
                            try:
                                with open(failed_file, 'r') as f:
                                    failed_data = json.load(f)
                                
                                self.test_results.append({
                                    'request_id': failed_data.get('request_id'),
                                    'status': 'failed',
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                processed_files.add(failed_file.name)
                                self.log_message(f"❌ リクエスト失敗: {failed_data.get('request_id')}", "WARNING")
                                self.update_stats()
                                
                            except Exception as e:
                                self.log_message(f"❌ 失敗ファイル読み取りエラー: {e}", "ERROR")
                
                time.sleep(2)  # 2秒間隔で監視
                
            except Exception as e:
                self.log_message(f"❌ 監視エラー: {e}", "ERROR")
                time.sleep(5)
    
    def start_automated_test(self):
        """自動テスト開始"""
        self.log_message("🚀 自動総合テストを開始します...")
        self.status_var.set("🚀 自動テスト実行中...")
        
        # バックグラウンドで自動テスト実行
        test_thread = threading.Thread(target=self.run_automated_test, daemon=True)
        test_thread.start()
    
    def run_automated_test(self):
        """自動テスト実行（バックグラウンド）"""
        try:
            result = subprocess.run([
                'python3', '/home/jinno/copilot-instruction-eval/automated_comprehensive_test.py'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.log_message("✅ 自動テスト完了")
                self.status_var.set("✅ 自動テスト完了")
            else:
                self.log_message(f"❌ 自動テスト失敗: {result.stderr}", "ERROR")
                self.status_var.set("❌ 自動テスト失敗")
                
        except subprocess.TimeoutExpired:
            self.log_message("⏰ 自動テストタイムアウト", "WARNING")
            self.status_var.set("⏰ テストタイムアウト")
        except Exception as e:
            self.log_message(f"❌ 自動テスト実行エラー: {e}", "ERROR")
            self.status_var.set("❌ テスト実行エラー")
    
    def reprocess_failed(self):
        """失敗リクエスト再処理"""
        self.log_message("🔄 失敗リクエストの再処理を開始...")
        
        try:
            failed_dir = self.base_dir / 'failed'
            if not failed_dir.exists():
                self.log_message("📁 失敗ディレクトリが存在しません")
                return
            
            failed_files = list(failed_dir.glob('*.json'))
            if not failed_files:
                self.log_message("📄 再処理対象のファイルがありません")
                return
            
            requests_dir = self.base_dir / 'requests'
            requests_dir.mkdir(exist_ok=True)
            
            reprocessed_count = 0
            for failed_file in failed_files:
                try:
                    # ファイルをrequestsディレクトリに移動
                    target_file = requests_dir / failed_file.name
                    failed_file.rename(target_file)
                    reprocessed_count += 1
                    self.log_message(f"♻️ 再処理: {failed_file.name}")
                except Exception as e:
                    self.log_message(f"❌ 再処理失敗: {failed_file.name} - {e}", "ERROR")
            
            self.log_message(f"✅ {reprocessed_count}件のリクエストを再処理しました")
            
        except Exception as e:
            self.log_message(f"❌ 再処理エラー: {e}", "ERROR")
    
    def open_vscode_monitor(self):
        """VSCode Activity Monitor開く"""
        try:
            # VSCodeでActivity Monitorを開く
            subprocess.run(['code', '--command', 'workbench.view.extension.copilot-automation'], 
                          timeout=10)
            self.log_message("📱 VSCode Activity Monitorを開きました")
        except Exception as e:
            self.log_message(f"❌ VSCode Monitor起動エラー: {e}", "ERROR")
    
    def send_feedback(self):
        """フィードバック送信"""
        feedback = self.feedback_entry.get().strip()
        if not feedback:
            return
        
        self.log_message(f"💬 フィードバック: {feedback}")
        
        # フィードバックファイル保存
        try:
            feedback_file = self.base_dir / 'logs' / f"feedback_{int(time.time())}.json"
            feedback_data = {
                'timestamp': datetime.now().isoformat(),
                'feedback': feedback,
                'source': 'gui_monitor'
            }
            
            with open(feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
            
            self.log_message("📤 フィードバックを保存しました")
            self.feedback_entry.delete(0, tk.END)
            
        except Exception as e:
            self.log_message(f"❌ フィードバック保存エラー: {e}", "ERROR")
    
    def process_all_feedback(self):
        """全フィードバックの処理・反映"""
        try:
            feedback_files = list((self.base_dir / 'logs').glob('feedback_*.json'))
            
            if not feedback_files:
                self.log_message("📝 処理対象のフィードバックがありません")
                return
            
            self.log_message(f"🔄 {len(feedback_files)}件のフィードバックを処理中...")
            
            processed_feedback = []
            for feedback_file in feedback_files:
                try:
                    with open(feedback_file, 'r') as f:
                        feedback_data = json.load(f)
                    
                    processed_feedback.append({
                        'timestamp': feedback_data.get('timestamp'),
                        'feedback': feedback_data.get('feedback'),
                        'source': feedback_data.get('source'),
                        'file': feedback_file.name
                    })
                    
                    self.log_message(f"📋 フィードバック処理: {feedback_data.get('feedback')[:50]}...")
                    
                except Exception as e:
                    self.log_message(f"❌ フィードバック読み取りエラー: {feedback_file.name} - {e}", "ERROR")
            
            # フィードバック統合レポート生成
            feedback_report = {
                'timestamp': datetime.now().isoformat(),
                'total_feedback_count': len(processed_feedback),
                'feedback_items': processed_feedback,
                'processing_status': 'completed'
            }
            
            feedback_report_file = self.base_dir / 'logs' / f"feedback_report_{int(time.time())}.json"
            with open(feedback_report_file, 'w') as f:
                json.dump(feedback_report, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"✅ フィードバック統合レポート生成: {feedback_report_file}")
            self.log_message(f"📊 処理完了: {len(processed_feedback)}件のフィードバックを反映")
            
            # フィードバックに基づく改善提案生成
            self.generate_improvement_suggestions(processed_feedback)
            
        except Exception as e:
            self.log_message(f"❌ フィードバック処理エラー: {e}", "ERROR")
    
    def generate_improvement_suggestions(self, feedback_items: List[Dict]):
        """フィードバックに基づく改善提案生成"""
        try:
            suggestions = []
            
            for item in feedback_items:
                feedback_text = item.get('feedback', '').lower()
                
                # フィードバック内容に基づく改善提案
                if 'エラー' in feedback_text or 'error' in feedback_text:
                    suggestions.append("エラーハンドリングの強化が必要")
                
                if '遅い' in feedback_text or 'slow' in feedback_text:
                    suggestions.append("処理速度の最適化が必要")
                
                if 'ui' in feedback_text or 'インターフェース' in feedback_text:
                    suggestions.append("ユーザーインターフェースの改善が必要")
                
                if 'ログ' in feedback_text or 'log' in feedback_text:
                    suggestions.append("ログ機能の拡張が必要")
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            
            if unique_suggestions:
                self.log_message("💡 フィードバックに基づく改善提案:")
                for i, suggestion in enumerate(unique_suggestions, 1):
                    self.log_message(f"   {i}. {suggestion}")
            else:
                self.log_message("💡 フィードバックから具体的な改善提案は抽出されませんでした")
            
            # 改善提案レポート保存
            suggestions_report = {
                'timestamp': datetime.now().isoformat(),
                'feedback_count': len(feedback_items),
                'suggestions': unique_suggestions,
                'raw_feedback': [item.get('feedback') for item in feedback_items]
            }
            
            suggestions_file = self.base_dir / 'logs' / f"improvement_suggestions_{int(time.time())}.json"
            with open(suggestions_file, 'w') as f:
                json.dump(suggestions_report, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"📋 改善提案レポート保存: {suggestions_file}")
            
        except Exception as e:
            self.log_message(f"❌ 改善提案生成エラー: {e}", "ERROR")
    
    def complete_test(self):
        """テスト完了"""
        # フィードバック受信チェック
        feedback_files = list((self.base_dir / 'logs').glob('feedback_*.json'))
        
        if not feedback_files:
            result = messagebox.askyesno(
                "⚠️ フィードバック未受信", 
                "まだフィードバックが入力されていません。\n" +
                "フィードバックなしでテストを完了しますか？\n\n" +
                "推奨: 下部のフィードバック欄に何か入力してから完了してください。"
            )
            if not result:
                self.log_message("⏸️ テスト完了をキャンセル - フィードバック入力待ち")
                self.status_var.set("💬 フィードバック入力をお待ちしています...")
                # フィードバック欄にフォーカス
                self.feedback_entry.focus_set()
                return
        
        # フィードバック受信済みの場合
        self.log_message("✅ テスト完了シグナル受信")
        self.status_var.set("✅ テスト完了")
        
        # 最終レポート生成
        self.generate_final_report()
        
        # フィードバック反映処理
        self.process_all_feedback()
        
        # 10秒後にGUI閉じる（フィードバック確認時間）
        self.log_message("⏰ 10秒後に自動終了します...")
        self.root.after(10000, self.root.quit)
    
    def generate_final_report(self):
        """最終レポート生成"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'test_results': self.test_results,
                'summary': {
                    'total': len(self.test_results),
                    'success': len([r for r in self.test_results if r.get('status') == 'success']),
                    'failed': len([r for r in self.test_results if r.get('status') == 'failed'])
                }
            }
            
            report_file = self.base_dir / 'logs' / f"gui_test_report_{int(time.time())}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.log_message(f"📊 最終レポート生成: {report_file}")
            
        except Exception as e:
            self.log_message(f"❌ レポート生成エラー: {e}", "ERROR")
    
    def run(self):
        """GUI実行"""
        self.log_message("🖥️ GUI テストモニター起動完了")
        self.log_message("👆 上部のボタンでテストを開始してください")
        self.log_message("💬 下部でフィードバックを入力できます")
        
        try:
            self.root.mainloop()
        finally:
            self.monitoring = False

def main():
    """メイン実行"""
    print("🖥️ GUI テストモニター起動中...")
    
    gui = CopilotTestGUI()
    gui.run()
    
    print("👋 GUI テストモニター終了")

if __name__ == "__main__":
    main()
