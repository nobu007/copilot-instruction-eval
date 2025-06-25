# 既存ブラウザ接続モードでの評価手順 (`gui_evaluation_script.py`)

2段階認証に対応するため、スクリプトは新しくブラウザを起動するのではなく、**あなたが事前に起動し、手動でログインしたブラウザに接続して**評価を実行します。

このモードで評価を実行するには、以下の2つのステップが必要です。

## ステップ1: デバッグモードでChromeを起動する

まず、スクリプトが接続するための「デバッグポート」を開いた状態でChromeを起動する必要があります。

1.  **既存のChromeウィンドウをすべて閉じてください。**

2.  **コマンドプロンプトまたはPowerShellを開きます。**

3.  以下のコマンドを実行します。これにより、通常のプロファイルとは別の、テスト専用のプロファイルでChromeが起動します。

    ```shell
    "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDevProfile"
    ```
    *   **注意:** `C:\Program Files\Google\Chrome\Application\chrome.exe` の部分は、あなたのPCのChromeのインストール場所に合わせて変更してください。
    *   `--user-data-dir` に指定したフォルダ (`C:\ChromeDevProfile`) は、このテスト専用のユーザーデータが保存される場所です。初回実行時に自動で作成されます。

4.  新しいChromeウィンドウが起動します。このウィンドウで、**手動でGitHubにアクセスし、評価したいアカウント（v1またはv2）でログインしてください。** 2段階認証のコード入力もこの段階で済ませます。

5.  **このChromeウィンドウは開いたままにしてください。** これがスクリプトの操作対象となります。

## ステップ2: 評価スクリプトを実行する

ステップ1で起動したChromeに接続するため、スクリプトにいくつかの引数を渡して実行します。

1.  **新しいコマンドプロンプトまたはPowerShellを開きます。**（ステップ1のウィンドウはそのままにしておきます）

2.  `copilot-instruction-eval` ディレクトリに移動します。
    ```shell
    cd c:\work\copilot-instruction-eval
    ```

3.  以下のコマンドを実行して、評価を開始します。

    **v1エージェントを評価する場合:**
    ```shell
    python gui_evaluation_script.py --port=9222 --agent-version=v1
    ```

    **v2エージェントを評価する場合:**
    *   まず、ステップ1で起動したChromeで一度ログアウトし、v2のアカウントで再度ログインします。
    *   その後、以下のコマンドを実行します。
    ```shell
    python gui_evaluation_script.py --port=9222 --agent-version=v2
    ```

### コマンド引数の説明

-   `--port=9222`: ステップ1で指定したデバッグポート番号に合わせます。
-   `--agent-version=v1`: どのエージェントの評価であるかをログに残すための指定です。`v1`または`v2`を指定します。

これで、2段階認証の問題を回避し、安定して評価を実行できるはずです。
