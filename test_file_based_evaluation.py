#!/usr/bin/env python3
"""
File-based Evaluation System Test Script

ファイルベース評価システムのテスト実行スクリプト
"""

import time
from file_based_evaluation_client import FileBasedEvaluationClient, TestCase

def main():
    print("🚀 File-based Copilot Evaluation System Test")
    print("=" * 50)
    
    # クライアント初期化
    client = FileBasedEvaluationClient()
    
    # レスポンス監視開始
    client.start_monitoring()
    
    try:
        # ステータス確認
        status = client.get_status()
        print(f"📊 System Status:")
        print(f"  Base directory: {status['base_directory']}")
        print(f"  Monitoring active: {status['monitoring_active']}")
        print(f"  Directories created: ✅")
        
        # 簡単なテストケース
        test_cases = [
            TestCase(
                test_id="simple_test_001",
                prompt="Write a simple Python hello world function",
                category="basic_code",
                expected_elements=["def", "hello", "print"],
                description="Simple hello world function test"
            ),
            TestCase(
                test_id="simple_test_002", 
                prompt="Create a function that adds two numbers",
                category="basic_code",
                expected_elements=["def", "add", "return"],
                description="Simple addition function test"
            )
        ]
        
        print(f"\n🧪 Running {len(test_cases)} test cases...")
        
        # 評価実行
        results = client.run_batch_evaluation(
            test_cases=test_cases,
            models=["copilot/gpt-4"],  # 1つのモデルでテスト
            modes=["agent"]           # 1つのモードでテスト
        )
        
        # 結果表示
        print(f"\n📊 Test Results:")
        print(f"Total tests: {results['summary']['total_tests']}")
        print(f"Successful tests: {results['summary']['successful_tests']}")
        print(f"Success rate: {results['summary']['success_rate']:.2%}")
        
        if results['results']:
            print(f"\n📝 Individual Results:")
            for result in results['results']:
                status_icon = "✅" if result['success'] else "❌"
                print(f"  {status_icon} {result['test_id']}: {result['execution_time']:.2f}s")
                if result['error_message']:
                    print(f"    Error: {result['error_message']}")
                else:
                    print(f"    Response preview: {result['response_preview'][:100]}...")
        
        print(f"\n💾 Results saved to: {client.results_dir}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    finally:
        # クリーンアップ
        client.stop_monitoring()
        print(f"\n🛑 Test completed")

if __name__ == "__main__":
    main()
