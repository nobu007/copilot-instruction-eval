# GitHub Copilot Agent Evaluation Report

Generated at: 2025-06-24T12:25:40.198186

## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Instructions | 5 |
| Agent v1 Success Rate | 100.0% (5/5) |
| Agent v2 Success Rate | 0.0% (0/5) |
| Improvement | -100.0% points |

## 📈 Success Rate Comparison

![Success Rate Comparison](success_rate_comparison.png)

## 📊 Metrics Comparison

### Average Metrics
| Metric | Agent v1 | Agent v2 | Difference |
|--------|----------|----------|------------|
| jaccard_similarity | 0.024 | 0.000 | -0.024 |
| bleu_score | 0.002 | 0.000 | -0.002 |
| rouge_1 | 0.045 | 0.000 | -0.045 |
| rouge_2 | 0.008 | 0.000 | -0.008 |
| rouge_l | 0.042 | 0.000 | -0.042 |
| response_time (s) | 10.282 | 0.000 | -10.282 |

![Metrics Comparison](metrics_comparison.png)

## 📋 Detailed Results

<details><summary>Click to expand detailed results</summary>

| ID | Type | Difficulty | v1 Success | v2 Success | v1 Jaccard | v2 Jaccard | v1 BLEU | v2 BLEU | v1 ROUGE-L | v2 ROUGE-L | v1 Time (s) | v2 Time (s) |
|----|------|------------|------------|------------|------------|------------|---------|---------|------------|------------|-------------|-------------|
| bug_fix_1 | bug_fix | hard | ✅ | ❌ | 0.037 | 0.000 | 0.004 | 0.000 | 0.067 | 0.000 | 4.71 | 0.00 |
| code_review_1 | code_review | medium | ✅ | ❌ | 0.036 | 0.000 | 0.003 | 0.000 | 0.074 | 0.000 | 9.05 | 0.00 |
| pr_creation_1 | pr_creation | easy | ✅ | ❌ | 0.008 | 0.000 | 0.001 | 0.000 | 0.016 | 0.000 | 18.27 | 0.00 |
| refactor_1 | refactoring | easy | ✅ | ❌ | 0.026 | 0.000 | 0.002 | 0.000 | 0.034 | 0.000 | 4.54 | 0.00 |
| test_case_1 | test_creation | medium | ✅ | ❌ | 0.013 | 0.000 | 0.001 | 0.000 | 0.022 | 0.000 | 14.84 | 0.00 |
</details>

## ⚙️ Configuration

<details><summary>Click to view evaluation configuration</summary>

```json
{
  "agent_v1_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
  "agent_v2_endpoint": "https://api.groq.com/openai/v1/chat/completion/meta-llama/llama-4-maverick-17b-128e-instruct",
  "api_key_v1": "***REDACTED***",
  "api_key_v2": "***REDACTED***",
  "instructions_file": "instructions.json",
  "results_dir": "results",
  "timeout": 60,
  "max_retries": 3,
  "retry_delay": 5
}
```
</details>
