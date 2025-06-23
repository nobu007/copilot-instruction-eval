"""
GitHub Copilot Agent Evaluation Script

This script evaluates two versions of GitHub Copilot agents (v1 and v2) using a set of predefined instructions.
It collects responses, calculates metrics, and generates a comparison report.
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    "agent_v1_endpoint": os.getenv("AGENT_V1_ENDPOINT", "http://agent-v1.example.com/api/v1/complete"),
    "agent_v2_endpoint": os.getenv("AGENT_V2_ENDPOINT", "http://agent-v2.example.com/api/v1/complete"),
    "api_key_v1": os.getenv("AGENT_V1_API_KEY", ""),
    "api_key_v2": os.getenv("AGENT_V2_API_KEY", ""),
    "instructions_file": "instructions.json",
    "results_dir": "results",
    "timeout": 60,  # seconds
}

class AgentEvaluator:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the evaluator with configuration."""
        self.config = config
        self.instructions = self._load_instructions()
        self.results = []
        self._setup_directories()

    def _load_instructions(self) -> List[Dict[str, Any]]:
        """Load instructions from the JSON file."""
        try:
            with open(self.config["instructions_file"], "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("instructions", [])
        except Exception as e:
            print(f"Error loading instructions: {e}")
            return []

    def _setup_directories(self) -> None:
        """Create necessary directories for storing results."""
        os.makedirs(self.config["results_dir"], exist_ok=True)

    def _call_agent(self, instruction: Dict[str, Any], agent_version: str) -> Dict[str, Any]:
        """Make API call to the specified agent version."""
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
            return {"success": False, "error": str(e)}

    def _calculate_metrics(self, response: str, expected: str) -> Dict[str, float]:
        """Calculate evaluation metrics for the response."""
        # Simple metrics - can be expanded with more sophisticated NLP metrics
        response_words = set(response.lower().split())
        expected_words = set(expected.lower().split())
        
        # Jaccard similarity
        intersection = len(response_words.intersection(expected_words))
        union = len(response_words.union(expected_words))
        jaccard_similarity = intersection / union if union > 0 else 0
        
        return {
            "jaccard_similarity": jaccard_similarity,
            "response_length": len(response),
            "expected_length": len(expected)
        }

    def run_evaluation(self) -> None:
        """Run evaluation on all instructions for both agents."""
        print(f"Starting evaluation of {len(self.instructions)} instructions...\n")
        
        for instruction in self.instructions:
            print(f"\nEvaluating instruction: {instruction['title']} ({instruction['type']})")
            
            # Test agent_v1
            print("  Testing agent_v1...")
            result_v1 = self._evaluate_instruction(instruction, "v1")
            
            # Test agent_v2
            print("  Testing agent_v2...")
            result_v2 = self._evaluate_instruction(instruction, "v2")
            
            # Store results
            self.results.append({
                "instruction_id": instruction["id"],
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
        
        # Call the agent
        start_time = time.time()
        response = self._call_agent(instruction, agent_version)
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
        else:
            print(f"    Error with {agent_version}: {response.get('error', 'Unknown error')}")
        
        return result
    
    def _save_results(self) -> None:
        """Save evaluation results to a CSV file."""
        if not self.results:
            return
            
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(self.results)
        
        # Flatten metrics columns
        for version in ["v1", "v2"]:
            metrics_df = pd.json_normalize(df[f"{version}_metrics"])
            if not metrics_df.empty:
                metrics_df.columns = [f"{version}_{col}" for col in metrics_df.columns]
                df = pd.concat([df.drop([f"{version}_metrics"], axis=1), metrics_df], axis=1)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(self.config["results_dir"]) / f"evaluation_results_{timestamp}.csv"
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")

def main():
    """Main function to run the evaluation."""
    print("GitHub Copilot Agent Evaluation")
    print("=" * 50)
    
    # Initialize and run evaluator
    evaluator = AgentEvaluator(CONFIG)
    evaluator.run_evaluation()
    
    print("\nEvaluation completed!")

if __name__ == "__main__":
    main()
