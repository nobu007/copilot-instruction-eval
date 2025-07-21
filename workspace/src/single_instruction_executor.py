#!/usr/bin/env python3
"""
単一指示実行テスト

1件のCopilot処理を正しく実行できるかE2E検証を行います。
"""

import sys
import os
import json
import time
import logging
from pathlib import Path

# 現在のディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from true_e2e_executor import TrueE2EExecutor
from vscode_process_manager import VSCodeProcessManager
from extension_communicator import ExtensionCommunicator
from fact_based_judge import FactBasedJudge

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """単一指示のE2E検証実行"""
    print("🎯 Starting Single Instruction E2E Verification")
    print("=" * 60)
    
    # 1. システム初期化
    workspace_path = "/home/jinno/copilot-instruction-eval"
    executor = TrueE2EExecutor(workspace_path)
    
    # 2. テスト指示読み込み
    test_file = Path(workspace_path) / "workspace" / "single_instruction_test.json"
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        instructions = test_data.get('instructions', [])
        if not instructions:
            print("❌ No test instructions found")
            return False
        
        instruction = instructions[0]
        print(f"📝 Test Instruction: {instruction['id']}")
        print(f"📋 Description: {instruction['description'][:100]}...")
        
    except Exception as e:
        print(f"❌ Failed to load test instruction: {e}")
        return False
    
    # 3. システム準備状態確認
    print("\n🔍 Step 1: System Readiness Check")
    print("-" * 40)
    
    ready, message = executor._ensure_system_ready()
    if not ready:
        print(f"❌ System not ready: {message}")
        return False
    
    print("✅ System is ready for execution")
    
    # 4. 単一指示実行
    print("\n🚀 Step 2: Single Instruction Execution")
    print("-" * 40)
    
    start_time = time.time()
    result = executor.execute_single_instruction(instruction)
    execution_time = time.time() - start_time
    
    # 5. 結果分析
    print("\n📊 Step 3: Result Analysis")
    print("-" * 40)
    
    print(f"Instruction ID: {result.instruction_id}")
    print(f"Judgment: {result.judgment.value}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Execution Time: {execution_time:.2f}s")
    
    print(f"\nVerification Status:")
    print(f"  VSCode Verified: {'✅' if result.vscode_verified else '❌'}")
    print(f"  Extension Verified: {'✅' if result.extension_verified else '❌'}")
    print(f"  Copilot Verified: {'✅' if result.copilot_verified else '❌'}")
    print(f"  Response Authentic: {'✅' if result.response_authentic else '❌'}")
    
    if result.response_content:
        print(f"\nResponse Content ({len(result.response_content)} chars):")
        print("-" * 40)
        print(result.response_content[:500] + ("..." if len(result.response_content) > 500 else ""))
    
    if result.error_message:
        print(f"\nError Message:")
        print("-" * 40)
        print(result.error_message)
    
    # 6. 最終判定
    print("\n🏁 Step 4: Final Assessment")
    print("-" * 40)
    
    success = (
        result.judgment.value == "success" and
        result.vscode_verified and
        result.extension_verified and
        result.copilot_verified and
        result.response_authentic and
        result.confidence >= 0.8
    )
    
    if success:
        print("🎉 SUCCESS: Single instruction E2E verification PASSED")
        print("✅ All systems functioning correctly")
        print("✅ Copilot processing verified")
        print("✅ No false positives detected")
    else:
        print("❌ FAILURE: Single instruction E2E verification FAILED")
        print("🔍 Issues detected:")
        
        if not result.vscode_verified:
            print("  - VSCode not properly verified")
        if not result.extension_verified:
            print("  - Extension not properly verified")
        if not result.copilot_verified:
            print("  - Copilot not properly verified")
        if not result.response_authentic:
            print("  - Response authenticity failed")
        if result.confidence < 0.8:
            print(f"  - Low confidence: {result.confidence:.2f}")
    
    print("\n" + "=" * 60)
    print(f"E2E Verification Complete: {'SUCCESS' if success else 'FAILURE'}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
