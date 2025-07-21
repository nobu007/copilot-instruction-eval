# VSCode Copilot Automation System - 運用ガイド

このドキュメントは、VSCode Copilot自動実行システムの日常的な操作と動作確認方法を説明します。

## 📋 目次

1. [クイックスタート](#クイックスタート)
2. [動作確認スクリプト](#動作確認スクリプト)
3. [システム監視](#システム監視)
4. [トラブルシューティング](#トラブルシューティング)
5. [メンテナンス](#メンテナンス)

## クイックスタート

### 前提条件確認

1. **VSCode拡張のインストール状況確認**
```bash
code --list-extensions | grep -E "(copilot|automation)"
```
期待される出力：
- `github.copilot`
- `github.copilot-chat` 
- `windsurf-dev.copilot-automation-extension` (または類似)

2. **基本ディレクトリ構造確認**
```bash
ls -la /tmp/copilot-evaluation/
```
期待される構造：
```
/tmp/copilot-evaluation/
├── requests/     # リクエストファイル
├── responses/    # レスポンスファイル
├── failed/       # 失敗したリクエスト
└── logs/         # ログファイル
```

### 最初の動作確認

```bash
# 1. ヘルスチェック実行
python3 scripts/health_check.py

# 2. 正常な場合のサンプル実行
python3 simple_executor_test.py
```

## 動作確認スクリプト

システムには4つの主要な動作確認スクリプトが用意されています。

### 1. ヘルスチェック（health_check.py）

**目的**: システム全体の基本動作状況を迅速に確認

```bash
# 基本実行
python3 scripts/health_check.py

# 期待される出力例
🏥 === SYSTEM HEALTH CHECK START ===
✅ /tmp/copilot-evaluation
✅ Extension directory: vscode-copilot-automation-extension
✅ VSCode extension host running
✅ GitHub Copilot extension
✅ Ping response received in 2s
🏥 SYSTEM STATUS: 🟢 HEALTHY (100%)
```

**チェック項目**:
- IPCディレクトリ構造
- VSCode拡張の存在・コンパイル状況
- VSCodeプロセスの動作状況
- GitHub Copilot拡張のインストール
- Ping通信テスト
- データベース構造
- 指示ファイルの存在

**異常時の対処**:
- 🔴 CRITICAL (70%未満): システム再起動が必要
- 🟡 DEGRADED (70-90%): 一部機能に問題、調査が必要
- 🟢 HEALTHY (90%以上): 正常動作

### 2. デモンストレーション（demo.py）

**目的**: システムの主要機能を実演・確認

```bash
# 対話型デモ（推奨）
python3 scripts/demo.py --mode interactive

# 自動デモ
python3 scripts/demo.py --mode automatic
```

**デモ内容**:
1. 基本応答テスト
2. コード生成テスト
3. 説明機能テスト
4. セキュリティ知識テスト
5. コードレビューテスト

**対話型デモの操作**:
- `Enter`: 次のステップを実行
- `s`: 現在のステップをスキップ
- `q`: デモを終了

### 3. 包括的検証（comprehensive_validation.py）

**目的**: システム全体の詳細な動作検証

```bash
# 完全検証（推奨）
python3 scripts/comprehensive_validation.py

# クイック検証（基本機能のみ）
python3 scripts/comprehensive_validation.py --quick

# 既存結果からレポート生成のみ
python3 scripts/comprehensive_validation.py --report-only
```

**検証カテゴリ**:
- **connectivity**: 基本接続・応答性
- **functionality**: コア機能
- **error_handling**: エラー処理・例外条件
- **performance**: 応答時間・スループット
- **reliability**: 一貫性・障害回復

**期待される結果**:
```
🧪 COMPREHENSIVE VALIDATION SUMMARY
📊 Success Rate: 95.0%
🟢 EXCELLENT (95.0%)
```

### 4. 簡易統合テスト（simple_executor_test.py）

**目的**: 実際の指示実行フローの確認

```bash
# デフォルト指示セットでの実行
python3 simple_executor_test.py

# カスタム指示ファイル指定
# (スクリプト内のinstructions_fileを変更)
```

## システム監視

### リアルタイム監視

```bash
# IPC通信の監視
watch -n 1 "ls -la /tmp/copilot-evaluation/requests/ /tmp/copilot-evaluation/responses/"

# VSCodeプロセス監視
watch -n 5 "ps aux | grep -E 'extensionHost|code' | grep -v grep"

# ログファイル監視
tail -f /tmp/copilot-evaluation/logs/system.log
```

### パフォーマンス確認

```bash
# データベース内の実行統計
sqlite3 simple_continuous_execution.db "
SELECT 
    status,
    COUNT(*) as count,
    AVG(execution_time) as avg_time,
    MAX(execution_time) as max_time
FROM execution_results 
GROUP BY status;
"
```

### ディスク使用量監視

```bash
# IPCディレクトリのサイズ確認
du -sh /tmp/copilot-evaluation/

# 古いファイルのクリーンアップ（必要に応じて）
find /tmp/copilot-evaluation/failed/ -name "*.json" -mtime +7 -delete
```

## トラブルシューティング

### 一般的な問題と対処法

#### 1. Ping応答が無い

**症状**: `health_check.py`でPingテストが失敗

**対処法**:
```bash
# VSCode拡張ホストの再起動
# 1. 現在のプロセス確認
ps aux | grep extensionHost

# 2. VSCode再起動（必要に応じて）
code --reload-window

# 3. 拡張の再インストール
cd vscode-copilot-automation-extension
make install
```

#### 2. submitPromptが失敗する

**症状**: 「Response got filtered」エラー

**対処法**:
```bash
# 1. シンプルなプロンプトでテスト
echo '{"request_id": "test", "command": "submitPrompt", "params": {"prompt": "hello"}}' > /tmp/copilot-evaluation/requests/test.json

# 2. 応答確認
sleep 5 && cat /tmp/copilot-evaluation/responses/test.json

# 3. Copilotの認証状況確認
code --status
```

#### 3. データベースエラー

**症状**: SQLiteエラーまたはスキーマ不整合

**対処法**:
```bash
# 1. データベーススキーマ確認
sqlite3 simple_continuous_execution.db ".schema execution_results"

# 2. データベース再作成
rm -f simple_continuous_execution.db
python3 simple_executor_test.py  # 新しいDBが作成される
```

#### 4. VSCodeプロセス関連の問題

**症状**: 拡張ホストが見つからない

**対処法**:
```bash
# 1. VSCodeプロセス全体の確認
ps aux | grep code

# 2. 拡張開発モードでの起動
code . --extensionDevelopmentPath=./vscode-copilot-automation-extension

# 3. システム全体の再起動（最後の手段）
sudo systemctl restart --user code-server  # 必要に応じて
```

### ログ分析

```bash
# システムログの確認
tail -100 /tmp/copilot-evaluation/logs/system.log

# エラーパターンの検索
grep -i error /tmp/copilot-evaluation/logs/system.log

# 特定期間のログ抽出
grep "2025-07-22" /tmp/copilot-evaluation/logs/system.log
```

## メンテナンス

### 日次メンテナンス

```bash
#!/bin/bash
# daily_maintenance.sh

# 1. ヘルスチェック実行
echo "=== Daily Health Check ==="
python3 scripts/health_check.py

# 2. 古いファイルのクリーンアップ
echo "=== Cleanup Old Files ==="
find /tmp/copilot-evaluation/failed/ -name "*.json" -mtime +7 -delete
find . -name "*.db" -size +100M -mtime +30 -delete

# 3. ディスク使用量確認
echo "=== Disk Usage ==="
df -h /tmp
du -sh /tmp/copilot-evaluation/

echo "=== Maintenance Complete ==="
```

### 週次メンテナンス

```bash
# 1. 包括的検証実行
python3 scripts/comprehensive_validation.py

# 2. パフォーマンス統計の確認
sqlite3 simple_continuous_execution.db "
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_requests,
    AVG(execution_time) as avg_response_time,
    COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM execution_results 
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY date;
"

# 3. システムアップデート確認（必要に応じて）
code --update-extensions
```

### バックアップ

```bash
# 重要データのバックアップ
backup_dir="backup_$(date +%Y%m%d)"
mkdir -p "$backup_dir"

# データベースバックアップ
cp *.db "$backup_dir/"

# 設定ファイルバックアップ
cp -r vscode-copilot-automation-extension/out "$backup_dir/"
cp *.json "$backup_dir/"

# アーカイブ作成
tar -czf "$backup_dir.tar.gz" "$backup_dir"
rm -rf "$backup_dir"

echo "Backup created: $backup_dir.tar.gz"
```

## パフォーマンス調整

### 応答時間の最適化

```bash
# 1. IPCポーリング間隔の調整
# vscode-copilot-automation-extension/package.json の設定:
"copilotAutomation.pollingInterval": 500  # デフォルト: 1000ms

# 2. タイムアウト値の調整
# スクリプト内のtimeout値を環境に応じて調整

# 3. 並列処理の有効化（将来の拡張）
# 複数リクエストの同時処理を検討
```

### リソース使用量の監視

```bash
# CPU・メモリ使用量
top -p $(pgrep -f extensionHost)

# ファイルディスクリプタ使用量
lsof -p $(pgrep -f extensionHost) | wc -l
```

---

## 📞 サポート情報

### 問題報告時の情報収集

問題が発生した場合、以下の情報を収集してください：

```bash
# システム情報パッケージ
./scripts/collect_support_info.sh > support_info_$(date +%Y%m%d_%H%M%S).txt
```

### よくある質問（FAQ）

**Q: システムが応答しない場合は？**
A: まず`health_check.py`を実行し、各コンポーネントの状況を確認してください。

**Q: 応答時間が遅い場合は？**
A: `comprehensive_validation.py`のperformanceカテゴリで具体的な応答時間を測定し、ボトルネックを特定してください。

**Q: 特定のプロンプトで失敗が多い場合は？**
A: Copilotのコンテンツフィルターが作動している可能性があります。よりシンプルなプロンプトでテストしてください。

---

**📝 ドキュメント更新**: 2025-07-22  
**📧 管理者**: システム管理担当者  
**🔗 関連ドキュメント**: [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md), [TASKS.md](TASKS.md)