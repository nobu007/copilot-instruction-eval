# GitHub Copilot Agent Evaluation

This project provides a framework for evaluating and comparing different versions of GitHub Copilot Agents. It automates the process of sending instructions to agents, collecting their responses, and analyzing the results using various metrics.

## Features

- **Automated Evaluation:** Runs predefined tasks (`code_review`, `bug_fix`, etc.) on multiple agents.
- **Performance Metrics:** Calculates scores like BLEU and ROUGE to objectively measure performance.
- **Comparative Reporting:** Generates reports and visualizations to compare agent capabilities.
- **Extensible:** Easily add new evaluation instructions or agents.
- **GUI and CLI:** Supports both a command-line script (`evaluate_agents.py`) and a GUI-based evaluation tool (`gui_evaluation_script.py`).

## Getting Started

### Prerequisites

- Python 3.9+
- Git

### Setup

1. **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd copilot-instruction-eval
    ```

2. **Install dependencies:**

    Create a virtual environment (recommended) and install the required packages.

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3. **Configure environment variables:**

    Copy the example environment file and fill in your API keys and endpoints.

    ```bash
    cp .env.example .env
    ```

    Now, edit the `.env` file with your actual credentials.

## How to Run

### Command-Line Evaluation

To run the full evaluation suite from the command line:

```bash
python evaluate_agents.py
```

The results, including logs and comparison charts, will be saved in the `results/` directory.

### GUI-Based Evaluation

For interactive evaluation, you can use the GUI script:

```bash
python gui_evaluation_script.py
```

This will launch a Tkinter window allowing you to send instructions and view agent responses in real-time.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
