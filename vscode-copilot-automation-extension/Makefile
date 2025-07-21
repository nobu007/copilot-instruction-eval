# VSCode Copilot Automation Extension - Makefile
# 開発・ビルド・インストールの自動化

.PHONY: help install build package clean dev watch test uninstall reinstall

# デフォルトターゲット
help:
	@echo "🚀 VSCode Copilot Automation Extension - Make Commands"
	@echo ""
	@echo "📦 Build & Install:"
	@echo "  make install     - フルビルド・パッケージ・インストール"
	@echo "  make reinstall   - アンインストール後に再インストール"
	@echo "  make build       - TypeScriptコンパイルのみ"
	@echo "  make package     - VSIXパッケージ作成のみ"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean       - ビルド成果物をクリーンアップ"
	@echo "  make uninstall   - 拡張機能をアンインストール"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make dev         - 開発モード（watch + 自動再インストール）"
	@echo "  make watch       - TypeScript watch モード"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test        - 拡張機能のテスト実行"

# 依存関係インストール
deps:
	@echo "📦 Installing dependencies..."
	npm install

# TypeScriptコンパイル
build: deps
	@echo "🔨 Compiling TypeScript..."
	npm run compile

# VSIXパッケージ作成
package: build clean-vsix
	@echo "📦 Creating VSIX package..."
	vsce package --allow-missing-repository --allow-star-activation

# 拡張機能インストール（フルプロセス）
install: package
	@echo "⚡ Installing extension..."
	@$(MAKE) uninstall || true
	@VSIX_FILE=$$(ls *.vsix | head -n 1); \
	if [ -n "$$VSIX_FILE" ]; then \
		echo "Installing $$VSIX_FILE..."; \
		code --install-extension "$$VSIX_FILE"; \
		echo "✅ Extension installed successfully!"; \
		echo ""; \
		echo "🔄 Reloading VSCode window..."; \
		$(MAKE) reload-vscode; \
		echo "✅ VSCode reloaded! Extension is ready to use."; \
	else \
		echo "❌ No VSIX file found!"; \
		exit 1; \
	fi

# VSCodeウィンドウリロード (via Singleton Manager)
reload-vscode:
	@echo "🔄 Safely reloading VSCode via Singleton Process Manager..."
	@python3 ../scripts/reload_helper.py

# 拡張機能アンインストール
uninstall:
	@echo "🗑️ Uninstalling existing extension..."
	@code --uninstall-extension undefined_publisher.copilot-automation-extension || true
	@code --uninstall-extension windsurf-dev.copilot-automation-extension || true

# 再インストール
reinstall: uninstall install

# VSIXファイルクリーンアップ
clean-vsix:
	@echo "🗑️ Cleaning up old VSIX files..."
	@rm -f *.vsix

# 全クリーンアップ
clean: clean-vsix
	@echo "🧹 Cleaning up build artifacts..."
	@rm -rf out/
	@rm -rf node_modules/

# 開発モード（watch + 自動再インストール）
dev:
	@echo "🔧 Starting development mode..."
	@echo "TypeScript will be compiled in watch mode."
	@echo "Run 'make reinstall' in another terminal when you want to test changes."
	npm run watch

# TypeScript watch モード
watch:
	@echo "👀 Starting TypeScript watch mode..."
	npm run watch

# テスト実行
test: build
	@echo "🧪 Running tests..."
	@echo "Testing extension installation..."
	@if code --list-extensions | grep -q "copilot-automation-extension"; then \
		echo "✅ Extension is installed"; \
	else \
		echo "❌ Extension is not installed"; \
		exit 1; \
	fi

# 拡張機能の状態確認
status:
	@echo "📊 Extension Status:"
	@echo "Installed extensions:"
	@code --list-extensions | grep -i copilot || echo "No copilot extensions found"
	@echo ""
	@echo "VSIX files in current directory:"
	@ls -la *.vsix 2>/dev/null || echo "No VSIX files found"

# 開発環境セットアップ
setup:
	@echo "🛠️ Setting up development environment..."
	@$(MAKE) deps
	@echo "Installing vsce globally..."
	@npm install -g @vscode/vsce || echo "vsce already installed or permission denied"
	@echo "✅ Development environment ready!"
