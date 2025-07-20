#!/bin/bash

# VSCode拡張機能 自動ビルド・パッケージ・インストールスクリプト
# Copilot Automation Extension

set -e  # エラー時に即座に終了

echo "🚀 VSCode拡張機能の自動ビルド・インストールを開始..."

# 現在のディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 作業ディレクトリ: $SCRIPT_DIR"

# Step 1: 依存関係のインストール
echo "📦 Step 1: 依存関係をインストール中..."
npm install

# Step 2: TypeScriptコンパイル
echo "🔨 Step 2: TypeScriptをコンパイル中..."
npm run compile

# Step 3: 既存のVSIXファイルを削除（存在する場合）
echo "🗑️  Step 3: 既存のVSIXファイルをクリーンアップ中..."
rm -f *.vsix

# Step 4: 拡張機能をパッケージ化
echo "📦 Step 4: 拡張機能をパッケージ化中..."
vsce package --allow-missing-repository --allow-star-activation

# Step 5: VSIXファイル名を取得
VSIX_FILE=$(ls *.vsix | head -n 1)
if [ -z "$VSIX_FILE" ]; then
    echo "❌ エラー: VSIXファイルが見つかりません"
    exit 1
fi

echo "📄 パッケージファイル: $VSIX_FILE"

# Step 6: 既存の拡張機能をアンインストール（エラーを無視）
echo "🔄 Step 6: 既存の拡張機能をアンインストール中..."
code --uninstall-extension undefined_publisher.copilot-automation-extension || true

# Step 7: 新しい拡張機能をインストール
echo "⚡ Step 7: 新しい拡張機能をインストール中..."
code --install-extension "$VSIX_FILE"

# Step 8: インストール確認
echo "✅ Step 8: インストール確認中..."
if code --list-extensions | grep -q "copilot-automation-extension"; then
    echo "🎉 成功! 拡張機能が正常にインストールされました"
    echo ""
    echo "📋 次の手順:"
    echo "1. VSCodeを再起動してください"
    echo "2. Ctrl+Shift+P でコマンドパレットを開く"
    echo "3. 'Send Automated Prompt to Copilot' を検索"
    echo "4. コマンドが表示されることを確認"
    echo ""
    echo "🔧 利用可能なコマンド:"
    echo "- Send Automated Prompt to Copilot"
    echo "- Get Copilot Chat State"
    echo "- Verify Prompt Was Sent to Copilot"
else
    echo "❌ エラー: 拡張機能のインストールに失敗しました"
    exit 1
fi

echo ""
echo "✨ 自動ビルド・インストール完了!"
