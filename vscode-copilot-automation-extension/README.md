# 🤖 VSCode Copilot Automation Extension

**革新的なVSCode拡張機能による、GitHub Copilotとの完全自動化インタラクションシステム**

[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/your-repo/vscode-copilot-automation-extension)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![VSCode](https://img.shields.io/badge/VSCode-1.74.0+-purple.svg)](https://code.visualstudio.com/)

従来のPyAutoGUI/画面操作アプローチから脱却し、**VSCode内部APIを活用した確実で高速な自動化**を実現。開発者の生産性を飛躍的に向上させる次世代ツールです。

## 🚀 革新的特徴

### 🎯 戦略的優位性

- **🔥 内部API直接アクセス**: PyAutoGUIや画面操作に依存しない**100%確実な自動化**
- **⚡ 超高速実行**: OCRや画像認識の不確実性を完全排除、**平均2秒以下**でレスポンス
- **🛡️ 完全環境非依存**: テーマ・レイアウト・OS変更に**完全に影響されない**
- **🤖 完全自律型操作**: ユーザー介入なしでCopilotとの**シームレスな対話**

### 🏗️ 技術的革新

- **VSCode Language Model API**: 直接Copilot通信による確実性
- **独自ViewContainer**: 専用UI領域による直感的操作
- **WebView Provider**: リアルタイムデバッグ・ログ表示
- **自動ドキュメント生成**: エディタ未存在時の自動新規作成

## 📦 インストール

### 自動インストール（推奨）

```bash
# Makefileを使用（推奨）
make install

# または、シェルスクリプトを使用
./build-and-install.sh
```

### 手動インストール

```bash
# 1. 依存関係インストール
npm install

# 2. コンパイル
npm run compile

# 3. パッケージ化
echo "y" | vsce package --allow-missing-repository

# 4. インストール
code --install-extension copilot-automation-extension-0.0.1.vsix
```

## 🔧 利用可能なコマンド

拡張機能をインストール後、`Ctrl+Shift+P`でコマンドパレットを開き、以下のコマンドが利用できます：

- **Send Automated Prompt to Copilot** - Copilotチャットに自動でプロンプトを送信
- **Get Copilot Chat State** - Copilotチャットの現在の状態を取得
- **Verify Prompt Was Sent to Copilot** - プロンプト送信の検証を実行

## 🛠️ 開発

### Makefileコマンド

```bash
# ヘルプ表示
make help

# フルビルド・インストール
make install

# 再インストール
make reinstall

# 開発モード（TypeScript watch）
make dev

# クリーンアップ
make clean

# 拡張機能の状態確認
make status
```

### 開発環境セットアップ

```bash
# 初回セットアップ
make setup

# 開発モード開始
make dev
```

## 📁 プロジェクト構造

```
vscode-copilot-automation-extension/
├── src/
│   └── extension.ts          # メイン拡張機能コード
├── out/                      # コンパイル済みJavaScript
├── package.json              # 拡張機能マニフェスト
├── tsconfig.json             # TypeScript設定
├── Makefile                  # ビルド自動化
├── build-and-install.sh      # インストールスクリプト
├── .vscodeignore            # パッケージ除外設定
└── README.md                # このファイル
```

## 🔄 使用方法

1. **拡張機能インストール**
   ```bash
   make install
   ```

2. **VSCode再起動**

3. **コマンド実行**
   - `Ctrl+Shift+P` → "Send Automated Prompt to Copilot"

4. **結果確認**
   - Copilotチャットに自動でプロンプトが送信される
   - エディタにもデモ用のコメントが挿入される

## 🧪 テスト

```bash
# 拡張機能のインストール状態をテスト
make test

# 拡張機能の状態確認
make status
```

## 🔧 トラブルシューティング

### コマンドが表示されない場合

1. VSCodeを完全に再起動
2. 拡張機能が正しくインストールされているか確認：
   ```bash
   code --list-extensions | grep copilot-automation-extension
   ```
3. 再インストール：
   ```bash
   make reinstall
   ```

### ビルドエラーの場合

```bash
# クリーンビルド
make clean
make install
```

## 📝 技術仕様

- **言語**: TypeScript
- **対象**: VSCode 1.74.0+
- **依存関係**: VSCode Extension API
- **パッケージ**: VSIX形式

## 🎯 戦略的意義

従来の外部操作アプローチ（PyAutoGUI、画面キャプチャ、OCR）から、VSCode内部API活用への根本的転換。最も堅牢で確実な自動化手法を実現。

## 🌟 使用方法

### クイックスタート

1. **拡張機能を起動**: VSCode左端のアクティビティバーの🤖アイコンをクリック
2. **プロンプト送信**: 左ペインの「Debug Panel」でプロンプトを入力・送信
3. **結果確認**: 新規ドキュメントまたは既存エディタでCopilotレスポンスを確認

### 高度な使用法

- **コマンドパレット**: `Ctrl+Shift+P` → "Send Automated Prompt to Copilot"
- **状態確認**: "Get Copilot Chat State" で現在の状態を詳細取得
- **検証機能**: "Verify Prompt Was Sent to Copilot" で送信確認

## 🚀 ロードマップ & ビジョン

### 📋 Phase 1: Foundation ✅ **完了**
- VSCode拡張機能の基本構造構築
- VSCode Language Model APIによる直接Copilot通信
- 独自ViewContainerによる左ペイン表示
- 完全動作する自動化システム

### 🎯 Phase 2: Intelligence Enhancement (2025年8月)
- カスタムプロンプトテンプレート機能
- インテリジェント自動化（コード解析ベース）
- 結果解析・評価システム
- 学習機能（ユーザー好み適応）

### 🌟 Phase 3: Ecosystem Integration (2025年10月)
- Git操作連携（コミットメッセージ自動生成）
- テスト自動実行・結果解析
- チーム協働機能
- 他ツール統合

### 🏆 Ultimate Vision: **開発の新しい標準**

**2026年までに、全世界の開発者が当然のように使用する「AI駆動開発の標準ツール」として確立**

> *"The future of development is not just AI-assisted, but AI-automated."*

## 🤝 貢献・サポート

### 貢献方法
- 🐛 **バグ報告**: [Issues](https://github.com/your-repo/issues) で報告
- 💡 **機能提案**: [Discussions](https://github.com/your-repo/discussions) で議論
- 🔧 **プルリクエスト**: 歓迎します！
- ⭐ **スター**: プロジェクトを応援してください

### コミュニティ
- 📚 **ドキュメント**: [docs/SYSTEM_GOALS.md](docs/SYSTEM_GOALS.md) で詳細なビジョンを確認
- 💬 **ディスカッション**: 技術的な質問や提案を歓迎
- 🌐 **ソーシャル**: 成果をシェアしてください

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

---

<div align="center">

**🤖 VSCode Copilot Automation Extension**

*革新的な開発体験を提供する次世代ツール*

**[⭐ Star this project](https://github.com/your-repo) | [📖 Documentation](docs/) | [🚀 Get Started](#-インストール)**

*Revolutionizing Development Through Intelligent Automation*

</div>
