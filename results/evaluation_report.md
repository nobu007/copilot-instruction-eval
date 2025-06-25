# GitHub Copilot Agent Evaluation Report

Generated at: 2025-06-25T19:51:12.429792

## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Instructions | 5 |
| Agent v1 Success Rate | 100.0% (5/5) |
| Agent v2 Success Rate | 100.0% (5/5) |
| Improvement | +0.0% points |

## 📈 Success Rate Comparison

![Success Rate Comparison](success_rate_comparison.png)

## 📊 Metrics Comparison

### Average Metrics
| Metric | Agent v1 | Agent v2 | Difference |
|--------|----------|----------|------------|
| jaccard_similarity | 0.020 | 0.040 | +0.020 |
| bleu_score | 0.002 | 0.004 | +0.001 |
| rouge_1 | 0.039 | 0.066 | +0.027 |
| rouge_2 | 0.005 | 0.013 | +0.007 |
| rouge_l | 0.038 | 0.066 | +0.028 |
| response_time (s) | 11.855 | 1.605 | -10.250 |

![Metrics Comparison](metrics_comparison.png)

## 📋 Detailed Results

<details><summary>Click to expand detailed results</summary>

| ID | Type | Difficulty | v1 Success | v2 Success | v1 Jaccard | v2 Jaccard | v1 BLEU | v2 BLEU | v1 ROUGE-L | v2 ROUGE-L | v1 Time (s) | v2 Time (s) |
|----|------|------------|------------|------------|------------|------------|---------|---------|------------|------------|-------------|-------------|
| bug_fix_1 | bug_fix | hard | ✅ | ✅ | 0.023 | 0.052 | 0.004 | 0.008 | 0.043 | 0.085 | 6.03 | 1.19 |
| code_review_1 | code_review | medium | ✅ | ✅ | 0.037 | 0.047 | 0.004 | 0.004 | 0.077 | 0.100 | 8.64 | 1.38 |
| pr_creation_1 | pr_creation | easy | ✅ | ✅ | 0.011 | 0.035 | 0.001 | 0.002 | 0.019 | 0.034 | 17.83 | 2.02 |
| refactor_1 | refactoring | easy | ✅ | ✅ | 0.021 | 0.039 | 0.001 | 0.003 | 0.033 | 0.060 | 6.23 | 1.31 |
| test_case_1 | test_creation | medium | ✅ | ✅ | 0.009 | 0.026 | 0.001 | 0.002 | 0.017 | 0.049 | 20.55 | 2.13 |
</details>

## ⚙️ Configuration

<details><summary>Click to view evaluation configuration</summary>

```json
{
  "agent_v1_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
  "agent_v2_endpoint": "https://api.groq.com/openai/v1/chat/completions/meta-llama/llama-4-maverick-17b-128e-instruct",
  "agent_v2_model": null,
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
