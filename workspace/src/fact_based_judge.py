#!/usr/bin/env python3
"""
事実ベース判定エンジン

このモジュールは客観的事実に基づいて成功/失敗を厳密に判定し、
偽陽性を完全に排除します。
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from vscode_process_manager import VSCodeStatus, VSCodeProcessManager
from extension_communicator import CommunicationStatus, ExtensionCommunicator
from copilot_verifier import CopilotResponse, CopilotVerifier

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JudgmentResult(Enum):
    """判定結果"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    SYSTEM_ERROR = "system_error"

@dataclass
class FactBasedEvidence:
    """事実ベース証拠データ"""
    vscode_running: bool
    extension_active: bool
    communication_established: bool
    copilot_responded: bool
    response_authentic: bool
    execution_time: float
    timestamp: str
    evidence_details: Dict[str, Any]

@dataclass
class JudgmentDecision:
    """判定決定"""
    result: JudgmentResult
    confidence: float  # 0.0-1.0
    evidence: FactBasedEvidence
    reasoning: List[str]
    recommendations: List[str]

class FactBasedJudge:
    """事実ベース判定エンジンクラス"""
    
    def __init__(self, workspace_path: str = "/home/jinno/copilot-instruction-eval"):
        self.workspace_path = workspace_path
        self.vscode_manager = VSCodeProcessManager(workspace_path)
        self.communicator = ExtensionCommunicator(workspace_path)
        self.verifier = CopilotVerifier(workspace_path)
        
        # 判定基準
        self.success_criteria = {
            "vscode_required": True,
            "extension_required": True,
            "communication_required": True,
            "authentic_response_required": True,
            "min_response_length": 20,
            "max_execution_time": 120  # seconds
        }
    
    def _collect_vscode_evidence(self) -> Tuple[VSCodeStatus, Dict[str, Any]]:
        """VSCode関連の証拠収集"""
        logger.info("🔍 Collecting VSCode evidence...")
        
        vscode_status = self.vscode_manager.get_vscode_status()
        
        evidence = {
            "process_running": vscode_status.is_running,
            "process_id": vscode_status.process_id,
            "executable_found": vscode_status.executable_path is not None,
            "workspace_open": vscode_status.workspace_path is not None,
            "extensions_loaded": vscode_status.extensions_loaded,
            "copilot_extension_active": vscode_status.copilot_extension_active,
            "check_timestamp": time.time()
        }
        
        logger.info(f"📊 VSCode Evidence: Running={evidence['process_running']}, Extensions={evidence['extensions_loaded']}")
        return vscode_status, evidence
    
    def _collect_communication_evidence(self) -> Tuple[CommunicationStatus, Dict[str, Any]]:
        """通信関連の証拠収集"""
        logger.info("🔍 Collecting communication evidence...")
        
        comm_status = self.communicator.get_communication_status()
        
        # 実際の通信テスト
        heartbeat_success = self.communicator.send_heartbeat()
        alive_check = self.communicator.check_extension_alive(timeout=5)
        
        evidence = {
            "connection_established": comm_status.connection_established,
            "handshake_successful": comm_status.handshake_successful,
            "heartbeat_success": heartbeat_success,
            "extension_alive": alive_check,
            "extension_version": comm_status.extension_version,
            "last_heartbeat": comm_status.last_heartbeat,
            "command_queue_active": comm_status.command_queue_active,
            "check_timestamp": time.time()
        }
        
        logger.info(f"📊 Communication Evidence: Connected={evidence['connection_established']}, Alive={evidence['extension_alive']}")
        return comm_status, evidence
    
    def _collect_copilot_evidence(self, instruction_id: str, instruction_text: str = "") -> Tuple[CopilotResponse, Dict[str, Any]]:
        """Copilot関連の証拠収集"""
        logger.info(f"🔍 Collecting Copilot evidence for: {instruction_id}")
        
        copilot_response = self.verifier.verify_copilot_response(instruction_id, instruction_text, timeout=30)
        
        evidence = {
            "response_received": copilot_response.success,
            "response_authentic": not copilot_response.is_mock,
            "response_length": copilot_response.response_length,
            "execution_time": copilot_response.execution_time,
            "model_used": copilot_response.model,
            "verification_hash": copilot_response.verification_hash,
            "error_message": copilot_response.error_message,
            "check_timestamp": time.time()
        }
        
        logger.info(f"📊 Copilot Evidence: Received={evidence['response_received']}, Authentic={evidence['response_authentic']}, Length={evidence['response_length']}")
        return copilot_response, evidence
    
    def _analyze_system_health(self) -> Dict[str, Any]:
        """システム全体の健全性分析"""
        logger.info("🔍 Analyzing system health...")
        
        health = {
            "overall_status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "performance_metrics": {}
        }
        
        # VSCode健全性
        vscode_status, _ = self._collect_vscode_evidence()
        if not vscode_status.is_running:
            health["critical_issues"].append("VSCode Desktop not running")
        elif not vscode_status.extensions_loaded:
            health["critical_issues"].append("VSCode extensions not loaded")
        
        # 通信健全性
        comm_status, comm_evidence = self._collect_communication_evidence()
        if not comm_evidence["extension_alive"]:
            health["critical_issues"].append("Extension not responding")
        elif not comm_evidence["heartbeat_success"]:
            health["warnings"].append("Heartbeat communication issues")
        
        # 全体判定
        if not health["critical_issues"]:
            health["overall_status"] = "healthy"
        elif len(health["critical_issues"]) < 2:
            health["overall_status"] = "degraded"
        else:
            health["overall_status"] = "critical"
        
        logger.info(f"🏥 System Health: {health['overall_status']} ({len(health['critical_issues'])} critical issues)")
        return health
    
    def judge_instruction_execution(self, instruction_id: str, instruction_text: str = "") -> JudgmentDecision:
        """指示実行の事実ベース判定"""
        logger.info(f"⚖️ Judging instruction execution: {instruction_id}")
        
        start_time = time.time()
        reasoning = []
        recommendations = []
        
        # 証拠収集
        vscode_status, vscode_evidence = self._collect_vscode_evidence()
        comm_status, comm_evidence = self._collect_communication_evidence()
        copilot_response, copilot_evidence = self._collect_copilot_evidence(instruction_id, instruction_text)
        
        # 事実ベース証拠統合
        evidence = FactBasedEvidence(
            vscode_running=vscode_evidence["process_running"],
            extension_active=vscode_evidence["extensions_loaded"],
            communication_established=comm_evidence["connection_established"],
            copilot_responded=copilot_evidence["response_received"],
            response_authentic=copilot_evidence["response_authentic"],
            execution_time=time.time() - start_time,
            timestamp=datetime.now().isoformat(),
            evidence_details={
                "vscode": vscode_evidence,
                "communication": comm_evidence,
                "copilot": copilot_evidence
            }
        )
        
        # 判定ロジック
        confidence = 1.0
        
        # 必須条件チェック
        if not evidence.vscode_running:
            reasoning.append("❌ CRITICAL: VSCode Desktop not running")
            recommendations.append("Start VSCode Desktop with the workspace")
            confidence = 0.0
            result = JudgmentResult.SYSTEM_ERROR
        
        elif not evidence.extension_active:
            reasoning.append("❌ CRITICAL: VSCode extension not active")
            recommendations.append("Install and activate the Copilot automation extension")
            confidence = 0.0
            result = JudgmentResult.SYSTEM_ERROR
        
        elif not evidence.communication_established:
            reasoning.append("❌ CRITICAL: Communication with extension failed")
            recommendations.append("Check extension installation and restart VSCode")
            confidence = 0.0
            result = JudgmentResult.FAILURE
        
        elif not evidence.copilot_responded:
            reasoning.append("❌ FAILURE: No Copilot response received")
            recommendations.append("Check Copilot authentication and network connectivity")
            confidence = 0.8
            result = JudgmentResult.FAILURE
        
        elif not evidence.response_authentic:
            reasoning.append("❌ FAILURE: Response appears to be mock/fake")
            recommendations.append("Verify actual Copilot communication and response generation")
            confidence = 0.9
            result = JudgmentResult.FAILURE
        
        else:
            # 成功条件の詳細チェック
            success_factors = []
            
            if evidence.vscode_running:
                success_factors.append("✅ VSCode Desktop running")
            if evidence.extension_active:
                success_factors.append("✅ Extension active")
            if evidence.communication_established:
                success_factors.append("✅ Communication established")
            if evidence.copilot_responded:
                success_factors.append("✅ Copilot responded")
            if evidence.response_authentic:
                success_factors.append("✅ Response authentic")
            
            reasoning.extend(success_factors)
            
            # 品質チェック
            response_length = copilot_evidence["response_length"]
            if response_length < self.success_criteria["min_response_length"]:
                reasoning.append(f"⚠️ Response length below threshold ({response_length} chars)")
                confidence *= 0.8
                result = JudgmentResult.PARTIAL_SUCCESS
            else:
                reasoning.append(f"✅ Response length adequate ({response_length} chars)")
                result = JudgmentResult.SUCCESS
            
            # 実行時間チェック
            if evidence.execution_time > self.success_criteria["max_execution_time"]:
                reasoning.append(f"⚠️ Execution time excessive ({evidence.execution_time:.1f}s)")
                confidence *= 0.9
            else:
                reasoning.append(f"✅ Execution time acceptable ({evidence.execution_time:.1f}s)")
        
        # 最終判定
        decision = JudgmentDecision(
            result=result,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            recommendations=recommendations
        )
        
        logger.info(f"⚖️ Judgment: {result.value} (confidence: {confidence:.2f})")
        for reason in reasoning:
            logger.info(f"  {reason}")
        
        return decision
    
    def batch_judge_executions(self, instruction_data: List[Dict[str, str]]) -> List[JudgmentDecision]:
        """複数指示実行の一括判定"""
        logger.info(f"⚖️ Batch judging {len(instruction_data)} instruction executions...")
        
        decisions = []
        
        # システム健全性事前チェック
        system_health = self._analyze_system_health()
        if system_health["overall_status"] == "critical":
            logger.error("🚨 System health critical - aborting batch judgment")
            # 全て失敗として処理
            for instruction in instruction_data:
                decision = JudgmentDecision(
                    result=JudgmentResult.SYSTEM_ERROR,
                    confidence=0.0,
                    evidence=FactBasedEvidence(
                        vscode_running=False,
                        extension_active=False,
                        communication_established=False,
                        copilot_responded=False,
                        response_authentic=False,
                        execution_time=0.0,
                        timestamp=datetime.now().isoformat(),
                        evidence_details={"system_health": system_health}
                    ),
                    reasoning=["🚨 System health critical"] + system_health["critical_issues"],
                    recommendations=["Fix critical system issues before retrying"]
                )
                decisions.append(decision)
            return decisions
        
        # 個別判定実行
        for i, instruction in enumerate(instruction_data):
            instruction_id = instruction.get("id", f"unknown_{i}")
            instruction_text = instruction.get("description", "")
            
            decision = self.judge_instruction_execution(instruction_id, instruction_text)
            decisions.append(decision)
            
            # 進捗ログ
            success_count = sum(1 for d in decisions if d.result == JudgmentResult.SUCCESS)
            logger.info(f"📊 Batch Progress: {len(decisions)}/{len(instruction_data)} ({success_count} successful)")
        
        return decisions
    
    def generate_judgment_report(self, decisions: List[JudgmentDecision]) -> Dict[str, Any]:
        """判定レポート生成"""
        if not decisions:
            return {"error": "No decisions to report"}
        
        # 統計計算
        total = len(decisions)
        successful = sum(1 for d in decisions if d.result == JudgmentResult.SUCCESS)
        failed = sum(1 for d in decisions if d.result == JudgmentResult.FAILURE)
        partial = sum(1 for d in decisions if d.result == JudgmentResult.PARTIAL_SUCCESS)
        errors = sum(1 for d in decisions if d.result == JudgmentResult.SYSTEM_ERROR)
        
        avg_confidence = sum(d.confidence for d in decisions) / total
        avg_execution_time = sum(d.evidence.execution_time for d in decisions) / total
        
        # 共通問題分析
        all_issues = []
        for decision in decisions:
            all_issues.extend([r for r in decision.reasoning if r.startswith("❌")])
        
        common_issues = {}
        for issue in all_issues:
            common_issues[issue] = common_issues.get(issue, 0) + 1
        
        report = {
            "summary": {
                "total_instructions": total,
                "successful": successful,
                "failed": failed,
                "partial_success": partial,
                "system_errors": errors,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "average_confidence": avg_confidence,
                "average_execution_time": avg_execution_time
            },
            "common_issues": dict(sorted(common_issues.items(), key=lambda x: x[1], reverse=True)),
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 推奨事項生成
        if errors > 0:
            report["recommendations"].append("Fix system-level issues (VSCode, extensions)")
        if failed > successful:
            report["recommendations"].append("Check Copilot authentication and connectivity")
        if avg_confidence < 0.8:
            report["recommendations"].append("Investigate response quality issues")
        
        return report

def main():
    """テスト実行"""
    judge = FactBasedJudge()
    
    print("=== Fact-Based Judge Test ===")
    
    # システム健全性チェック
    health = judge._analyze_system_health()
    print(f"System health: {health['overall_status']}")
    
    # 単一判定テスト（コメントアウト）
    # decision = judge.judge_instruction_execution("test_001", "Test instruction")
    # print(f"Judgment: {decision.result.value} (confidence: {decision.confidence:.2f})")

if __name__ == "__main__":
    main()
