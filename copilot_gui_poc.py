import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import time
import os


async def run_copilot_poc(playwright: Playwright):
    # VS Code の実行パス (WSL2 Ubuntu 環境での例)
    # Windows のパスであれば 'C:/Users/YourUser/AppData/Local/Programs/Microsoft VS Code/Code.exe' のように指定
    # WSLg を利用する場合、Linux 側の VS Code を指定するのが一般的です。
    # ここでは、Linux 用 VS Code が /usr/bin/code にインストールされていると仮定します。
    vs_code_executable_path = "/usr/bin/code"

    # テストシナリオで使用するコードと指示
    python_code_to_review = """
def calculate_area(width, height):
    # This function calculates the area of a rectangle
    return width * height

def get_user_input():
    # Get user input for width and height
    w = input("Enter width: ")
    h = input("Enter height: ")
    return w, h

if __name__ == "__main__":
    w, h = get_user_input()
    area = calculate_area(int(w), int(h))
    print("Area:", area)
"""

    copilot_instruction = "上記のPythonコードをPEP8に準拠するようにレビューし、型ヒントを追加してください。また、より良いコメントを追加してください。"

    # Chromium を起動し、そのコンテキストで VS Code を実行
    # `executable_path` に VS Code の実行ファイルを指定することで、Playwright がブラウザとして VS Code を扱えるようになります。
    # headless=False で GUI を表示します。
    # devtools=True はデバッグ用ですが、今回はオフにしています。
    browser = await playwright.chromium.launch(
        executable_path=vs_code_executable_path,
        headless=False,
        args=["--new-window"],  # 新しいウィンドウで開くオプション
    )

    page = await browser.new_page()

    try:
        print("VS Code を起動中...")
        # VS Code の起動を待つ。具体的な表示要素を待つ方が確実だが、今回は暫定的に固定秒数待機。
        await page.wait_for_timeout(5000)  # 5秒待機

        # --- 新しいファイルを作成 ---
        print("新しいファイルを作成中...")
        # Command Palette を開く (Ctrl+Shift+P または Cmd+Shift+P)
        await page.keyboard.press("Control+Shift+P")
        await page.wait_for_timeout(500)

        # 'new file' と入力し、Enter を押す
        await page.keyboard.type("new file")
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)  # 新しいファイルが開くのを待つ

        # --- コードを貼り付け ---
        print("Python コードをエディタに貼り付け中...")
        await page.keyboard.type(python_code_to_review)
        await page.wait_for_timeout(1000)  # 貼り付けを待つ

        # --- Copilot にコードレビューを依頼 (Chat 機能を利用) ---
        print("GitHub Copilot Chat を開く...")
        # Copilot Chat を開くコマンド (通常は Ctrl+Alt+I または Cmd+Alt+I)
        # 環境や設定によっては異なる可能性があります。
        # または、左サイドバーのアイコンをクリックすることも可能ですが、キーボードショートカットの方が安定しやすいです。
        await page.keyboard.press("Control+Alt+I")
        await page.wait_for_timeout(2000)  # Copilot Chat が開くのを待つ

        # Chat 入力フィールドに指示を入力
        # CSS セレクタは VS Code のバージョンやテーマによって異なる可能性があります。
        # 実際には VS Code の開発者ツール (Help -> Toggle Developer Tools) で確認するのが確実です。
        # ここでは一般的なセレクタを仮定します。
        # Playwright の Locator を使って要素を探します。
        # Chat 入力ボックスの一般的なセレクタの例
        # `.chat-input-textarea` や `textarea[aria-label="Chat input"]` など
        chat_input_selector = 'textarea[aria-label="Chat input"]'  # より頑健なセレクタ
        # もしくは、もっと汎用的なセレクタで、入力できる場所を探す
        # chat_input_selector = 'textarea.input-box' # これも試す価値あり

        # chat_input_locator = page.locator(chat_input_selector).last # 複数ある場合、最後のものを取得

        # 要素が見つかるまで待機
        await expect(page.locator(chat_input_selector)).to_be_visible()
        chat_input_locator = page.locator(chat_input_selector)

        print("Copilot への指示を入力中...")
        await chat_input_locator.fill(copilot_instruction)
        await page.wait_for_timeout(500)

        # Enter キーを押して指示を送信
        await chat_input_locator.press("Enter")
        print("指示を送信しました。Copilot の応答を待機中...")

        # --- Copilot の応答を待機し、取得 ---
        # Copilot の応答が表示される領域を特定し、そのテキスト内容を取得します。
        # 応答の完了を待つのは非常に難しいですが、ここでは暫定的に十分な時間を待機します。
        # 実際には、応答がストリーミングされる場合は、その完了を検知するロジックが必要です。
        # 例えば、特定の「Generating...」のような表示が消えるのを待つ、最終的な出力要素が安定するのを待つなど。
        await page.wait_for_timeout(20000)  # 20秒待機 (応答時間による)

        # Copilot の応答が表示される要素のセレクタ (これも環境依存)
        # `.chat-response-content` や `[data-testid="copilot-chat-response"]` など
        response_selector = ".chat-response-content"  # 仮のセレクタ

        # 応答要素が存在し、表示されていることを確認
        if await page.locator(response_selector).first.is_visible():
            copilot_response = await page.locator(
                response_selector
            ).first.text_content()
            print("\n--- GitHub Copilot Agent の応答 ---")
            print(copilot_response)
            print("---------------------------------\n")
        else:
            print("Copilot の応答が見つからないか、まだ表示されていません。")

        # スクリーンショットを保存 (デバッグ用)
        timestamp = int(time.time())
        screenshot_path = f"copilot_response_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"スクリーンショットを保存しました: {screenshot_path}")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        # クリーンアップ: VS Code を閉じる
        print("VS Code を閉じます。")
        await browser.close()


async def main():
    async with async_playwright() as playwright:
        await run_copilot_poc(playwright)


if __name__ == "__main__":
    asyncio.run(main())
