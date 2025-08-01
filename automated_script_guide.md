# 自動評価スクリプト (`gui_evaluation_script.py`) 動作手順書

## 1. 目的

このドキュメントは、`gui_evaluation_script.py`が、`manual_test_procedure.md`で定義された手動操作をどのように自動化しているかを解説します。

## 2. スクリプトの全体的な流れ

スクリプトは、**エージェントのバージョンごと（v1, v2）**に以下の処理を繰り返します。

```mermaid
graph TD
    A[スクリプト開始] --> B{エージェントループ (v1, v2)};
    B --> C[1. ブラウザ起動];
    C --> D[2. GitHubログイン];
    D --> E{プロンプトループ (prompts.csv)};
    E --> F[3. Copilotページ移動];
    F --> G[4. プロンプト入力・送信];
    G --> H[5. 応答完了を待機];
    H --> I[6. 応答内容と時間を記録];
    I --> E;
    E -- 全プロンプト完了 --> J[7. ブラウザ終了];
    J --> B;
    B -- 全エージェント完了 --> K[スクリプト終了];
```

## 3. 各ステップの詳細

1.  **ブラウザ起動**
    - `Selenium`と`webdriver-manager`を使い、新しいChromeブラウザのウィンドウを起動します。

2.  **GitHubログイン**
    - `.env`ファイルから現在のエージェントバージョン（v1またはv2）に対応する`GITHUB_USERNAME`と`PASSWORD`を読み取ります。
    - `https://github.com/login`にアクセスし、IDとパスワードの入力欄に認証情報を自動入力してログインボタンをクリックします。

3.  **Copilotページ移動**
    - ログイン後、`https://github.com/features/copilot`に直接アクセスします。

4.  **プロンプト入力・送信**
    - `prompts.csv`から一行ずつプロンプトを読み込み、チャット入力欄にテキストを自動入力し、送信ボタンをクリックします。

5.  **応答完了を待機**
    - Copilotが思考中であることを示すUI要素（例: プログレスバー）を監視します。
    - この要素が画面から消えるまで待機することで、応答が完了したと判断します。

6.  **応答内容と時間を記録**
    - 応答が表示されているHTML要素からテキストをすべて抽出します。
    - プロンプト送信から応答完了までの時間を計測します。
    - 以下の情報をJSON形式で`gui_evaluation_logs.jsonl`ファイルに追記します。
      - `prompt_id`, `prompt_text`, `agent_version`, `response_text`, `response_time_ms`, `timestamp`, `error`

7.  **ブラウザ終了**
    - 現在のエージェントのすべてのプロンプト評価が完了したら、ブラウザウィンドウを閉じ、セッションをクリーンアップします。

このサイクルをv1とv2のエージェントで繰り返すことで、全自動での評価を実現します。
