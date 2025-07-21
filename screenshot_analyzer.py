#!/usr/bin/env python3
"""
Screenshot Analysis Tool
スクリーンショットを表示・分析するツール
"""

import cv2
import numpy as np
from pathlib import Path
import sys

def display_screenshot(image_path):
    """スクリーンショットを表示"""
    try:
        print(f"📸 Analyzing screenshot: {image_path}")
        
        # 画像を読み込み
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"❌ Failed to load image: {image_path}")
            return False
        
        # 画像情報を表示
        height, width, channels = img.shape
        print(f"📏 Image dimensions: {width}x{height} ({channels} channels)")
        
        # ウィンドウサイズを調整
        display_width = min(1200, width)
        display_height = int(height * (display_width / width))
        
        # リサイズ
        resized = cv2.resize(img, (display_width, display_height))
        
        # ウィンドウを作成して表示
        window_name = f"Screenshot Analysis - {Path(image_path).name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, resized)
        
        print(f"🖼️  Screenshot displayed in window: {window_name}")
        print("Press any key to continue to next screenshot...")
        
        # キー入力待ち
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return True
        
    except Exception as e:
        print(f"❌ Error displaying screenshot: {e}")
        return False

def analyze_latest_autonomous_screenshots():
    """最新の自動化スクリーンショットを分析"""
    log_dir = Path("evaluation_logs")
    
    # 最新の自動化スクリーンショットを検索
    pattern = "autonomous_*20250720_113*.png"
    screenshots = sorted(log_dir.glob(pattern))
    
    if not screenshots:
        print("❌ No autonomous screenshots found")
        return
    
    print(f"🔍 Found {len(screenshots)} screenshots to analyze:")
    for screenshot in screenshots:
        print(f"  - {screenshot.name}")
    
    print("\n" + "="*60)
    print("📸 SCREENSHOT ANALYSIS SESSION")
    print("="*60)
    
    for i, screenshot in enumerate(screenshots, 1):
        print(f"\n🔍 [{i}/{len(screenshots)}] Analyzing: {screenshot.name}")
        
        if not display_screenshot(screenshot):
            continue
        
        # ユーザーに分析結果を聞く
        print(f"\n❓ What do you see in this screenshot?")
        print("   - Is VSCode visible?")
        print("   - Is Copilot chat panel open?")
        print("   - Is there any prompt text visible?")
        print("   - What is the main content of the screen?")
        
        response = input("📝 Your analysis (or 'skip' to continue): ").strip()
        if response.lower() != 'skip':
            print(f"✅ User analysis recorded: {response}")
    
    print("\n" + "="*60)
    print("🎯 SCREENSHOT ANALYSIS COMPLETED")
    print("="*60)

def main():
    """メイン実行"""
    if len(sys.argv) > 1:
        # 特定のスクリーンショットを分析
        image_path = sys.argv[1]
        display_screenshot(image_path)
    else:
        # 最新の自動化スクリーンショットを分析
        analyze_latest_autonomous_screenshots()

if __name__ == "__main__":
    main()
