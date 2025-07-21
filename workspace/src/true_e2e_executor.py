#!/usr/bin/env python3
"""
真のE2E実行エンジン

このモジュールは偽陽性を完全に排除した真のエンドツーエンド実行システムです。
事実ベースの検証により、確実な動作確認を行います。
"""

import os
import json
import time
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# 依存コンポーネントのインポート
from vscode_process_manager import VSCodeProcessManager
from extension_communicator import ExtensionCommunicator
from copilot_verifier import CopilotVerifier
from fact_based_judge import FactBasedJudge, JudgmentResult

# ログ設定
TRACE_REPORT_PATH = Path('/home/jinno/copilot-instruction-eval/workspace/true_e2e_execution_trace.md')

# Clear previous trace report
if TRACE_REPORT_PATH.exists():
    TRACE_REPORT_PATH.unlink()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(TRACE_REPORT_PATH) # Add markdown trace logger
    ]
)

# Add a header to the trace report
with open(TRACE_REPORT_PATH, 'a', encoding='utf-8') as f:
    f.write(f"""# True E2E Execution Trace\n\n*Execution started at: {datetime.now().isoformat()}*\n\n""")
logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """実行結果データクラス"""
    instruction_id: str
    instruction_description: str
    judgment: JudgmentResult
    confidence: float
    execution_time: float
    vscode_verified: bool
    extension_verified: bool
    copilot_verified: bool
    response_authentic: bool
    response_content: str
    error_message: Optional[str]
    timestamp: str
    evidence_hash: str

class TrueE2EExecutor:
    """真のE2E実行エンジンクラス"""
    
    def __init__(self, 
                 vscode_manager: VSCodeProcessManager,
                 communicator: ExtensionCommunicator,
                 verifier: CopilotVerifier,
                 judge: FactBasedJudge,
                 workspace_path: str = "/home/jinno/copilot-instruction-eval"):
        self.workspace_path = workspace_path
        self.db_path = Path(workspace_path) / "workspace" / "true_e2e_execution.db"
        self.report_path = Path(workspace_path) / "workspace" / "true_e2e_execution_report.md"
        
        # 依存性注入 (Dependency Injection)
        self.vscode_manager = vscode_manager
        self.communicator = communicator
        self.verifier = verifier
        self.judge = judge
        
        # データベース初期化
        self._init_database()
        
    def _init_database(self):
        """データベース初期化"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instruction_id TEXT NOT NULL,
                        instruction_description TEXT,
                        judgment TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        execution_time REAL NOT NULL,
                        vscode_verified BOOLEAN NOT NULL,
                        extension_verified BOOLEAN NOT NULL,
                        copilot_verified BOOLEAN NOT NULL,
                        response_authentic BOOLEAN NOT NULL,
                        response_content TEXT,
                        error_message TEXT,
                        timestamp TEXT NOT NULL,
                        evidence_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        check_timestamp TEXT NOT NULL,
                        vscode_status TEXT NOT NULL,
                        communication_status TEXT NOT NULL,
                        overall_health TEXT NOT NULL,
                        critical_issues TEXT,
                        warnings TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("✅ Database initialized")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def _save_execution_result(self, result: ExecutionResult):
        """実行結果をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO executions (
                        instruction_id, instruction_description, judgment, confidence,
                        execution_time, vscode_verified, extension_verified, 
                        copilot_verified, response_authentic, response_content,
                        error_message, timestamp, evidence_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.instruction_id,
                    result.instruction_description,
                    result.judgment.value,
                    result.confidence,
                    result.execution_time,
                    result.vscode_verified,
                    result.extension_verified,
                    result.copilot_verified,
                    result.response_authentic,
                    result.response_content,
                    result.error_message,
                    result.timestamp,
                    result.evidence_hash
                ))
                conn.commit()
                logger.debug(f"💾 Saved execution result: {result.instruction_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to save execution result: {e}")
    
    def _load_instructions(self, instructions_file: str = "instructions.json") -> List[Dict[str, Any]]:
        """指示ファイルを読み込み"""
        instructions_path = Path(self.workspace_path) / instructions_file
        
        try:
            with open(instructions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            instructions = data.get('instructions', [])
            logger.info(f"📖 Loaded {len(instructions)} instructions from {instructions_file}")
            return instructions
            
        except Exception as e:
            logger.error(f"❌ Failed to load instructions: {e}")
            return []
    
    def _ensure_system_ready(self) -> Tuple[bool, str]:
        """システム準備状態確認と自己修復"""
        logger.info("🔍 Ensuring system is ready with self-healing...")
        
        # 1. VSCodeの状態確認
        vscode_status = self.vscode_manager.get_vscode_status()
        
        # 2. ワークスペースの検証と自己修復
        if vscode_status.is_running and vscode_status.actual_workspace != self.workspace_path:
            logger.warning(f"Incorrect workspace detected. Expected '{self.workspace_path}', but found '{vscode_status.actual_workspace}'.")
            logger.info("🔄 Shutting down incorrect VSCode instance...")
            self.vscode_manager.stop_vscode()
            time.sleep(5) # プロセスが完全に終了するのを待つ
            vscode_status.is_running = False # ステータスを更新

        # 3. VSCodeが起動していない場合、正しいワークスペースで起動
        if not vscode_status.is_running:
            logger.info(f"🚀 Starting VSCode Desktop with workspace: {self.workspace_path}")
            success, message = self.vscode_manager.start_vscode(wait_timeout=90)
            if not success:
                return False, f"Failed to start VSCode: {message}"
        
        # 4. VSCode準備完了待機
        logger.info("⏳ Waiting for VSCode to become ready...")
        if not self.vscode_manager.wait_for_ready(timeout=120):
            return False, "VSCode did not become ready within the timeout period."
        
        # 5. 拡張機能との通信確立
        logger.info("🤝 Establishing communication with the extension...")
        comm_status = self.communicator.establish_connection()
        if not comm_status.handshake_successful:
            return False, "Failed to establish a handshake with the extension."
        
        logger.info("✅ System is ready for execution.")
        return True, "System ready"
    
    def execute_single_instruction(self, instruction: Dict[str, Any]) -> ExecutionResult:
        """単一指示の実行"""
        instruction_id = instruction.get('id', 'unknown')
        instruction_description = instruction.get('description', '')
        
        logger.info(f"🎯 Executing instruction: {instruction_id}")
        logger.info(f"📝 Description: {instruction_description[:100]}...")
        
        start_time = time.time()
        
        try:
            # 1. Copilotプロンプト送信
            success, response_data = self.communicator.send_copilot_prompt(
                prompt=instruction_description,
                mode=instruction.get('mode', 'agent'),
                model=instruction.get('model', 'copilot/gpt-4')
            )
            
            if not success:
                logger.error(f"❌ Failed to send prompt: {instruction_id}")
                # 事実ベース判定を実行して、システムエラーとして記録
                decision = self.judge.judge_instruction_execution(instruction_id, instruction_description, is_failure=True)
                return ExecutionResult(
                    instruction_id=instruction_id,
                    instruction_description=instruction_description,
                    judgment=JudgmentResult.FAILURE,
                    confidence=decision.confidence,
                    execution_time=time.time() - start_time,
                    vscode_verified=decision.evidence.vscode_running,
                    extension_verified=decision.evidence.extension_active,
                    copilot_verified=False,
                    response_authentic=False,
                    response_content="",
                    error_message="Failed to send prompt to extension",
                    timestamp=datetime.now().isoformat(),
                    evidence_hash=str(hash(str(decision.evidence.evidence_details)))
                )
            
            # 2. 事実ベース判定実行
            decision = self.judge.judge_instruction_execution(instruction_id, instruction_description)
            
            # 3. 実行結果構築
            result = ExecutionResult(
                instruction_id=instruction_id,
                instruction_description=instruction_description,
                judgment=decision.result,
                confidence=decision.confidence,
                execution_time=time.time() - start_time,
                vscode_verified=decision.evidence.vscode_running,
                extension_verified=decision.evidence.extension_active,
                copilot_verified=decision.evidence.copilot_responded,
                response_authentic=decision.evidence.response_authentic,
                response_content=decision.evidence.evidence_details.get('copilot', {}).get('response', ''),
                error_message=None if decision.result == JudgmentResult.SUCCESS else '; '.join(decision.reasoning),
                timestamp=decision.evidence.timestamp,
                evidence_hash=str(hash(str(decision.evidence.evidence_details)))
            )
            
            # 4. 結果保存
            self._save_execution_result(result)
            
            # 5. ログ出力
            status_emoji = {
                JudgmentResult.SUCCESS: "✅",
                JudgmentResult.PARTIAL_SUCCESS: "⚠️",
                JudgmentResult.FAILURE: "❌",
                JudgmentResult.SYSTEM_ERROR: "🚨"
            }.get(decision.result, "❓")
            
            logger.info(f"{status_emoji} Instruction completed: {instruction_id} ({decision.result.value}, confidence: {decision.confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Execution error for {instruction_id}: {e}", exc_info=True)
            
            return ExecutionResult(
                instruction_id=instruction_id,
                instruction_description=instruction_description,
                judgment=JudgmentResult.SYSTEM_ERROR,
                confidence=0.0,
                execution_time=time.time() - start_time,
                vscode_verified=False,
                extension_verified=False,
                copilot_verified=False,
                response_authentic=False,
                response_content="",
                error_message=f"System error: {e}",
                timestamp=datetime.now().isoformat(),
                evidence_hash=""
            )
    
    def execute_continuous(self, instructions_file: str = "instructions.json") -> List[ExecutionResult]:
        """連続実行"""
        logger.info("🚀 Starting TRUE E2E continuous execution...")
        
        # システム準備
        ready, message = self._ensure_system_ready()
        if not ready:
            logger.error(f"🚨 System not ready: {message}")
            return []
        
        # 指示読み込み
        instructions = self._load_instructions(instructions_file)
        if not instructions:
            logger.error("❌ No instructions to execute")
            return []
        
        logger.info(f"📋 Executing {len(instructions)} instructions...")
        
        results = []
        try:
            for i, instruction in enumerate(instructions, 1):
                logger.info(f"\n---\n### 📊 Executing Instruction: {i}/{len(instructions)} ({instruction.get('id', 'N/A')})\n---\n")
                
                result = self.execute_single_instruction(instruction)
                results.append(result)
                
                # 進捗統計
                successful = sum(1 for r in results if r.judgment == JudgmentResult.SUCCESS)
                logger.info(f"📈 **Current success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)**")
                
                # インターバル
                if i < len(instructions):
                    time.sleep(2)
            
            logger.info("\n---\n🎉 TRUE E2E continuous execution completed!\n---")
            
        except Exception as e:
            logger.critical(f"🚨 A critical error occurred during continuous execution: {e}", exc_info=True)
        finally:
            # 最終レポート生成
            logger.info("\n---\n### 📊 Generating Final Report\n---\n")
            self._generate_report(results)
            logger.info("✅ Final report generation complete.")

        return results
    
    def _generate_report(self, results: List[ExecutionResult]):
        """実行レポート生成"""
        if not results:
            return
        
        logger.info("📊 Generating execution report...")
        
        # 統計計算
        total = len(results)
        successful = sum(1 for r in results if r.judgment == JudgmentResult.SUCCESS)
        failed = sum(1 for r in results if r.judgment == JudgmentResult.FAILURE)
        partial = sum(1 for r in results if r.judgment == JudgmentResult.PARTIAL_SUCCESS)
        errors = sum(1 for r in results if r.judgment == JudgmentResult.SYSTEM_ERROR)
        
        success_rate = (successful / total * 100) if total > 0 else 0
        avg_execution_time = sum(r.execution_time for r in results) / total if total > 0 else 0
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0
        
        # 検証統計
        vscode_verified = sum(1 for r in results if r.vscode_verified)
        extension_verified = sum(1 for r in results if r.extension_verified)
        copilot_verified = sum(1 for r in results if r.copilot_verified)
        authentic_responses = sum(1 for r in results if r.response_authentic)
        
        # レポート生成
        report_content = f"""# True E2E Execution Report

## Executive Summary
- **Total Instructions**: {total}
- **Successful**: {successful} ({success_rate:.1f}%)
- **Failed**: {failed}
- **Partial Success**: {partial}
- **System Errors**: {errors}
- **Average Execution Time**: {avg_execution_time:.2f}s
- **Average Confidence**: {avg_confidence:.2f}

## Verification Statistics
- **VSCode Verified**: {vscode_verified}/{total} ({vscode_verified/total*100:.1f}%)
- **Extension Verified**: {extension_verified}/{total} ({extension_verified/total*100:.1f}%)
- **Copilot Verified**: {copilot_verified}/{total} ({copilot_verified/total*100:.1f}%)
- **Authentic Responses**: {authentic_responses}/{total} ({authentic_responses/total*100:.1f}%)

## Detailed Results

| Instruction ID | Status | Confidence | VSCode | Extension | Copilot | Authentic | Time |
|----------------|--------|------------|--------|-----------|---------|-----------|------|
"""
        
        for result in results:
            status_emoji = {
                JudgmentResult.SUCCESS: "✅",
                JudgmentResult.PARTIAL_SUCCESS: "⚠️", 
                JudgmentResult.FAILURE: "❌",
                JudgmentResult.SYSTEM_ERROR: "🚨"
            }.get(result.judgment, "❓")
            
            report_content += f"| {result.instruction_id} | {status_emoji} {result.judgment.value} | {result.confidence:.2f} | {'✅' if result.vscode_verified else '❌'} | {'✅' if result.extension_verified else '❌'} | {'✅' if result.copilot_verified else '❌'} | {'✅' if result.response_authentic else '❌'} | {result.execution_time:.1f}s |\n"
        
        # エラー分析
        if failed > 0 or errors > 0:
            report_content += f"\n## Error Analysis\n\n"
            
            error_results = [r for r in results if r.judgment in [JudgmentResult.FAILURE, JudgmentResult.SYSTEM_ERROR]]
            for result in error_results:
                report_content += f"### {result.instruction_id}\n"
                report_content += f"- **Error**: {result.error_message}\n"
                report_content += f"- **Verification**: VSCode={result.vscode_verified}, Extension={result.extension_verified}, Copilot={result.copilot_verified}\n\n"
        
        # 推奨事項
        report_content += f"\n## Recommendations\n\n"
        if total > 0 and authentic_responses < total:
            report_content += "- **Copilot Response Authenticity**: Improve response verification to reduce mock/inauthentic responses.\n"
        if total > 0 and extension_verified < total:
            report_content += "- **Extension Communication**: Strengthen handshake and heartbeat protocol to ensure reliable communication.\n"
        if total > 0 and vscode_verified < total:
            report_content += "- **VSCode Stability**: Investigate VSCode startup or stability issues.\n"
        if total > 0 and success_rate < 100:
            report_content += "- **Instruction Prompts**: Review failed instructions and refine prompts for clarity and effectiveness.\n"
        if total > 0 and success_rate == 100:
            report_content += "- **All systems nominal.** Excellent performance and reliability observed.\n"
            
        try:
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"✅ Report generated: {self.report_path}")
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")

def main():
    """メイン実行関数"""
    logger.info("==================================================")
    logger.info("   Initializing True E2E Autonomous Testbed   ")
    logger.info("==================================================")
    
    logger.info("--- Component Initialization ---")
    workspace_path = "/home/jinno/copilot-instruction-eval"
    
    # 1. 依存コンポーネントを初期化
    vscode_manager = VSCodeProcessManager(workspace_path=workspace_path)
    communicator = ExtensionCommunicator(workspace_path=workspace_path)
    verifier = CopilotVerifier(workspace_path=workspace_path)
    judge = FactBasedJudge(workspace_path=workspace_path)
    logger.info("✅ All components initialized.")

    # 2. 依存性を注入して実行エンジンをインスタンス化
    executor = TrueE2EExecutor(
        vscode_manager=vscode_manager,
        communicator=communicator,
        verifier=verifier,
        judge=judge,
        workspace_path=workspace_path
    )
    
    # 3. 連続実行を開始
    executor.execute_continuous(instructions_file="workspace/instructions/instructions.json")

if __name__ == "__main__":
    main()
