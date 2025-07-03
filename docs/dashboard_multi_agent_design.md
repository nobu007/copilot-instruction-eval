# ダッシュボードの複数エージェント対応デザイン

## 背景
現在のパフォーマンス分析ダッシュボードは、Agentごとの成功率と平均応答時間を単一グラフとして表示します。
データベースに新しいAgentバージョンが追加された場合でも、手動でコードを修正せずに自動的にグラフに反映させる必要があります。

## 目的
- データベースに登録されたすべてのAgentバージョンを自動取得し、グラフ描画時に動的に線を生成する
- Agentが増減してもコード修正やテンプレート修正を不要とし、拡張性を担保する

## アーキテクチャ
- **バックエンド (Flask)**
  - `index` ルート: SQLiteから`agent_version`を`SELECT DISTINCT ... ORDER BY`で取得し、テンプレートへ渡す
  - `/api/data` ルート: 評価結果を全件取得し、JSON配列で返却
- **フロントエンド (HTML + JavaScript + Chart.js)**
  - テンプレートで`agent_versions`を`tojson`フィルタを使ってJavaScript変数に埋め込む
  - JS側で`agentVersions`配列をループし、各Agent用のデータ配列 (`successRates`, `responseTimes`) を初期化
  - Chart.jsの`datasets`にAgentごとのオブジェクトを生成し、動的に渡す
  - カラーコードはAgentバージョン文字列のハッシュから算出し、一意の色を生成

## 詳細設計
1. **バックエンド変更** (`dashboard.py`)
   - `index()`でのSQLを修正: `SELECT DISTINCT agent_version FROM results ORDER BY agent_version`
2. **フロントエンド変更** (`templates/index.html`)
   - 既存ロジックで動的に対応済み。必要に応じて、以下を検討:
     - 新規Metricの追加を想定してCanvas要素を動的に生成
     - User InterfaceでAgentごとの表示・非表示を切り替えるチェックボックス

## テスト計画
- DBに複数（例：`v1`, `v2`, `v3`）のAgentバージョンを登録し、起動後ダッシュボード上に全ラインが正しく描画されること
- Agentバージョンの順序がSQLの`ORDER BY`により安定すること

## 拡張案
- AgentフィルタリングUIの実装（チェックボックス or ドロップダウン）
- グラフ上のホバー時、Agentバージョンが明示されるTooltip
- 時系列の粒度（時間単位）の動的変更機能
