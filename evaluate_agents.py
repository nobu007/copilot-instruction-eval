"""
GitHub Copilot Agent Evaluation Script

This script evaluates two versions of GitHub Copilot agents (v1 and v2) using a set of predefined instructions.
It collects responses, calculates metrics, and generates a comparison report with visualizations.
"""

import json
import os
import sys
import time
import logging
import shutil
from typing import Dict, List, Any, Optional, Tuple, Union
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import matplotlib.pyplot as plt
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge import Rouge

# Load environment variables from .env before anything else
load_dotenv()

# Ensure the output directory exists
os.makedirs("results", exist_ok=True)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 設定
CONFIG = {
    "agent_v1_endpoint": os.getenv("AGENT_V1_ENDPOINT"),
    "agent_v2_endpoint": os.getenv("AGENT_V2_ENDPOINT"),
    "api_key_v1": os.getenv("AGENT_V1_API_KEY"),
    "api_key_v2": os.getenv("AGENT_V2_API_KEY"),
    "instructions_file": "instructions.json",
    "results_dir": "results",
    "timeout": 60,  # 秒
    "max_retries": 3,  # リトライ回数
    "retry_delay": 5,  # リトライ間隔（秒）
}

class AgentEvaluator:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the evaluator with configuration."""
        self.config = config
        self._validate_config()
        self.instructions = self._load_instructions()
        self.results = []
        self._setup_directories()
        self.rouge = Rouge()  # ROUGEスコア計算用
        
        # Download required NLTK data
        try:
            import nltk
            nltk.download('punkt', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        required_vars = [
            "agent_v1_endpoint", "agent_v2_endpoint",
            "api_key_v1", "api_key_v2"
        ]
        
        missing_vars = [var for var in required_vars if not self.config.get(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required configuration variables: {', '.join(missing_vars)}\n"
                "Please set these in your .env file or environment variables."
            )

    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from the JSON file."""
        try:
            with open(self.config["instructions_file"], "r", encoding="utf-8") as f:
                data = json.load(f)
                instructions = data.get("instructions", [])
                logger.info(f"Loaded {len(instructions)} instructions from {self.config['instructions_file']}")
                return instructions
        except FileNotFoundError:
            logger.error(f"Instructions file not found: {self.config['instructions_file']}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in instructions file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading instructions: {e}")
            raise

    def _setup_directories(self) -> None:
        """Create necessary directories for storing results."""
        os.makedirs(self.config["results_dir"], exist_ok=True)

    def _call_agent_with_retry(self, instruction: Dict[str, Any], agent_version: str) -> Dict[str, Any]:
        """Make API call with retry mechanism."""
        endpoint = self.config[f"agent_{agent_version}_endpoint"]
        api_key = self.config[f"api_key_{agent_version}"]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "instruction": instruction["description"],
            "code": instruction.get("code", ""),
            "requirements": instruction.get("requirements", []),
            "metadata": {
                "instruction_id": instruction["id"],
                "type": instruction["type"],
                "difficulty": instruction["difficulty"]
            }
        }
        
        last_error = None
        for attempt in range(self.config["max_retries"]):
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config["timeout"]
                )
                response.raise_for_status()
                return {"success": True, "response": response.json()}
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.config["max_retries"] - 1:
                    wait_time = self.config["retry_delay"] * (attempt + 1)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {agent_version}. "
                        f"Retrying in {wait_time} seconds... Error: {e}"
                    )
                    time.sleep(wait_time)
        
        return {"success": False, "error": f"Failed after {self.config['max_retries']} attempts: {str(last_error)}"}

    def _calculate_metrics(self, response: str, expected: str) -> Dict[str, float]:
        """Calculate evaluation metrics for the response."""
        metrics = {
            "response_length": len(response),
            "expected_length": len(expected),
            "length_ratio": len(response) / max(len(expected), 1),  # ゼロ除算を防ぐ
        }
        
        # Jaccard類似度
        response_words = set(response.lower().split())
        expected_words = set(expected.lower().split())
        intersection = len(response_words.intersection(expected_words))
        union = len(response_words.union(expected_words))
        metrics["jaccard_similarity"] = intersection / union if union > 0 else 0
        
        # BLEUスコア
        try:
            smoothie = SmoothingFunction().method4
            metrics["bleu_score"] = sentence_bleu(
                [expected.split()],
                response.split(),
                smoothing_function=smoothie
            )
        except Exception as e:
            logger.warning(f"Error calculating BLEU score: {e}")
            metrics["bleu_score"] = 0.0
        
        # ROUGEスコア
        try:
            if response.strip() and expected.strip():
                rouge_scores = self.rouge.get_scores(response, expected)[0]
                metrics.update({
                    "rouge_1": rouge_scores["rouge-1"]["f"],
                    "rouge_2": rouge_scores["rouge-2"]["f"],
                    "rouge_l": rouge_scores["rouge-l"]["f"],
                })
            else:
                metrics.update({
                    "rouge_1": 0.0,
                    "rouge_2": 0.0,
                    "rouge_l": 0.0,
                })
        except Exception as e:
            logger.warning(f"Error calculating ROUGE scores: {e}")
            metrics.update({
                "rouge_1": 0.0,
                "rouge_2": 0.0,
                "rouge_l": 0.0,
            })
        
        return metrics

    def run_evaluation(self) -> None:
        """Run evaluation on all instructions for both agents."""
        logger.info(f"Starting evaluation of {len(self.instructions)} instructions...")
        
        for instruction in tqdm(self.instructions, desc="Evaluating instructions"):
            instruction_id = instruction["id"]
            logger.info(f"\nEvaluating instruction: {instruction['title']} ({instruction['type']})")
            
            # Test agent_v1
            logger.info("  Testing agent_v1...")
            result_v1 = self._evaluate_instruction(instruction, "v1")
            
            # Test agent_v2
            logger.info("  Testing agent_v2...")
            result_v2 = self._evaluate_instruction(instruction, "v2")
            
            # Store results
            self.results.append({
                "instruction_id": instruction_id,
                "instruction_type": instruction["type"],
                "difficulty": instruction["difficulty"],
                "v1_success": result_v1["success"],
                "v2_success": result_v2["success"],
                "v1_metrics": result_v1.get("metrics", {}),
                "v2_metrics": result_v2.get("metrics", {})
            })
            
            # Save intermediate results
            self._save_results()
    
    def _evaluate_instruction(self, instruction: Dict[str, Any], agent_version: str) -> Dict[str, Any]:
        """Evaluate a single instruction with the specified agent version."""
        result = {"success": False}
        
        # Call the agent with retry
        start_time = time.time()
        response = self._call_agent_with_retry(instruction, agent_version)
        duration = time.time() - start_time
        
        if response["success"]:
            # Calculate metrics if we have an expected response
            if "expected_response" in instruction:
                metrics = self._calculate_metrics(
                    response["response"].get("text", ""),
                    instruction["expected_response"]
                )
                metrics["response_time"] = duration
                result["metrics"] = metrics
            result["success"] = True
            logger.info(f"  {agent_version} completed in {duration:.2f}s")
        else:
            error_msg = f"Error with {agent_version}: {response.get('error', 'Unknown error')}"
            logger.error(f"  {error_msg}")
            result["error"] = error_msg
        
        return result
    
    def _save_results(self) -> None:
        """Save current results to JSON and CSV files."""
        # Save full results as JSON
        results_file = os.path.join(self.config["results_dir"], "evaluation_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        # Also save a flattened version as CSV for easier analysis
        self._save_results_csv()
        
        logger.info(f"Results saved to {results_file}")
    
    def _save_results_csv(self) -> None:
        """Save flattened results to CSV for easier analysis."""
        if not self.results:
            return
            
        # Flatten the results
        flattened = []
        for result in self.results:
            row = {
                "instruction_id": result["instruction_id"],
                "instruction_type": result["instruction_type"],
                "difficulty": result["difficulty"],
                "v1_success": int(result["v1_success"]),
                "v2_success": int(result["v2_success"]),
            }
            
            # Add metrics if available
            for version in ["v1", "v2"]:
                prefix = f"{version}_"
                metrics = result.get(f"{prefix}metrics", {})
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        row[f"{prefix}{key}"] = value
            
            flattened.append(row)
        
        # Save to CSV
        csv_file = os.path.join(self.config["results_dir"], "evaluation_results.csv")
        df = pd.DataFrame(flattened)
        df.to_csv(csv_file, index=False)
        logger.info(f"CSV results saved to {csv_file}")
        
        return df
    
    def generate_report(self) -> None:
        """Generate a comprehensive markdown report with visualizations."""
        if not self.results:
            logger.warning("No results to generate report.")
            return
            
        report_file = os.path.join(self.config["results_dir"], "evaluation_report.md")
        
        # Generate visualizations
        self._generate_visualizations()
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# GitHub Copilot Agent Evaluation Report\n\n")
            f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
            
            # Summary statistics
            total = len(self.results)
            v1_success = sum(1 for r in self.results if r["v1_success"])
            v2_success = sum(1 for r in self.results if r["v2_success"])
            improvement = (v2_success - v1_success) / total if total > 0 else 0
            
            f.write("## 📊 Summary\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Total Instructions | {total} |\n")
            f.write(f"| Agent v1 Success Rate | {v1_success/total:.1%} ({v1_success}/{total}) |\n")
            f.write(f"| Agent v2 Success Rate | {v2_success/total:.1%} ({v2_success}/{total}) |\n")
            f.write(f"| Improvement | {improvement:+.1%} points |\n\n")
            
            # Add success rate comparison chart
            f.write("## 📈 Success Rate Comparison\n\n")
            f.write("![Success Rate Comparison](success_rate_comparison.png)\n\n")
            
            # Add metrics comparison
            f.write("## 📊 Metrics Comparison\n\n")
            f.write("### Average Metrics\n")
            f.write("| Metric | Agent v1 | Agent v2 | Difference |\n")
            f.write("|--------|----------|----------|------------|\n")
            
            # Calculate average metrics
            metrics = ["jaccard_similarity", "bleu_score", "rouge_1", "rouge_2", "rouge_l", "response_time"]
            for metric in metrics:
                v1_avg = self._calculate_average_metric(metric, "v1")
                v2_avg = self._calculate_average_metric(metric, "v2")
                diff = v2_avg - v1_avg
                diff_str = f"{diff:+.3f}"
                if metric == "response_time":
                    f.write(f"| {metric} (s) | {v1_avg:.3f} | {v2_avg:.3f} | {diff_str} |\n")
                else:
                    f.write(f"| {metric} | {v1_avg:.3f} | {v2_avg:.3f} | {diff_str} |\n")
            
            f.write("\n![Metrics Comparison](metrics_comparison.png)\n\n")
            
            # Detailed results
            f.write("## 📋 Detailed Results\n\n")
            f.write("<details>")
            f.write("<summary>Click to expand detailed results</summary>\n\n")
            f.write("| ID | Type | Difficulty | v1 Success | v2 Success | v1 Jaccard | v2 Jaccard | v1 BLEU | v2 BLEU | v1 ROUGE-L | v2 ROUGE-L | v1 Time (s) | v2 Time (s) |\n")
            f.write("|----|------|------------|------------|------------|------------|------------|---------|---------|------------|------------|-------------|-------------|\n")
            
            for result in sorted(self.results, key=lambda x: x["instruction_id"]):
                v1_metrics = result.get("v1_metrics", {})
                v2_metrics = result.get("v2_metrics", {})
                
                f.write(f"| {result['instruction_id']} | {result['instruction_type']} | {result['difficulty']} | "
                       f"{'✅' if result['v1_success'] else '❌'} | "
                       f"{'✅' if result['v2_success'] else '❌'} | "
                       f"{v1_metrics.get('jaccard_similarity', 0):.3f} | "
                       f"{v2_metrics.get('jaccard_similarity', 0):.3f} | "
                       f"{v1_metrics.get('bleu_score', 0):.3f} | "
                       f"{v2_metrics.get('bleu_score', 0):.3f} | "
                       f"{v1_metrics.get('rouge_l', 0):.3f} | "
                       f"{v2_metrics.get('rouge_l', 0):.3f} | "
                       f"{v1_metrics.get('response_time', 0):.2f} | "
                       f"{v2_metrics.get('response_time', 0):.2f} |\n")
            
            f.write("</details>\n\n")
            
            # Configuration
            f.write("## ⚙️ Configuration\n\n")
            f.write("<details>")
            f.write("<summary>Click to view evaluation configuration</summary>\n\n")
            f.write("```json\n")
            f.write(json.dumps({
                k: v for k, v in self.config.items() 
                if not k.endswith("api_key")  # Don't log API keys
            }, indent=2))
            f.write("\n```\n")
            f.write("</details>\n")
        
        logger.info(f"Report generated at {report_file}")
    
    def _calculate_average_metric(self, metric_name: str, version: str) -> float:
        """Calculate average of a specific metric for a version."""
        total = 0
        count = 0
        
        for result in self.results:
            metrics = result.get(f"{version}_metrics", {})
            if metric_name in metrics and metrics[metric_name] is not None:
                total += metrics[metric_name]
                count += 1
        
        return total / count if count > 0 else 0.0
    
    def _generate_visualizations(self) -> None:
        """Generate visualization charts for the evaluation results."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Set style
            plt.style.use('seaborn')
            
            # 1. Success Rate Comparison
            total = len(self.results)
            v1_success = sum(1 for r in self.results if r["v1_success"])
            v2_success = sum(1 for r in self.results if r["v2_success"])
            
            fig, ax = plt.subplots(figsize=(10, 6))
            x = np.arange(1)
            width = 0.35
            
            rects1 = ax.bar(x - width/2, v1_success/total*100, width, label='Agent v1')
            rects2 = ax.bar(x + width/2, v2_success/total*100, width, label='Agent v2')
            
            ax.set_ylabel('Success Rate (%)')
            ax.set_title('Agent Success Rate Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels([''])
            ax.legend()
            
            # Add value labels
            def autolabel(rects):
                for rect in rects:
                    height = rect.get_height()
                    ax.annotate(f'{height:.1f}%',
                              xy=(rect.get_x() + rect.get_width() / 2, height),
                              xytext=(0, 3),  # 3 points vertical offset
                              textcoords="offset points",
                              ha='center', va='bottom')
            
            autolabel(rects1)
            autolabel(rects2)
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.config["results_dir"], "success_rate_comparison.png"))
            plt.close()
            
            # 2. Metrics Comparison
            metrics = ["jaccard_similarity", "bleu_score", "rouge_1", "rouge_2", "rouge_l"]
            v1_avgs = [self._calculate_average_metric(m, "v1") for m in metrics]
            v2_avgs = [self._calculate_average_metric(m, "v2") for m in metrics]
            
            x = np.arange(len(metrics))
            width = 0.35
            
            fig, ax = plt.subplots(figsize=(12, 6))
            rects1 = ax.bar(x - width/2, v1_avgs, width, label='Agent v1')
            rects2 = ax.bar(x + width/2, v2_avgs, width, label='Agent v2')
            
            ax.set_ylabel('Score')
            ax.set_title('Average Metrics Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics])
            ax.legend()
            
            # Add value labels
            def autolabel(rects):
                for rect in rects:
                    height = rect.get_height()
                    ax.annotate(f'{height:.3f}',
                              xy=(rect.get_x() + rect.get_width() / 2, height),
                              xytext=(0, 3),  # 3 points vertical offset
                              textcoords="offset points",
                              ha='center', va='bottom', fontsize=8)
            
            autolabel(rects1)
            autolabel(rects2)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(self.config["results_dir"], "metrics_comparison.png"))
            plt.close()
            
            # 3. Response Time Comparison
            v1_times = []
            v2_times = []
            for result in self.results:
                v1_metrics = result.get("v1_metrics", {})
                v2_metrics = result.get("v2_metrics", {})
                if "response_time" in v1_metrics:
                    v1_times.append(v1_metrics["response_time"])
                if "response_time" in v2_metrics:
                    v2_times.append(v2_metrics["response_time"])
            
            if v1_times and v2_times:
                fig, ax = plt.subplots(figsize=(10, 6))
                x = np.arange(2)
                
                # Calculate mean and std
                v1_mean = np.mean(v1_times)
                v2_mean = np.mean(v2_times)
                v1_std = np.std(v1_times, ddof=1)  # Sample standard deviation
                v2_std = np.std(v2_times, ddof=1)
                
                rects1 = ax.bar(x[0], v1_mean, width=0.6, yerr=v1_std, 
                               capsize=10, label='Agent v1', alpha=0.7)
                rects2 = ax.bar(x[1], v2_mean, width=0.6, yerr=v2_std, 
                               capsize=10, label='Agent v2', alpha=0.7)
                
                ax.set_ylabel('Response Time (s)')
                ax.set_title('Average Response Time Comparison')
                ax.set_xticks(x)
                ax.set_xticklabels(['Agent v1', 'Agent v2'])
                ax.legend()
                
                # Add value labels
                def autolabel(rects):
                    for rect in rects:
                        height = rect.get_height()
                        ax.annotate(f'{height:.2f}±{rect.get_yerr():.2f}s',
                                  xy=(rect.get_x() + rect.get_width() / 2, height),
                                  xytext=(0, 3),  # 3 points vertical offset
                                  textcoords="offset points",
                                  ha='center', va='bottom')
                
                autolabel(rects1)
                autolabel(rects2)
                
                plt.tight_layout()
                plt.savefig(os.path.join(self.config["results_dir"], "response_time_comparison.png"))
                plt.close()
            
            logger.info("Visualizations generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}", exc_info=True)

def main():
    """Main function to run the evaluation and generate reports."""
    print("GitHub Copilot Agent Evaluation")
    print("=" * 50)
    
    try:
        # Initialize evaluator
        evaluator = AgentEvaluator(CONFIG)
        
        # Run evaluation
        print("\n[START] Starting evaluation...")
        start_time = time.time()
        evaluator.run_evaluation()
        
        # Generate report
        print("\n[REPORT] Generating report...")
        evaluator.generate_report()
        
        # Print completion message
        duration = time.time() - start_time
        print(f"\n[DONE] Evaluation completed in {duration:.1f} seconds!")
        print(f"[RESULTS] Report and results saved to: {os.path.abspath(CONFIG['results_dir'])}")
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Evaluation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {str(e)}")
        logging.exception("Evaluation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
