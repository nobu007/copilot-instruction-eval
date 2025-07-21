# 設計書: GitHub Copilot連続自動実行システム真正性検証プロジェクト

## 1. 最終目的

**主目的:** GitHub Copilot連続自動実行システムの偽陽性問題を根本解決し、真の E2E 通信による確実な動作検証システムを構築する

**具体的達成目標:**

- VSCode Desktop の実起動確認機能
- VSCode拡張機能との実通信検証
- 実際のCopilot応答取得・検証
- 偽陽性を完全排除した厳密な成功/失敗判定
- 事実ベースの動作確認システム


## 2. 現状問題分析

### 2.1 判明した重大な問題

- **偽陽性判定:** `simple_continuous_executor.py` が常に成功を返す設計欠陥
- **VSCode未起動:** システムが100%成功報告するが実際にはVSCode Desktopが起動していない
- **通信未発生:** VSCode拡張機能との実通信が発生していない
- **モック応答:** 古い `.vscode/copilot-automation/execution_result.json` を流用


### 2.2 根本原因

```python
# simple_continuous_executor.py Line 207-223: 致命的欠陥
time.sleep(5)  # 単純待機のみ
response = "Command sent to VSCode extension successfully"  # ハードコード
return True, response, execution_time  # 常にTrue返却
```


## 3. システムアーキテクチャ

### 3.1 新設計アーキテクチャ

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    真正性検証システム                        │
├─────────────────────────────────────────────────────────────┤
│ 1. VSCode Desktop プロセス起動確認                           │
│ 2. VSCode拡張機能 実通信検証                                 │
│ 3. Copilot API 実応答取得                                   │
│ 4. E2E 通信フロー完全検証                                   │
│ 5. 事実ベース成功/失敗判定                                   │
└─────────────────────────────────────────────────────────────┘
```


### 3.2 コンポーネント設計

- **ProcessManager**: VSCode Desktop起動・監視
- **ExtensionCommunicator**: 拡張機能との実通信
- **CopilotVerifier**: 実際のCopilot応答検証
- **E2EValidator**: エンドツーエンド通信検証
- **FactBasedJudge**: 事実ベース判定エンジン


## 4. ファイル構造

```plaintext
/home/jinno/copilot-instruction-eval/workspace/
├── src/
│   ├── true_e2e_executor.py          # 真のE2E実行エンジン
│   ├── vscode_process_manager.py     # VSCode起動・監視
│   ├── extension_communicator.py     # 拡張機能通信
│   ├── copilot_verifier.py          # Copilot応答検証
│   ├── fact_based_judge.py          # 事実ベース判定
│   └── utils/
│       ├── process_utils.py          # プロセス管理ユーティリティ
│       └── communication_utils.py    # 通信ユーティリティ
├── tests/
│   ├── test_vscode_manager.py        # VSCode管理テスト
│   ├── test_extension_comm.py        # 拡張機能通信テスト
│   ├── test_copilot_verify.py       # Copilot検証テスト
│   └── test_e2e_integration.py      # E2E統合テスト
├── config/
│   ├── vscode_config.json           # VSCode設定
│   └── extension_config.json        # 拡張機能設定
└── reports/
    └── (インシデントレポートが自動生成される)
```


## 5. データスキーマ

### 5.1 VSCode起動確認レスポンス

```json
{
  "vscode_status": {
    "is_running": true,
    "process_id": 12345,
    "executable_path": "/usr/bin/code",
    "workspace_path": "/home/jinno/copilot-instruction-eval",
    "extensions_loaded": true,
    "copilot_extension_active": true
  }
}
```


### 5.2 拡張機能通信レスポンス

```json
{
  "communication_status": {
    "connection_established": true,
    "handshake_successful": true,
    "extension_version": "0.0.1",
    "last_heartbeat": "2025-07-21T10:51:17+09:00"
  }
}
```


### 5.3 Copilot実応答スキーマ

```json
{
  "copilot_response": {
    "success": true,
    "instruction_id": "code_review_1",
    "actual_response": "実際のCopilot応答テキスト",
    "model": "copilot/gpt-4",
    "execution_time": 3.24,
    "timestamp": "2025-07-21T10:51:17+09:00",
    "verification_hash": "sha256:abc123..."
  }
}
```


## 6. 実行計画 (ステップバイステップ)

### Phase 2: 実装

- [x] **Step 1:** VSCodeプロセス管理モジュール実装 (`vscode_process_manager.py`)
- [x] **Step 2:** 拡張機能通信モジュール実装 (`extension_communicator.py`)
- [x] **Step 3:** Copilot検証モジュール実装 (`copilot_verifier.py`)

- [x] **Step 4:** 事実ベース判定エンジン実装 (`fact_based_judge.py`)

- [x] **Step 5:** 真のE2E実行エンジン統合 (`true_e2e_executor.py`)
- [ ] **Step 5.1:** 拡張機能のファイル監視・リクエスト検知処理のデバッグ


### Phase 3: テスト実行

- [ ] **Step 6:** 単体テスト実装・実行

- [ ] **Step 7:** 統合テスト実装・実行

- [ ] **Step 8:** E2Eテスト実装・実行

- [ ] **Step 9:** 実システム検証テスト


### Phase 4: 検証・修正

- [ ] **Step 10:** 偽陽性問題の完全解決確認

- [ ] **Step 11:** 実通信による動作確認

- [ ] **Step 12:** パフォーマンス・安定性検証


## 7. リスク分析

### 7.1 技術的リスク

**リスク:** VSCode Desktop起動に失敗する可能性
- **対策:** 複数起動方法の実装、詳細エラーログ、自動リトライ機能

**リスク:** 拡張機能との通信が不安定
- **対策:** ハートビート機能、接続状態監視、自動再接続

**リスク:** Copilot APIの応答遅延・失敗
- **対策:** タイムアウト設定、リトライロジック、フォールバック機能


### 7.2 運用リスク

**リスク:** 既存システムとの互換性問題
- **対策:** 段階的移行、並行運用期間の設定

**リスク:** 検証時間の大幅増加
- **対策:** 並列処理、キャッシュ機能、最適化


## 8. 成功基準

### 8.1 機能要件

- ✅ VSCode Desktop実起動確認 (100%精度)
- ✅ 拡張機能実通信確認 (100%精度)
- ✅ 実Copilot応答取得 (100%精度)
- ✅ 偽陽性完全排除 (0%偽陽性率)


### 8.2 非機能要件

- ⏱️ 1指示あたり実行時間: 10秒以内
- 🔄 システム可用性: 99%以上
- 📊 ログ・監査証跡: 100%記録


## 9. 検証方法

### 9.1 事実ベース検証項目

1. **プロセス確認:** `ps aux | grep code` でVSCode Desktop確認
2. **通信確認:** 実際のJSON交換ログ確認
3. **応答確認:** Copilot実応答の内容・タイムスタンプ確認
4. **ファイル確認:** 最新の結果ファイル生成確認


### 9.2 偽陽性排除確認（エッジケース・ストレステスト）

- **シナリオ1: VSCode未起動**
  - **手順:** VSCodeプロセスを完全に終了させた状態でE2Eテストを実行。
  - **期待結果:** システムは即座に「VSCodeプロセスが起動していません」と報告し、`FAILURE`ステータスで終了する。

- **シナリオ2: 拡張機能の無効化/未インストール**
  - **手順:** VSCodeは起動しているが、対象のCopilot自動化拡張機能を無効化またはアンインストールした状態でE2Eテストを実行。
  - **期待結果:** システムは「拡張機能との通信ハンドシェイクに失敗しました」と報告し、`FAILURE`ステータスで終了する。

- **シナリオ3: ネットワーク切断**
  - **手順:** マシンのネットワーク接続を無効化した状態でE2Eテストを実行。
  - **期待結果:** 拡張機能は「Copilotモデルへのアクセスに失敗しました」という趣旨のエラーを記録し、システムはCopilotからの応答がタイムアウトまたは失敗したことを検知して`FAILURE`ステータスで終了する。

- **シナリオ4: 通信ディレクトリの異常**
  - **手順:** 通信に使用する`/tmp/copilot-evaluation`ディレクトリを削除、または読み取り専用権限に変更してE2Eテストを実行。
  - **期待結果:** システムまたは拡張機能がファイルI/Oエラーを検知し、`FAILURE`ステータスで終了する。

- **シナリオ5: 不正なリクエストJSON**
  - **手順:** `request.json`を空にする、または必須キーを欠いた状態でE2Eテストを実行。
  - **期待結果:** 拡張機能がリクエストのパースに失敗したことをログに出力し、システムは応答がないため`FAILURE`ステータスで終了する。

- **シナリオ6: Copilot応答タイムアウト**
  - **手順:** 拡張機能側のCopilot API呼び出しに意図的に長い遅延を注入し、E2Eテストのタイムアウト値を短く設定して実行。
  - **期待結果:** システムは「Copilotからの応答がタイムアウトしました」と報告し、`FAILURE`ステータスで終了する。

- **シナリオ7: リクエストの連続投入**
  - **手順:** 1つ目のリクエスト処理が完了する前に、2つ目の`request.json`を投入する。
  - **期待結果:** 拡張機能は進行中の処理が完了するまで新しいリクエストをキューイングするか、あるいは明確に拒否する。システム全体がクラッシュしたり、未定義の動作に陥らないことを確認する。
