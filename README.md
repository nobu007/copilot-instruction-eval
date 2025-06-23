# GitHub Copilot Agent Evaluation

This repository contains tools and scripts for evaluating different versions of GitHub Copilot agents. It provides a framework for comparing the performance of agent versions using predefined instructions and metrics.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Access to GitHub Copilot agent APIs (v1 and v2)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/copilot-instruction-eval.git
   cd copilot-instruction-eval
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the `.env` file with your API endpoints and keys

## 📋 Project Structure

```
copilot-instruction-eval/
├── .env.example           # Example environment variables
├── requirements.txt       # Python dependencies
├── instructions.json      # Evaluation instructions and test cases
├── evaluate_agents.py     # Main evaluation script
├── test_evaluation.py     # Test cases for the evaluation setup
└── results/               # Directory for evaluation results (created automatically)
```

## 🛠 Usage

### Running the Evaluation

To run the evaluation with the default settings:

```bash
python evaluate_agents.py
```

### Testing the Setup

To verify that everything is set up correctly, run the test suite:

```bash
python -m pytest test_evaluation.py -v
```

## 📊 Evaluation Process

The evaluation process works as follows:

1. Loads instructions from `instructions.json`
2. Sends each instruction to both agent versions (v1 and v2)
3. Collects and compares the responses
4. Calculates metrics such as response similarity and response time
5. Generates a CSV report in the `results/` directory

## 📝 Customizing Instructions

Edit the `instructions.json` file to add, modify, or remove test cases. Each instruction should include:

- `id`: Unique identifier
- `type`: Type of task (e.g., code_review, bug_fix)
- `title`: Short title for the instruction
- `description`: Detailed description of the task
- `code`: (Optional) Code snippet for the task
- `requirements`: (Optional) List of requirements for the task
- `expected_response`: (Optional) Expected response for automated evaluation
- `difficulty`: Difficulty level (easy/medium/hard)

## 📈 Metrics

The evaluation script calculates the following metrics:

- **Jaccard Similarity**: Measures the similarity between the agent's response and the expected response
- **Response Length**: Length of the response in characters
- **Response Time**: Time taken to get a response from the agent

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.