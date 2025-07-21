#!/usr/bin/env python3
"""
YOLO-based Input Field Verification
Compares before/after screenshots to detect text input in VSCode Copilot chat
"""

import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
import logging
from datetime import datetime
import json
from PIL import Image

# Setup logging
LOG_DIR = "evaluation_logs"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"yolo_input_verification_{TIMESTAMP}.log")

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

class YOLOInputVerifier:
    def __init__(self):
        self.model = None
        self.load_yolo_model()
        
    def load_yolo_model(self):
        """Load YOLO model for UI detection"""
        try:
            # Use YOLOv8 nano model for faster inference
            self.model = YOLO('yolov8n.pt')
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading YOLO model: {e}")
            self.model = None
    
    def detect_input_fields(self, image_path):
        """Detect input fields and text areas in the image"""
        try:
            logger.info(f"Analyzing image: {image_path}")
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return []
            
            height, width = image.shape[:2]
            
            # Focus on bottom half where Copilot chat input is likely located
            bottom_half = image[height//2:, :]
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(bottom_half, cv2.COLOR_BGR2GRAY)
            
            # Find rectangular regions that could be input fields
            # Use edge detection and contour finding
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            input_fields = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Adjust coordinates back to full image
                y += height // 2
                
                # Filter for input field-like shapes
                aspect_ratio = w / h if h > 0 else 0
                area = w * h
                
                # Input field criteria:
                # - Width > 200px (reasonable input field width)
                # - Height between 15-80px (typical input field height)
                # - Aspect ratio > 3 (wider than tall)
                # - Located in bottom 60% of screen
                # - Minimum area
                if (w > 200 and 15 < h < 80 and aspect_ratio > 3 and 
                    y > height * 0.4 and area > 3000):
                    
                    input_fields.append({
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'center': (x + w//2, y + h//2)
                    })
            
            # Sort by area (largest first) and position (bottom first)
            input_fields.sort(key=lambda f: (f['bbox'][1], -f['area']))
            
            logger.info(f"Found {len(input_fields)} potential input fields")
            for i, field in enumerate(input_fields):
                bbox = field['bbox']
                logger.info(f"  Field {i+1}: bbox={bbox}, area={field['area']}, ratio={field['aspect_ratio']:.2f}")
            
            return input_fields
            
        except Exception as e:
            logger.error(f"Error detecting input fields: {e}")
            return []
    
    def extract_input_field_content(self, image_path, input_field):
        """Extract the visual content of an input field region"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            x, y, w, h = input_field['bbox']
            
            # Extract the input field region with some padding
            padding = 5
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.shape[1], x + w + padding)
            y2 = min(image.shape[0], y + h + padding)
            
            field_region = image[y1:y2, x1:x2]
            
            return field_region
            
        except Exception as e:
            logger.error(f"Error extracting input field content: {e}")
            return None
    
    def compare_input_fields(self, before_image, after_image):
        """Compare input fields between before and after images"""
        try:
            logger.info("=== Comparing Input Fields ===")
            
            # Detect input fields in both images
            before_fields = self.detect_input_fields(before_image)
            after_fields = self.detect_input_fields(after_image)
            
            if not before_fields or not after_fields:
                logger.warning("Could not find input fields in one or both images")
                return False
            
            # Find matching input fields (by position similarity)
            matches = []
            for before_field in before_fields:
                before_center = before_field['center']
                
                best_match = None
                min_distance = float('inf')
                
                for after_field in after_fields:
                    after_center = after_field['center']
                    
                    # Calculate distance between centers
                    distance = np.sqrt((before_center[0] - after_center[0])**2 + 
                                     (before_center[1] - after_center[1])**2)
                    
                    if distance < min_distance and distance < 300:  # Within 300 pixels (more flexible)
                        min_distance = distance
                        best_match = after_field
                
                if best_match:
                    matches.append((before_field, best_match))
                    logger.info(f"Matched input field: distance={min_distance:.1f}px")
            
            # If no close matches, try to match by size similarity
            if not matches:
                logger.info("No close position matches, trying size-based matching...")
                for before_field in before_fields:
                    before_area = before_field['area']
                    
                    best_match = None
                    min_area_diff = float('inf')
                    
                    for after_field in after_fields:
                        after_area = after_field['area']
                        area_diff = abs(before_area - after_area) / max(before_area, after_area)
                        
                        if area_diff < min_area_diff and area_diff < 0.5:  # Within 50% area difference
                            min_area_diff = area_diff
                            best_match = after_field
                    
                    if best_match:
                        matches.append((before_field, best_match))
                        logger.info(f"Size-matched input field: area_diff={min_area_diff:.2f}")
            
            # If still no matches, use the largest fields from each image
            if not matches and before_fields and after_fields:
                logger.info("Using largest input fields from each image...")
                largest_before = max(before_fields, key=lambda f: f['area'])
                largest_after = max(after_fields, key=lambda f: f['area'])
                matches.append((largest_before, largest_after))
                logger.info("Matched largest input fields")
            
            if not matches:
                logger.warning("No matching input fields found between images")
                return False
            
            # Compare the content of matched input fields
            differences_found = False
            
            for i, (before_field, after_field) in enumerate(matches):
                logger.info(f"Analyzing input field pair {i+1}")
                
                # Extract field regions
                before_content = self.extract_input_field_content(before_image, before_field)
                after_content = self.extract_input_field_content(after_image, after_field)
                
                if before_content is None or after_content is None:
                    continue
                
                # Resize to same dimensions for comparison
                h, w = min(before_content.shape[0], after_content.shape[0]), min(before_content.shape[1], after_content.shape[1])
                before_resized = cv2.resize(before_content, (w, h))
                after_resized = cv2.resize(after_content, (w, h))
                
                # Calculate difference
                diff = cv2.absdiff(before_resized, after_resized)
                diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                
                # Count significant differences
                _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)
                diff_pixels = np.sum(thresh > 0)
                total_pixels = thresh.shape[0] * thresh.shape[1]
                diff_percentage = (diff_pixels / total_pixels) * 100
                
                logger.info(f"Field {i+1} difference: {diff_pixels}/{total_pixels} pixels ({diff_percentage:.2f}%)")
                
                # Save difference visualization
                diff_filename = os.path.join(LOG_DIR, f"input_field_diff_{i+1}_{TIMESTAMP}.png")
                cv2.imwrite(diff_filename, diff)
                
                before_filename = os.path.join(LOG_DIR, f"before_field_{i+1}_{TIMESTAMP}.png")
                after_filename = os.path.join(LOG_DIR, f"after_field_{i+1}_{TIMESTAMP}.png")
                cv2.imwrite(before_filename, before_content)
                cv2.imwrite(after_filename, after_content)
                
                # Consider significant if more than 5% of pixels changed
                if diff_percentage > 5.0:
                    differences_found = True
                    logger.info(f"✅ SIGNIFICANT CHANGE DETECTED in field {i+1} ({diff_percentage:.2f}% pixels changed)")
                else:
                    logger.info(f"❌ No significant change in field {i+1} ({diff_percentage:.2f}% pixels changed)")
            
            return differences_found
            
        except Exception as e:
            logger.error(f"Error comparing input fields: {e}")
            return False
    
    def verify_prompt_input_by_difference(self):
        """Verify prompt input by comparing before/after screenshots"""
        try:
            logger.info("=== YOLO Input Verification Started ===")
            
            # Find before and after screenshots
            before_files = []
            after_files = []
            
            for filename in os.listdir(LOG_DIR):
                if filename.endswith('.png'):
                    if 'before_precise_input' in filename:
                        before_files.append(os.path.join(LOG_DIR, filename))
                    elif 'after_precise_typing' in filename:
                        after_files.append(os.path.join(LOG_DIR, filename))
            
            # Sort by modification time (newest first)
            before_files.sort(key=os.path.getmtime, reverse=True)
            after_files.sort(key=os.path.getmtime, reverse=True)
            
            if not before_files or not after_files:
                logger.error("Could not find before/after screenshots for comparison")
                return False
            
            before_image = before_files[0]
            after_image = after_files[0]
            
            logger.info(f"Comparing:")
            logger.info(f"  Before: {before_image}")
            logger.info(f"  After:  {after_image}")
            
            # Compare the images
            input_detected = self.compare_input_fields(before_image, after_image)
            
            if input_detected:
                logger.info("🎉 VERIFICATION SUCCESSFUL: Prompt input detected via image difference analysis!")
            else:
                logger.warning("⚠️  VERIFICATION FAILED: No significant input field changes detected")
            
            return input_detected
            
        except Exception as e:
            logger.error(f"Error in verification: {e}")
            return False

def main():
    """Main function for YOLO input verification"""
    logger.info("=== YOLO Input Field Verification Started ===")
    
    try:
        verifier = YOLOInputVerifier()
        
        # Verify prompt input by comparing before/after images
        success = verifier.verify_prompt_input_by_difference()
        
        if success:
            logger.info("=== YOLO Input Verification Completed Successfully ===")
        else:
            logger.error("=== YOLO Input Verification Failed ===")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
