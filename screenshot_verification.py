#!/usr/bin/env python3
"""
Screenshot Verification System
スクリーンショットからOCRでプロンプト内容を検証
"""

import cv2
import pytesseract
from PIL import Image
import logging
from pathlib import Path
import re

class ScreenshotVerifier:
    def __init__(self):
        self.logger = logging.getLogger("ScreenshotVerifier")
        logging.basicConfig(level=logging.INFO)
        
    def extract_text_from_screenshot(self, image_path):
        """スクリーンショットからテキストを抽出"""
        try:
            self.logger.info(f"Analyzing screenshot: {image_path}")
            
            # 画像を読み込み
            img = cv2.imread(str(image_path))
            if img is None:
                self.logger.error(f"Failed to load image: {image_path}")
                return ""
            
            # グレースケール変換
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # OCRでテキスト抽出
            text = pytesseract.image_to_string(gray, lang='eng+jpn')
            
            self.logger.info(f"Extracted text length: {len(text)} characters")
            return text
            
        except Exception as e:
            self.logger.error(f"Error extracting text: {e}")
            return ""
    
    def verify_prompt_in_copilot(self, image_path, expected_keywords):
        """Copilotチャットにプロンプトが表示されているか検証"""
        text = self.extract_text_from_screenshot(image_path)
        
        if not text:
            return False, "No text extracted from screenshot"
        
        # 期待するキーワードをチェック
        found_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() in text.lower():
                found_keywords.append(keyword)
        
        success_rate = len(found_keywords) / len(expected_keywords)
        
        result = {
            'success': success_rate >= 0.5,  # 50%以上のキーワードが見つかれば成功
            'success_rate': success_rate,
            'found_keywords': found_keywords,
            'missing_keywords': [k for k in expected_keywords if k not in found_keywords],
            'extracted_text': text[:500] + "..." if len(text) > 500 else text
        }
        
        return result['success'], result
    
    def analyze_autonomous_screenshots(self):
        """自律型自動化のスクリーンショットを分析"""
        log_dir = Path("evaluation_logs")
        
        # 期待するプロンプトキーワード
        expected_keywords = [
            "AUTONOMOUS AUTOMATION TEST",
            "fully autonomous",
            "VSCode Desktop automation",
            "Zero user intervention",
            "System executed at"
        ]
        
        # 分析対象のスクリーンショット
        screenshots_to_analyze = [
            "autonomous_after_autonomous_typing_20250720_111335.png",
            "autonomous_after_autonomous_send_20250720_111338.png",
            "autonomous_final_result_20250720_111338.png"
        ]
        
        results = {}
        
        for screenshot in screenshots_to_analyze:
            image_path = log_dir / screenshot
            if image_path.exists():
                self.logger.info(f"\n=== Analyzing {screenshot} ===")
                success, details = self.verify_prompt_in_copilot(image_path, expected_keywords)
                
                results[screenshot] = {
                    'success': success,
                    'details': details
                }
                
                self.logger.info(f"Success: {success}")
                self.logger.info(f"Success rate: {details['success_rate']:.2%}")
                self.logger.info(f"Found keywords: {details['found_keywords']}")
                if details['missing_keywords']:
                    self.logger.info(f"Missing keywords: {details['missing_keywords']}")
                
                # 抽出されたテキストの一部を表示
                if details['extracted_text']:
                    self.logger.info(f"Extracted text preview:\n{details['extracted_text'][:200]}...")
                
            else:
                self.logger.warning(f"Screenshot not found: {image_path}")
                results[screenshot] = {'success': False, 'details': 'File not found'}
        
        return results
    
    def generate_verification_report(self, results):
        """検証レポートを生成"""
        report = """
🔍 SCREENSHOT VERIFICATION REPORT
{'=' * 50}

OBJECTIVE: Verify if the autonomous automation actually displayed 
the prompt in VSCode Copilot chat by analyzing screenshots with OCR.

"""
        
        overall_success = False
        successful_screenshots = 0
        
        for screenshot, result in results.items():
            report += f"\n📸 {screenshot}:\n"
            
            if isinstance(result['details'], dict):
                success = result['success']
                details = result['details']
                
                report += f"  ✅ SUCCESS: {success}\n"
                report += f"  📊 Success Rate: {details['success_rate']:.2%}\n"
                report += f"  🔍 Found Keywords: {details['found_keywords']}\n"
                
                if details['missing_keywords']:
                    report += f"  ❌ Missing Keywords: {details['missing_keywords']}\n"
                
                if success:
                    successful_screenshots += 1
                    overall_success = True
                
                # 抽出テキストのサンプル
                if details['extracted_text']:
                    report += f"  📝 Text Sample: {details['extracted_text'][:100]}...\n"
                    
            else:
                report += f"  ❌ ERROR: {result['details']}\n"
        
        report += f"\n{'=' * 50}\n"
        report += f"🎯 OVERALL RESULT: {'SUCCESS' if overall_success else 'FAILED'}\n"
        report += f"📊 Successful Screenshots: {successful_screenshots}/{len(results)}\n"
        
        if overall_success:
            report += "\n✅ CONCLUSION: OCR analysis confirms that the autonomous automation\n"
            report += "successfully displayed the prompt text in VSCode Copilot chat.\n"
        else:
            report += "\n❌ CONCLUSION: OCR analysis could not confirm that the prompt\n"
            report += "was successfully displayed in VSCode Copilot chat.\n"
        
        return report

def main():
    """メイン実行"""
    print("🔍 Starting Screenshot Verification...")
    
    verifier = ScreenshotVerifier()
    
    # スクリーンショット分析実行
    results = verifier.analyze_autonomous_screenshots()
    
    # レポート生成
    report = verifier.generate_verification_report(results)
    
    # レポート表示・保存
    print(report)
    
    # レポートをファイルに保存
    report_file = Path("evaluation_logs") / "screenshot_verification_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Verification report saved: {report_file}")

if __name__ == "__main__":
    main()
