# VSCode Copilot Automation System

This project provides a robust and reliable system for automating interactions with GitHub Copilot by directly integrating with a custom VSCode extension. It avoids fragile UI automation in favor of a stable client-server architecture.

For a deep dive into the system's design, please see the [**Architecture Guide**](./docs/ARCHITECTURE_GUIDE.md).

## Core Components

1. **`simple_continuous_executor.py` (The Client):**
   A Python script that orchestrates the automation. It reads instructions from a JSON file, sends them to the VSCode extension, and logs the results.

2. **`vscode-copilot-automation-extension/` (The Server):**
   A custom VSCode extension that listens for requests from the Python client. It uses the official VSCode Language Model API to interact with GitHub Copilot, ensuring high reliability.

3. **`instructions.json`:**
   A file where you define the prompts and tasks you want Copilot to execute.

## 🚀 Quick Start

### システム動作確認

システムが正常に動作しているか確認するには：

```bash
# 1. 基本ヘルスチェック（推奨）
python3 scripts/health_check.py

# 2. 簡単なデモ実行
python3 scripts/demo.py --mode automatic

# 3. 包括的検証（詳細テスト）
python3 scripts/comprehensive_validation.py --quick
```

期待される結果：
```
🏥 SYSTEM STATUS: 🟢 HEALTHY (100%)
🏆 OVERALL SYSTEM STATUS: 🟢 EXCELLENT (100.0%)
```

### 基本的な使用方法

```bash
# シンプルな実行テスト
python3 simple_executor_test.py

# カスタム指示での実行
# instructions.json を編集して実行
python3 simple_continuous_executor.py --run-once --mode chat
```

## 📋 動作確認スクリプト一覧

| スクリプト | 用途 | 実行時間 | 推奨頻度 |
|-----------|------|----------|----------|
| `scripts/health_check.py` | システム全体の基本動作確認 | ~2秒 | 毎日 |
| `scripts/demo.py` | 主要機能のデモンストレーション | ~3分 | 週次 |
| `scripts/comprehensive_validation.py` | 詳細な機能検証 | ~1分 | 月次 |
| `simple_executor_test.py` | 実際の指示実行テスト | ~30秒 | 随時 |

詳細な運用方法は [**運用ガイド**](./docs/OPERATION_GUIDE.md) を参照してください。

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js (for building the extension)
- A local installation of Visual Studio Code

### Setup

1. **Clone the repository:**

   ```bash
   git clone <repository_url>
   cd copilot-instruction-eval
   ```

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Build and Install the VSCode Extension:**

   ```bash
   # Navigate to the extension directory
   cd vscode-copilot-automation-extension

   # Install Node.js dependencies
   npm install

   # Package the extension into a .vsix file
   npm run package

   # Install the extension into your local VSCode
   code --install-extension copilot-automation-extension-0.0.1.vsix
   ```

   *Note: After installation, restart VSCode to ensure the extension is activated.*

## How to Run

1. **Define your tasks** in the `instructions.json` file.

2. **Execute the automation script:**

   The primary script is `simple_continuous_executor.py`. It runs in a "run-once" mode by default, processing all requests in the `/tmp/copilot-evaluation/requests` directory and then exiting.

   ```bash
   # Ensure the IPC directories are clean before starting
   rm -rf /tmp/copilot-evaluation/requests/*
   rm -rf /tmp/copilot-evaluation/responses/*

   # Populate the requests directory from your master instructions file
   # (This is a manual step for now, or can be scripted)
   cp instructions.json /tmp/copilot-evaluation/requests/instruction_set_1.json

   # Run the executor
   python simple_continuous_executor.py --run-once
   ```

3. **Check the results:**
   - A detailed log is created in `simple_continuous_execution.log`.
   - Structured results are saved to a SQLite database: `simple_continuous_execution.db`.

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
