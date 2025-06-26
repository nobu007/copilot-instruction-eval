import asyncio
from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright):
    # このPoCでは、既存のブラウザインスタンスには接続せず、
    # Playwrightが新しいブラウザを起動します。
    # 認証は手動で行う必要があります。
    browser = await playwright.chromium.launch(headless=False, slow_mo=500)
    context = await browser.new_context()
    page = await context.new_page()

    # --- ユーザーに手動操作を要求するパート ---
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("ブラウザが起動しました。")
    print("1. vscode.dev/tunnel への接続と認証を完了してください。")
    print("2. 準備ができたら、このコンソールでEnterキーを押してください...")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    await asyncio.get_event_loop().run_in_executor(None, input)

    try:
        print("\n>>> Copilotチャットパネルを開きます (Ctrl+Alt+I)")
        await page.keyboard.press('Control+Alt+I')

        # チャット入力欄のセレクタ（仮）。実際のセレクタは調査して修正する必要がある。
        chat_input_selector = 'textarea[aria-label="Chat input"]'
        print(f">>> チャット入力欄を待ちます: {chat_input_selector}")
        await page.wait_for_selector(chat_input_selector, timeout=30000)
        print(">>> 入力欄が見つかりました。")

        prompt = "Hello, Copilot! How are you today?"
        print(f">>> プロンプトを送信します: '{prompt}'")
        await page.fill(chat_input_selector, prompt)
        await page.keyboard.press('Enter')

        # 応答が表示されるのを待つ（仮のセレクタとロジック）
        # 実際の応答コンテナのセレクタを特定する必要がある
        response_selector = 'div[class*="response"] .markdown-body'
        print(f">>> 応答を待ちます: {response_selector}")
        await page.wait_for_selector(response_selector, timeout=60000)
        print(">>> 応答が見つかりました。")

        # 最後の応答要素からテキストを取得
        response_elements = await page.query_selector_all(response_selector)
        last_response_element = response_elements[-1] if response_elements else None

        if last_response_element:
            response_text = await last_response_element.inner_text()
            print("\n--- Copilotからの応答 ---")
            print(response_text)
            print("--------------------------")
        else:
            print("XXX 応答が見つかりませんでした。")

    except Exception as e:
        print(f"\nXXX エラーが発生しました: {e}")

    finally:
        print("\nPoCスクリプトが終了しました。ブラウザを手動で閉じてください。")
        # await browser.close() # デバッグのため、ブラウザは開いたままにする

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

if __name__ == "__main__":
    asyncio.run(main())
