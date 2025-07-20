# VSCode Copilot Automation Extension

VSCode内部APIを使用してGitHub Copilotとの確実な自動化を実現するVSCode拡張機能です。

## 🚀 特徴

- **内部API直接アクセス**: PyAutoGUIや画面操作に依存しない確実な自動化
- **テーマ・レイアウト非依存**: VSCodeのテーマやレイアウト変更に影響されない
- **高速・高精度**: OCRや画像認識の不確実性を排除した確実な操作
- **完全自動化**: ユーザー介入なしでCopilotチャットにプロンプトを送信

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

## 📄 ライセンス

MIT License
