#!/usr/bin/env python3
"""
Prompt Input Verification using Image Recognition
Verifies that prompts are actually typed into the input field using OCR and image analysis
"""

import os
import sys
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageGrab
import logging
from datetime import datetime
import json
import difflib
import re

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"prompt_verification_{TIMESTAMP}.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class PromptVerifier:
    def __init__(self):
        self.verification_results = {}
        
    def load_image(self, image_path):
        """Load image from file path"""
        try:
            if os.path.exists(image_path):
                image = cv2.imread(image_path)
                logger.info(f"Image loaded: {image_path}")
                return image
            else:
                logger.error(f"Image not found: {image_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None
    
    def preprocess_for_ocr(self, image, region=None):
        """Preprocess image for better OCR results"""
        try:
            # Extract region if specified
            if region:
                x, y, w, h = region
                image = image[y:y+h, x:x+w]
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply different preprocessing techniques
            processed_images = []
            
            # 1. Original grayscale
            processed_images.append(("original", gray))
            
            # 2. Threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("threshold", thresh))
            
            # 3. Adaptive threshold
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            processed_images.append(("adaptive", adaptive))
            
            # 4. Morphological operations
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            processed_images.append(("morphological", morph))
            
            # 5. Gaussian blur + threshold
            blur = cv2.GaussianBlur(gray, (5,5), 0)
            _, blur_thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("blur_threshold", blur_thresh))
            
            return processed_images
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return []
    
    def extract_text_from_image(self, image, method_name=""):
        """Extract text from image using OCR"""
        try:
            # Configure Tesseract with simpler config
            custom_config = r'--oem 3 --psm 6'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean up text
            text = text.strip()
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            
            if text:
                logger.info(f"OCR ({method_name}) extracted text: '{text}'")
            else:
                logger.debug(f"OCR ({method_name}) found no text")
                
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text with OCR ({method_name}): {e}")
            return ""
    
    def find_input_regions(self, image):
        """Find potential input field regions in the image"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Find contours that might be input fields
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            input_regions = []
            height, width = image.shape[:2]
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter for input field-like shapes
                if (w > 200 and h > 15 and h < 100 and w/h > 3 and 
                    y > height * 0.5):  # Focus on bottom half of screen
                    input_regions.append((x, y, w, h))
            
            # Sort by area (largest first)
            input_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
            
            logger.info(f"Found {len(input_regions)} potential input regions")
            return input_regions[:5]  # Return top 5 candidates
            
        except Exception as e:
            logger.error(f"Error finding input regions: {e}")
            return []
    
    def verify_prompt_input(self, image_path, expected_prompt):
        """Verify that the expected prompt appears in the image"""
        try:
            logger.info(f"Verifying prompt input in: {image_path}")
            logger.info(f"Expected prompt: '{expected_prompt}'")
            
            image = self.load_image(image_path)
            if image is None:
                return False
            
            # Find potential input regions
            input_regions = self.find_input_regions(image)
            
            verification_result = {
                "image_path": image_path,
                "expected_prompt": expected_prompt,
                "found_text": [],
                "match_scores": [],
                "verification_passed": False
            }
            
            # Check full image first
            processed_images = self.preprocess_for_ocr(image)
            
            for method_name, processed_img in processed_images:
                text = self.extract_text_from_image(processed_img, method_name)
                if text:
                    verification_result["found_text"].append(f"Full image ({method_name}): {text}")
                    
                    # Calculate similarity score
                    similarity = difflib.SequenceMatcher(None, expected_prompt.lower(), text.lower()).ratio()
                    verification_result["match_scores"].append(f"{method_name}: {similarity:.3f}")
                    
                    # Check if prompt is contained in the text
                    if expected_prompt.lower() in text.lower() or similarity > 0.7:
                        verification_result["verification_passed"] = True
                        logger.info(f"✅ Prompt verification PASSED (method: {method_name}, similarity: {similarity:.3f})")
            
            # Check specific input regions
            for i, region in enumerate(input_regions):
                logger.info(f"Checking input region {i+1}: {region}")
                
                processed_regions = self.preprocess_for_ocr(image, region)
                
                for method_name, processed_img in processed_regions:
                    text = self.extract_text_from_image(processed_img, f"region_{i+1}_{method_name}")
                    if text:
                        verification_result["found_text"].append(f"Region {i+1} ({method_name}): {text}")
                        
                        # Calculate similarity score
                        similarity = difflib.SequenceMatcher(None, expected_prompt.lower(), text.lower()).ratio()
                        verification_result["match_scores"].append(f"region_{i+1}_{method_name}: {similarity:.3f}")
                        
                        # Check if prompt is contained in the text
                        if expected_prompt.lower() in text.lower() or similarity > 0.7:
                            verification_result["verification_passed"] = True
                            logger.info(f"✅ Prompt verification PASSED (region {i+1}, method: {method_name}, similarity: {similarity:.3f})")
            
            # Save verification result
            result_path = os.path.join(LOG_DIR, f"verification_result_{TIMESTAMP}.json")
            with open(result_path, 'w') as f:
                json.dump(verification_result, f, indent=2)
            
            if verification_result["verification_passed"]:
                logger.info("✅ VERIFICATION PASSED: Prompt was successfully input")
            else:
                logger.warning("❌ VERIFICATION FAILED: Prompt was not found in the image")
                logger.info("Found text samples:")
                for text in verification_result["found_text"][:5]:  # Show first 5 samples
                    logger.info(f"  - {text}")
            
            return verification_result["verification_passed"]
            
        except Exception as e:
            logger.error(f"Error verifying prompt input: {e}")
            return False
    
    def verify_latest_automation_run(self):
        """Verify the latest automation run by checking recent screenshots"""
        try:
            logger.info("=== Verifying Latest Automation Run ===")
            
            # Define the expected prompt
            expected_prompt = "Hello! Can you help me write a Python function to calculate the factorial of a number?"
            
            # Find recent screenshots
            screenshot_patterns = [
                "after_precise_typing_",
                "before_precise_input_",
                "precise_copilot_opened",
                "precise_final_state"
            ]
            
            verification_results = {}
            
            for pattern in screenshot_patterns:
                # Find matching files
                matching_files = []
                for filename in os.listdir(LOG_DIR):
                    if pattern in filename and filename.endswith('.png'):
                        filepath = os.path.join(LOG_DIR, filename)
                        matching_files.append(filepath)
                
                # Sort by modification time (newest first)
                matching_files.sort(key=os.path.getmtime, reverse=True)
                
                if matching_files:
                    latest_file = matching_files[0]
                    logger.info(f"Checking {pattern}: {latest_file}")
                    
                    result = self.verify_prompt_input(latest_file, expected_prompt)
                    verification_results[pattern] = {
                        "file": latest_file,
                        "passed": result
                    }
            
            # Summary
            logger.info("=== Verification Summary ===")
            passed_count = 0
            total_count = len(verification_results)
            
            for pattern, result in verification_results.items():
                status = "✅ PASSED" if result["passed"] else "❌ FAILED"
                logger.info(f"{pattern}: {status}")
                if result["passed"]:
                    passed_count += 1
            
            overall_success = passed_count > 0
            logger.info(f"Overall verification: {passed_count}/{total_count} screenshots verified")
            
            if overall_success:
                logger.info("🎉 PROMPT INPUT VERIFICATION SUCCESSFUL!")
            else:
                logger.warning("⚠️  PROMPT INPUT VERIFICATION FAILED - No screenshots showed the expected prompt")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Error in verification: {e}")
            return False

def main():
    """Main function for prompt verification"""
    logger.info("=== Prompt Input Verification Started ===")
    
    try:
        verifier = PromptVerifier()
        
        # Verify the latest automation run
        success = verifier.verify_latest_automation_run()
        
        if success:
            logger.info("=== Prompt Verification Completed Successfully ===")
        else:
            logger.error("=== Prompt Verification Failed ===")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
