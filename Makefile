# VSCode Copilot Automation Project - Root Makefile
# プロジェクトルートからの統合ビルド・管理

# 拡張機能ディレクトリ
EXTENSION_DIR = vscode-copilot-automation-extension

.PHONY: help install build package clean dev watch test uninstall reinstall status setup

# デフォルトターゲット
help:
	@echo "🚀 VSCode Copilot Automation Project"
	@echo ""
	@echo "📦 Extension Management:"
	@echo "  make install     - VSCode拡張機能をビルド・インストール"
	@echo "  make reinstall   - 拡張機能を再インストール"
	@echo "  make uninstall   - 拡張機能をアンインストール"
	@echo "  make build       - 拡張機能をビルドのみ"
	@echo "  make package     - VSIXパッケージ作成のみ"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean       - ビルド成果物をクリーンアップ"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make dev         - 開発モード（TypeScript watch）"
	@echo "  make watch       - TypeScript watch モード"
	@echo "  make setup       - 開発環境セットアップ"
	@echo ""
	@echo "🧪 Testing & Status:"
	@echo "  make test        - 拡張機能テスト実行"
	@echo "  make status      - 拡張機能の状態確認"
	@echo ""
	@echo "📁 Project Structure:"
	@echo "  $(EXTENSION_DIR)/ - VSCode拡張機能"
	@echo ""
	@echo "💡 Quick Start:"
	@echo "  make setup && make install"

# 拡張機能のフルビルド・インストール
install:
	@echo "🚀 Installing VSCode Copilot Automation Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) install

# 拡張機能の再インストール
reinstall:
	@echo "🔄 Reinstalling VSCode Copilot Automation Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) reinstall

# 拡張機能のアンインストール
uninstall:
	@echo "🗑️ Uninstalling VSCode Copilot Automation Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) uninstall

# 拡張機能のビルド
build:
	@echo "🔨 Building VSCode Copilot Automation Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) build

# 拡張機能のパッケージ化
package:
	@echo "📦 Packaging VSCode Copilot Automation Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) package

# クリーンアップ
clean:
	@echo "🧹 Cleaning up project..."
	@cd $(EXTENSION_DIR) && $(MAKE) clean

# 開発モード
dev:
	@echo "🔧 Starting development mode for VSCode Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) dev

# TypeScript watch モード
watch:
	@echo "👀 Starting TypeScript watch mode..."
	@cd $(EXTENSION_DIR) && $(MAKE) watch

# テスト実行
test:
	@echo "🧪 Running tests for VSCode Extension..."
	@cd $(EXTENSION_DIR) && $(MAKE) test

# 拡張機能の状態確認
status:
	@echo "📊 VSCode Extension Status:"
	@cd $(EXTENSION_DIR) && $(MAKE) status

# 開発環境セットアップ
setup:
	@echo "🛠️ Setting up development environment..."
	@cd $(EXTENSION_DIR) && $(MAKE) setup
	@echo ""
	@echo "✅ Development environment setup complete!"
	@echo ""
	@echo "🎯 Next steps:"
	@echo "  make install    # Install the extension"
	@echo "  make dev        # Start development mode"

# プロジェクト全体の状態確認
info:
	@echo "📋 Project Information:"
	@echo "  Project Root: $(shell pwd)"
	@echo "  Extension Dir: $(EXTENSION_DIR)"
	@echo ""
	@echo "📁 Directory Structure:"
	@find . -maxdepth 2 -type d -name ".*" -prune -o -type d -print | head -10
	@echo ""
	@echo "📦 VSCode Extensions:"
	@code --list-extensions | grep -i copilot || echo "  No copilot extensions found"

# 高速インストール（開発用）
quick:
	@echo "⚡ Quick install (development mode)..."
	@cd $(EXTENSION_DIR) && ./build-and-install.sh

# プロジェクト全体のクリーンアップ
deep-clean: clean
	@echo "🧹 Deep cleaning project..."
	@find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.vsix" -type f -delete 2>/dev/null || true
	@echo "✅ Deep clean complete!"
