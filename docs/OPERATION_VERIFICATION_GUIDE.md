# システム動作確認ガイド

**目的**: GitHub Copilot指示評価システムの実際の動作を段階的に検証する  
**対象**: システム管理者・開発者・品質保証担当者  
**最終更新**: 2025-07-21

---

## 🔍 動作確認の原則

### 事実ベース検証
- **ログファイル**: 実際の出力を確認
- **データベース**: 保存されたデータを検証
- **結果ファイル**: VSCode拡張機能の出力を確認
- **プロセス監視**: 実行中のシステム状態を観察

### 検証レベル
1. **Level 1**: 基本動作確認（環境・インストール）
2. **Level 2**: 単体機能確認（個別コンポーネント）
3. **Level 3**: 統合動作確認（システム全体）
4. **Level 4**: 連続実行確認（実運用シミュレーション）

---

## 📋 Level 1: 基本動作確認

### 1.1 環境確認

#### Python環境
```bash
cd /home/jinno/copilot-instruction-eval
python3 --version
# 期待値: Python 3.9+
```

#### VSCode拡張機能確認
```bash
code --list-extensions | grep copilot
# 期待値: 
# github.copilot
# github.copilot-chat
# undefined_publisher.copilot-automation-extension
```

#### プロジェクト構造確認
```bash
ls -la /home/jinno/copilot-instruction-eval/
# 期待値: simple_continuous_executor.py, instructions.json等が存在
```

### 1.2 依存関係確認

#### 必須ファイル存在確認
```bash
# 指示セットファイル
test -f instructions.json && echo "✅ instructions.json存在" || echo "❌ instructions.json不存在"

# VSCode拡張機能パッケージ
test -f vscode-copilot-automation-extension/copilot-automation-extension-0.0.1.vsix && echo "✅ 拡張機能パッケージ存在" || echo "❌ 拡張機能パッケージ不存在"

# 連続実行システム
test -f simple_continuous_executor.py && echo "✅ 連続実行システム存在" || echo "❌ 連続実行システム不存在"
```

---

## 🔧 Level 2: 単体機能確認

### 2.1 VSCode拡張機能単体テスト

#### 拡張機能インストール確認
```bash
cd vscode-copilot-automation-extension
# 拡張機能が正しくインストールされているか確認
code --list-extensions | grep copilot-automation-extension
# 期待値: undefined_publisher.copilot-automation-extension
```

#### 出力ディレクトリ確認
```bash
# VSCode拡張機能の出力先ディレクトリ
ls -la .vscode/copilot-automation/
# 期待値: execution_result.json, instruction_queue.json等
```

### 2.2 指示セット読み込みテスト

#### 指示セット構文確認
```bash
python3 -c "
import json
with open('instructions.json', 'r') as f:
    data = json.load(f)
    print(f'✅ 指示セット読み込み成功: {len(data[\"instructions\"])}件')
    for inst in data['instructions']:
        print(f'  - {inst[\"id\"]}: {inst[\"type\"]}')
"
```

### 2.3 データベース接続テスト

#### SQLite接続確認
```bash
python3 -c "
import sqlite3
import os
db_path = 'simple_continuous_execution.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\";')
    tables = cursor.fetchall()
    print(f'✅ データベース接続成功')
    print(f'テーブル: {[t[0] for t in tables]}')
    conn.close()
except Exception as e:
    print(f'❌ データベース接続失敗: {e}')
"
```

---

## 🔄 Level 3: 統合動作確認

### 3.1 単一指示実行テスト

#### テスト用指示ファイル作成
```bash
cat > test_single_instruction.json << 'EOF'
{
  "instructions": [
    {
      "id": "test_single",
      "type": "test",
      "title": "Single Instruction Test",
      "description": "This is a test instruction to verify single execution.",
      "expected_response": "Test response",
      "difficulty": "easy"
    }
  ]
}
EOF
```

#### 単一指示実行
```bash
# バックアップ作成
cp instructions.json instructions.json.backup

# テスト指示に置換
cp test_single_instruction.json instructions.json

# 実行
python3 simple_continuous_executor.py

# 結果確認
echo "=== 実行結果 ==="
cat simple_continuous_execution_report.md

# 元に戻す
cp instructions.json.backup instructions.json
rm test_single_instruction.json
```

### 3.2 VSCode拡張機能連携確認

#### コマンド送信確認
```bash
# 最新のコマンド確認
echo "=== 送信されたコマンド ==="
cat vscode-copilot-automation-extension/command.json

# 実行結果確認
echo "=== VSCode拡張機能の出力 ==="
cat .vscode/copilot-automation/execution_result.json 2>/dev/null || echo "結果ファイルなし"
```

### 3.3 ログ・データベース確認

#### 実行ログ確認
```bash
echo "=== 最新の実行ログ（最後の20行）==="
tail -20 simple_continuous_execution.log
```

#### データベース内容確認
```bash
echo "=== データベース内容確認 ==="
sqlite3 simple_continuous_execution.db "
SELECT 
    instruction_id,
    status,
    execution_time,
    timestamp
FROM execution_results 
ORDER BY timestamp DESC 
LIMIT 5;
"
```

---

## 🚀 Level 4: 連続実行確認

### 4.1 完全連続実行テスト

#### 実行前状態確認
```bash
echo "=== 実行前状態確認 ==="
echo "指示セット数: $(python3 -c "import json; data=json.load(open('instructions.json')); print(len(data['instructions']))")"
echo "データベース既存レコード数: $(sqlite3 simple_continuous_execution.db 'SELECT COUNT(*) FROM execution_results;' 2>/dev/null || echo '0')"
```

#### 連続実行実施
```bash
echo "=== 連続実行開始 ==="
echo "開始時刻: $(date)"

# 連続実行（バックグラウンド実行）
python3 simple_continuous_executor.py > execution_output.log 2>&1 &
EXEC_PID=$!

echo "実行PID: $EXEC_PID"
echo "実行監視中..."

# 実行監視（30秒間）
for i in {1..30}; do
    if ! kill -0 $EXEC_PID 2>/dev/null; then
        echo "実行完了（${i}秒後）"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "終了時刻: $(date)"
```

### 4.2 実行結果検証

#### 成功率確認
```bash
echo "=== 実行結果検証 ==="

# レポート確認
if [ -f simple_continuous_execution_report.md ]; then
    echo "✅ レポート生成成功"
    grep -E "(Total Instructions|Success Rate)" simple_continuous_execution_report.md
else
    echo "❌ レポート生成失敗"
fi

# データベース確認
TOTAL_RECORDS=$(sqlite3 simple_continuous_execution.db 'SELECT COUNT(*) FROM execution_results;' 2>/dev/null || echo '0')
SUCCESS_RECORDS=$(sqlite3 simple_continuous_execution.db 'SELECT COUNT(*) FROM execution_results WHERE status="success";' 2>/dev/null || echo '0')

echo "総実行数: $TOTAL_RECORDS"
echo "成功数: $SUCCESS_RECORDS"

if [ $TOTAL_RECORDS -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS_RECORDS * 100 / $TOTAL_RECORDS" | bc)
    echo "成功率: ${SUCCESS_RATE}%"
fi
```

### 4.3 パフォーマンス確認

#### 実行時間分析
```bash
echo "=== パフォーマンス分析 ==="

sqlite3 simple_continuous_execution.db "
SELECT 
    '平均実行時間' as metric,
    ROUND(AVG(execution_time), 2) || '秒' as value
FROM execution_results
UNION ALL
SELECT 
    '最大実行時間' as metric,
    ROUND(MAX(execution_time), 2) || '秒' as value
FROM execution_results
UNION ALL
SELECT 
    '最小実行時間' as metric,
    ROUND(MIN(execution_time), 2) || '秒' as value
FROM execution_results;
" 2>/dev/null || echo "データベースアクセスエラー"
```

---

## 🔍 トラブルシューティング

### 一般的な問題と解決策

#### 問題1: 実行が開始されない
**確認項目**:
```bash
# VSCode拡張機能インストール確認
code --list-extensions | grep copilot-automation-extension

# 指示セットファイル確認
test -f instructions.json && echo "OK" || echo "NG"

# Python実行権限確認
python3 -c "print('Python実行OK')"
```

#### 問題2: 実行は開始されるが結果が出力されない
**確認項目**:
```bash
# ログファイル確認
tail -50 simple_continuous_execution.log

# VSCode拡張機能出力確認
ls -la .vscode/copilot-automation/

# プロセス確認
ps aux | grep python3
```

#### 問題3: 成功率が低い
**確認項目**:
```bash
# エラー詳細確認
sqlite3 simple_continuous_execution.db "
SELECT instruction_id, error_message 
FROM execution_results 
WHERE status != 'success';
"

# Copilot認証状態確認（VSCodeで実施）
# VSCode > Command Palette > "GitHub Copilot: Sign In"
```

### ログレベル別対応

#### INFO レベル
- 正常な実行進捗
- 対応不要

#### WARNING レベル
- 軽微な問題
- 監視継続

#### ERROR レベル
- 実行エラー
- 即座に調査・修正

---

## 📊 動作確認チェックリスト

### 基本確認 ✅
- [ ] Python環境（3.9+）
- [ ] VSCode拡張機能インストール
- [ ] 必須ファイル存在
- [ ] 依存関係解決

### 機能確認 ✅
- [ ] 指示セット読み込み
- [ ] データベース接続
- [ ] VSCode拡張機能通信
- [ ] ログ出力

### 統合確認 ✅
- [ ] 単一指示実行
- [ ] 連続実行
- [ ] 結果出力
- [ ] レポート生成

### パフォーマンス確認 ✅
- [ ] 実行時間（10秒以下/指示）
- [ ] 成功率（95%以上）
- [ ] メモリ使用量
- [ ] CPU使用率

---

## 📞 サポート

### 問題報告時の必要情報
1. **実行環境**: OS, Python版, VSCode版
2. **エラーログ**: `simple_continuous_execution.log`の該当部分
3. **実行コマンド**: 実際に実行したコマンド
4. **再現手順**: 問題が発生するまでの手順

### 緊急時対応
1. **実行停止**: `Ctrl+C`またはプロセス終了
2. **ログ確認**: `tail -100 simple_continuous_execution.log`
3. **状態リセット**: データベース・ログファイル削除
4. **再実行**: クリーンな状態から再度実行

---

*このガイドは継続的に更新されます。問題や改善提案があれば、プロジェクトのIssuesに報告してください。*
