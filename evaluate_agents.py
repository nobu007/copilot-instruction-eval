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
import seaborn as sns
import sqlite3

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
    "agent_v2_model": os.getenv("AGENT_V2_MODEL"),
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
        self.db_conn = self._setup_database()
        
        # Download required NLTK data
        try:
            import nltk
            nltk.download('punkt', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        # Check for demo mode
        if self.config.get("demo_mode"):
            logger.info("Running in demo mode - using simulated responses")
            return
            
        required_vars = [
            "agent_v1_endpoint", "agent_v2_endpoint",
            "api_key_v1", "api_key_v2"
        ]
        
        missing_vars = [var for var in required_vars if not self.config.get(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required configuration variables: {', '.join(missing_vars)}\n"
                "Please set these in your .env file or environment variables.\n"
                "Alternatively, use --demo-mode to run with simulated data."
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

    def _get_sanitized_config(self) -> Dict[str, Any]:
        """Return a copy of the config with sensitive values removed."""
        sanitized_config = self.config.copy()
        if "api_key_v1" in sanitized_config:
            sanitized_config["api_key_v1"] = "***REDACTED***"
        if "api_key_v2" in sanitized_config:
            sanitized_config["api_key_v2"] = "***REDACTED***"
        return sanitized_config

    def _simulate_agent_response(self, agent_version: str, instruction_text: str) -> str:
        """Simulate agent response for demo mode."""
        import random
        
        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))
        
        # Template responses based on instruction type
        templates = {
            "code_review": f"Agent {agent_version}: Security analysis indicates potential vulnerabilities in the authentication code. The implementation lacks proper password hashing and salt usage.",
            "pr_creation": f"Agent {agent_version}: I'll create a pull request for input validation with email format checks, strong password policies (12+ chars, special chars, numbers), and server-side validation.",
            "bug_fix": f"Agent {agent_version}: This issue appears to be related to race conditions. I recommend implementing proper synchronization mechanisms.",
            "optimization": f"Agent {agent_version}: Performance can be improved by implementing caching mechanisms and optimizing database queries.",
            "refactoring": f"Agent {agent_version}: The code structure can be improved by applying SOLID principles and reducing cyclomatic complexity."
        }
        
        # Determine instruction type from text
        instruction_lower = instruction_text.lower()
        if "security" in instruction_lower or "authentication" in instruction_lower:
            response_type = "code_review"
        elif "pull request" in instruction_lower or "validation" in instruction_lower:
            response_type = "pr_creation"
        elif "bug" in instruction_lower or "error" in instruction_lower:
            response_type = "bug_fix"
        elif "performance" in instruction_lower or "optimize" in instruction_lower:
            response_type = "optimization"
        else:
            response_type = "refactoring"
        
        base_response = templates.get(response_type, f"Agent {agent_version}: [Simulated response] Analysis and recommendations provided based on the given instruction.")
        
        # Add some variation between agents
        if agent_version == "v2":
            base_response += " Additionally, I suggest implementing comprehensive testing and documentation."
        
        return base_response

    def _call_agent_with_retry(self, agent_version: str, instruction_text: str) -> Tuple[Optional[str], Optional[str]]:
        """Make API call with retry mechanism and return (response_text, error_message)."""
        # Demo mode: return simulated responses
        if self.config.get("demo_mode"):
            return self._simulate_agent_response(agent_version, instruction_text), None
            
        api_key = self.config[f"api_key_{agent_version}"]
        headers = {}
        params = {}
        payload = {}
        endpoint = self.config[f"agent_{agent_version}_endpoint"]

        # API format differs for v1 (Google AI) and v2 (Groq/OpenAI)
        if agent_version == 'v2':
            model_name = self.config.get("agent_v2_model")
            # If model is not in config, try to parse from endpoint URL as a fallback
            if not model_name:
                url_parts = endpoint.split('/')
                if len(url_parts) > 7 and url_parts[6] == 'completions':
                    model_name = '/'.join(url_parts[7:])
                    logger.info(f"AGENT_V2_MODEL not set, parsed model '{model_name}' from endpoint URL.")
                else:
                    model_name = 'llama3-8b-8192' # Fallback to a default model
                    logger.warning(f"AGENT_V2_MODEL not set and couldn't parse from URL. Using default model: {model_name}")
            
            # V2 always uses the same base endpoint
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [{"role": "user", "content": instruction_text}],
                "model": model_name
            }
            params = None # No URL params for OpenAI-compatible APIs
        else:  # agent_version == 'v1'
            headers = {"Content-Type": "application/json"}
            params = {'key': api_key}
            payload = {
                "contents": [{"parts": [{"text": instruction_text}]}]
            }

        last_error = None
        for attempt in range(self.config["max_retries"]):
            try:
                logger.debug(f"--- API Request Details (Attempt {attempt + 1}) ---")
                logger.debug(f"Agent: {agent_version}, URL: {endpoint}")
                logger.debug(f"Headers: {headers}")
                logger.debug(f"Params: {params}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config["timeout"],
                    params=params
                )
                response.raise_for_status()

                if agent_version == 'v2':
                    return response.json()['choices'][0]['message']['content'], None
                else:  # agent_version == 'v1'
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"], None

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = e.response.status_code
                error_detail = e.response.text
                logger.error(f"HTTP Error {status_code} for {agent_version}: {error_detail}")
                wait_time = self.config["retry_delay"] * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed for {agent_version}. "
                    f"Retrying in {wait_time} seconds... Error: {e}"
                )
                time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                last_error = e
                wait_time = self.config["retry_delay"] * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed for {agent_version}. "
                    f"Retrying in {wait_time} seconds... Error: {e}"
                )
                time.sleep(wait_time)

        error_message = f"Failed after {self.config['max_retries']} attempts: {str(last_error)}"
        logger.error(f"Error with {agent_version}: {error_message}")
        return None, error_message

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
        
        # Create a new evaluation run
        cursor = self.db_conn.cursor()
        timestamp = datetime.now()
        config_str = json.dumps(self._get_sanitized_config())
        cursor.execute("INSERT INTO evaluation_runs (timestamp, config) VALUES (?, ?)", (timestamp, config_str))
        run_id = cursor.lastrowid
        self.db_conn.commit()
        
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
            self._save_results(run_id)
    
    def _evaluate_instruction(self, instruction: Dict[str, Any], agent_version: str) -> Dict[str, Any]:
        """Evaluate a single instruction with the specified agent version."""
        result = {"success": False}
        
        prompt_parts = []
        if instruction.get("description"):
            prompt_parts.append(instruction["description"])
        if instruction.get("code"):
            prompt_parts.append(f'\n\n```\n{instruction["code"]}\n```')
        if instruction.get("requirements"):
            req_text = "\n".join(f'- {r}' for r in instruction["requirements"])
            prompt_parts.append(f'\n\nRequirements:\n{req_text}')
        instruction_text = "\n".join(prompt_parts)

        start_time = time.time()
        response_text, error = self._call_agent_with_retry(agent_version, instruction_text)
        duration = time.time() - start_time
        
        if error is None and response_text is not None:
            result["success"] = True
            if "expected_response" in instruction:
                metrics = self._calculate_metrics(
                    response_text,
                    instruction["expected_response"]
                )
                metrics["response_time"] = duration
                result["metrics"] = metrics
            logger.info(f"  {agent_version} completed in {duration:.2f}s")
        else:
            error_msg = f"Error with {agent_version}: {error or 'Unknown error'}"
            logger.error(f"  {error_msg}")
            result["error"] = error_msg
        
        return result
    
    def _save_results(self, run_id: int) -> None:
        """Save current results to JSON, CSV, and SQLite."""
        # Save full results as JSON
        results_file = os.path.join(self.config["results_dir"], "evaluation_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "config": self._get_sanitized_config(),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        # Also save a flattened version as CSV for easier analysis
        self._save_results_csv()
        
        # Save to database
        self._save_results_to_db(run_id)
        
        logger.info(f"Results saved to {results_file}, CSV, and database.")
    
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

    def _setup_database(self) -> sqlite3.Connection:
        """Setup the SQLite database and create tables."""
        db_path = os.path.join(self.config["results_dir"], "evaluation.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create evaluation_runs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            config TEXT NOT NULL
        )
        """)
        
        # Create results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            instruction_id TEXT NOT NULL,
            instruction_type TEXT,
            difficulty TEXT,
            agent_version TEXT NOT NULL,
            success BOOLEAN,
            response_time REAL,
            jaccard_similarity REAL,
            bleu_score REAL,
            rouge_1 REAL,
            rouge_2 REAL,
            rouge_l REAL,
            FOREIGN KEY (run_id) REFERENCES evaluation_runs (run_id)
        )
        """)
        
        conn.commit()
        logger.info(f"Database setup complete at {db_path}")
        return conn

    def _save_results_to_db(self, run_id: int) -> None:
        """Save evaluation results to the SQLite database."""
        cursor = self.db_conn.cursor()
        
        for result in self.results:
            for version in ["v1", "v2"]:
                metrics = result.get(f"{version}_metrics", {})
                cursor.execute("""
                INSERT INTO results (
                    run_id, instruction_id, instruction_type, difficulty, 
                    agent_version, success, response_time, jaccard_similarity, 
                    bleu_score, rouge_1, rouge_2, rouge_l
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    result["instruction_id"],
                    result["instruction_type"],
                    result["difficulty"],
                    version,
                    result[f"{version}_success"],
                    metrics.get("response_time"),
                    metrics.get("jaccard_similarity"),
                    metrics.get("bleu_score"),
                    metrics.get("rouge_1"),
                    metrics.get("rouge_2"),
                    metrics.get("rouge_l"),
                ))
        
        self.db_conn.commit()
        logger.info("Results saved to database.")

    def _fetch_historical_data(self) -> pd.DataFrame:
        """Fetch historical evaluation data from the database."""
        try:
            query = """
            SELECT r.run_id, r.timestamp, res.* 
            FROM evaluation_runs r JOIN results res ON r.run_id = res.run_id
            """
            df = pd.read_sql_query(query, self.db_conn)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Fetched {len(df)} historical records from the database.")
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def generate_report(self) -> None:
        """Generate a comprehensive markdown report with visualizations."""
        if not self.results:
            logger.warning("No results to generate report.")
            return
            
        report_file = os.path.join(self.config["results_dir"], "evaluation_report.md")
        historical_data = self._fetch_historical_data()
        
        # Generate visualizations
        self._generate_visualizations(historical_data)
        
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

            # Historical Trend Analysis
            if not historical_data.empty:
                f.write("## 📉 Historical Trend Analysis\n\n")
                f.write("![Historical Success Rate](historical_success_rate.png)\n\n")
                f.write("![Historical Response Time](historical_response_time.png)\n\n")
            
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
            f.write(json.dumps(self._get_sanitized_config(), indent=2))
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
    
    def _generate_visualizations(self, historical_data: pd.DataFrame) -> None:
        """Generate visualization charts for the evaluation results."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Set style
            sns.set_theme(style="whitegrid")
            
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

                # Annotate bars with mean and std dev
                ax.annotate(f'{v1_mean:.2f} ± {v1_std:.2f}s',
                            xy=(rects1[0].get_x() + rects1[0].get_width() / 2, v1_mean),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom')
                ax.annotate(f'{v2_mean:.2f} ± {v2_std:.2f}s',
                            xy=(rects2[0].get_x() + rects2[0].get_width() / 2, v2_mean),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom')

                plt.tight_layout()
                plt.savefig(os.path.join(self.config["results_dir"], "response_time_comparison.png"))
                plt.close()

            # 4. Historical Trend Analysis
            if not historical_data.empty:
                # Success Rate Trend
                hist_success = historical_data.groupby(['timestamp', 'agent_version'])['success'].mean().unstack()
                hist_success.plot(figsize=(12, 6), marker='o')
                plt.title('Historical Success Rate Trend')
                plt.ylabel('Success Rate')
                plt.xlabel('Date')
                plt.legend(title='Agent Version')
                plt.grid(True)
                plt.tight_layout()
                plt.savefig(os.path.join(self.config["results_dir"], "historical_success_rate.png"))
                plt.close()

                # Response Time Trend
                hist_time = historical_data.groupby(['timestamp', 'agent_version'])['response_time'].mean().unstack()
                hist_time.plot(figsize=(12, 6), marker='o')
                plt.title('Historical Response Time Trend')
                plt.ylabel('Average Response Time (s)')
                plt.xlabel('Date')
                plt.legend(title='Agent Version')
                plt.grid(True)
                plt.tight_layout()
                plt.savefig(os.path.join(self.config["results_dir"], "historical_response_time.png"))
                plt.close()
            
            logger.info("Visualizations generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}", exc_info=True)

def main():
    """Main function to run the evaluation and generate reports."""
    import argparse

    parser = argparse.ArgumentParser(description="GitHub Copilot Agent Evaluation Script")
    parser.add_argument(
        "--instructions",
        type=str,
        default=CONFIG["instructions_file"],
        help=f"Path to the instructions JSON file (default: {CONFIG['instructions_file']})",
    )
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode with simulated responses (no API calls)"
    )
    args = parser.parse_args()

    # Update CONFIG with parsed arguments
    CONFIG["instructions_file"] = args.instructions
    CONFIG["demo_mode"] = args.demo_mode

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
