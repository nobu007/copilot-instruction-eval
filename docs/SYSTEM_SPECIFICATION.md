# GitHub Copilot指示評価システム - 完全仕様書

**最終更新**: 2025-07-21  
**バージョン**: 2.0  
**ステータス**: 運用可能

---

## 🎯 システム概要

### プロジェクト目的
**GitHub Copilot指示評価システムの完全自動化** - AI指示効果を定量評価し、開発効率向上のためのデータ駆動型改善サイクルを確立する統合プラットフォーム

### 戦略的意義
- **内部API活用**: 従来のPyAutoGUI/画面操作から完全転換
- **完全自動化**: ユーザー介入なしでの連続実行
- **定量評価**: BLEU, ROUGE, Jaccard等による客観的評価
- **データ駆動**: 長期的なトレンド分析とパフォーマンス比較

---

## 🏗️ システム構成

### 1. メインプロジェクト (`/home/jinno/copilot-instruction-eval`)

#### 1.1 評価フレームワーク
- **`evaluate_agents.py`**: コマンドライン評価システム
- **`gui_evaluation_script.py`**: GUI評価ツール
- **`instructions.json`**: 評価指示セット定義

#### 1.2 自動化システム群
- **`simple_continuous_executor.py`**: 簡略版連続実行システム（pandas依存なし）
- **`vscode_copilot_continuous_executor.py`**: 完全版連続実行システム
- **`autonomous_vscode_automation.py`**: 完全自律型自動化システム

#### 1.3 データベース・ログ
- **`simple_continuous_execution.db`**: 実行結果SQLiteDB
- **`simple_continuous_execution.log`**: 実行ログ
- **`simple_continuous_execution_report.md`**: 実行レポート

### 2. VSCode拡張機能 (`/vscode-copilot-automation-extension`)

#### 2.1 Phase 1完了済み機能
- ✅ **Agent Mode完全対応**: GitHub Copilot Agent Modeの自動有効化
- ✅ **動的モデル選択**: 利用可能なCopilotモデルの自動検出・選択
- ✅ **WebView統合UI**: 左ペインパネルでの完全制御
- ✅ **内部API通信**: VSCode Language Model API直接アクセス

#### 2.2 技術仕様
- **言語**: TypeScript
- **フレームワーク**: VSCode Extension API
- **出力先**: `.vscode/copilot-automation/`
- **結果ファイル**: `execution_result.json`, `instruction_queue.json`

#### 2.3 サービス構成
- **CopilotService**: Copilot通信管理
- **ModelManager**: モデル選択・管理
- **ModeManager**: Agent/Chatモード切替
- **UIManager**: WebViewUI管理

---

## 🔄 システム動作フロー

### 連続実行システムの動作仕様

#### 1. 初期化フェーズ
```
1. VSCode拡張機能のインストール確認
2. instructions.jsonの読み込み
3. SQLiteデータベースの初期化
4. 実行環境の検証
```

#### 2. 実行フェーズ
```
For each instruction in instructions.json:
  1. VSCode拡張機能にコマンド送信 (command.json)
  2. Agent Modeでプロンプト実行
  3. 結果受信 (.vscode/copilot-automation/execution_result.json)
  4. データベースに結果保存
  5. 次の指示へ移行
```

#### 3. 完了フェーズ
```
1. 実行結果の集計・分析
2. レポート生成 (simple_continuous_execution_report.md)
3. データベースへの永続化
4. ログファイル出力
```

---

## 📊 データ仕様

### 指示セット形式 (`instructions.json`)
```json
{
  "instructions": [
    {
      "id": "code_review_1",
      "type": "code_review",
      "title": "Security Issue in Authentication",
      "description": "Review the following authentication code...",
      "code": "def authenticate(username, password)...",
      "expected_response": "The code has a security vulnerability...",
      "difficulty": "medium"
    }
  ]
}
```

### 実行結果形式 (`execution_result.json`)
```json
{
  "success": true,
  "instruction_id": "code_review_1",
  "response": "Copilot response text...",
  "execution_time": 5.0,
  "timestamp": 1752988344.0304062,
  "model": "copilot/gpt-4",
  "mode": "agent"
}
```

### データベーススキーマ
```sql
CREATE TABLE execution_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instruction_id TEXT NOT NULL,
    instruction_text TEXT NOT NULL,
    mode TEXT NOT NULL,
    model TEXT NOT NULL,
    response TEXT NOT NULL,
    execution_time REAL NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    error_message TEXT,
    metrics TEXT
);
```

---

## 🚀 運用手順

### 基本実行手順

#### 1. 環境確認
```bash
cd /home/jinno/copilot-instruction-eval
code --list-extensions | grep copilot
```

#### 2. 連続実行システム起動
```bash
python3 simple_continuous_executor.py
```

#### 3. 結果確認
```bash
# 実行レポート確認
cat simple_continuous_execution_report.md

# データベース確認
sqlite3 simple_continuous_execution.db "SELECT * FROM execution_results;"

# VSCode拡張機能出力確認
cat .vscode/copilot-automation/execution_result.json
```

### トラブルシューティング

#### 問題1: pandas依存関係エラー
**症状**: `ValueError: numpy.dtype size changed`  
**解決策**: `simple_continuous_executor.py`を使用（pandas依存なし）

#### 問題2: VSCode拡張機能未インストール
**症状**: 拡張機能リストに表示されない  
**解決策**: 
```bash
cd vscode-copilot-automation-extension
make install
```

#### 問題3: Copilot認証エラー
**症状**: モデル選択失敗  
**解決策**: VSCodeでCopilot認証を確認

---

## 📈 評価メトリクス

### 定量評価指標
- **成功率**: 実行成功した指示の割合
- **実行時間**: 指示あたりの平均実行時間
- **応答品質**: BLEU, ROUGE, Jaccard類似度
- **エラー率**: 実行エラーの発生頻度

### 品質基準
- **成功率**: 95%以上
- **平均実行時間**: 10秒以下
- **応答品質**: BLEU > 0.3, ROUGE-L > 0.4

---

## 🔧 技術的詳細

### VSCode拡張機能の内部構造

#### ファイル構成
```
vscode-copilot-automation-extension/
├── src/
│   ├── extension.ts              # メインエントリーポイント
│   ├── services/
│   │   ├── CopilotService.ts     # Copilot通信管理
│   │   ├── ModelManager.ts       # モデル選択管理
│   │   └── ModeManager.ts        # モード切替管理
│   └── ui/
│       ├── UIManager.ts          # WebViewUI管理
│       └── LogDisplayProvider.ts # ログ表示
├── package.json                  # 拡張機能設定
└── copilot-automation-extension-0.0.1.vsix # パッケージ
```

#### 通信プロトコル
1. **コマンド送信**: `command.json`にJSON形式で指示を記録
2. **結果受信**: `.vscode/copilot-automation/execution_result.json`から結果を読み取り
3. **ステータス管理**: `instruction_queue.json`で実行キューを管理

### 依存関係
- **Python**: 3.9+
- **VSCode**: 1.99.0+
- **Node.js**: 20.19.2+
- **拡張機能**: github.copilot, github.copilot-chat

---

## 📋 開発ロードマップ

### Phase 1: 基盤構築 ✅ 完了
- VSCode拡張機能の基本機能
- 連続実行システムの実装
- 基本的な評価メトリクス

### Phase 2: 機能拡張 🚧 進行中
- 高度な評価メトリクス
- Webダッシュボード統合
- CI/CD統合

### Phase 3: 運用最適化 📅 計画中
- パフォーマンス最適化
- セキュリティ強化
- 運用自動化

---

## 📞 サポート・連絡先

### 問題報告
- **GitHub Issues**: プロジェクトリポジトリのIssuesセクション
- **ログ確認**: `simple_continuous_execution.log`
- **デバッグ**: VSCode拡張機能のActivity Monitor

### ドキュメント
- **README.md**: 基本的な使用方法
- **SYSTEM_GOALS.md**: システム設計思想
- **TASKS.md**: 開発進捗・タスク管理

---

*このドキュメントは継続的に更新されます。最新版は常にプロジェクトルートの`docs/SYSTEM_SPECIFICATION.md`を参照してください。*
