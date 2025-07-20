import * as vscode from 'vscode';

/**
 * Copilot Automation Debug WebView Provider
 * VSCode左ペインにデバッグ用のインターフェースを提供
 */
export class CopilotDebugProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'copilotAutomation.debugView';
    
    private _view?: vscode.WebviewView;
    private _logs: string[] = [];

    constructor(
        private readonly _extensionUri: vscode.Uri,
    ) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            // Allow scripts in the webview
            enableScripts: true,
            localResourceRoots: [
                this._extensionUri
            ]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(
            message => {
                switch (message.type) {
                    case 'sendPrompt':
                        this.sendPromptToCopilot(message.prompt);
                        break;
                    case 'clearLogs':
                        this.clearLogs();
                        break;
                }
            },
            undefined,
        );
    }

    public addLog(message: string) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}`;
        this._logs.push(logEntry);
        
        // Keep only last 100 logs
        if (this._logs.length > 100) {
            this._logs = this._logs.slice(-100);
        }

        this._updateWebview();
    }

    public clearLogs() {
        this._logs = [];
        this._updateWebview();
    }

    private async sendPromptToCopilot(prompt: string) {
        try {
            this.addLog(`🚀 Sending Agent Mode prompt: "${prompt}"`);

            // 1. Agent Mode設定の確認・有効化
            const agentConfig = vscode.workspace.getConfiguration('chat.agent');
            const isAgentEnabled = agentConfig.get('enabled', false);
            
            if (!isAgentEnabled) {
                this.addLog('⚠️ Agent mode not enabled. Attempting to enable...');
                await agentConfig.update('enabled', true, vscode.ConfigurationTarget.Global);
                this.addLog('✅ Agent mode enabled. Restart VSCode for full effect.');
            } else {
                this.addLog('✅ Agent mode is already enabled');
            }

            // 2. Agent ModeでCopilot Chatを起動
            this.addLog('🚀 Launching Copilot Agent Mode...');
            
            try {
                // Agent ModeでChatを開く
                await vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
                
                // 少し待ってからAgent Modeに切り替え
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                // Agent Modeに切り替えるコマンドを実行
                await vscode.commands.executeCommand('workbench.action.chat.setMode', 'agent');
                
                this.addLog('✅ Successfully switched to Agent Mode UI');
                
                // Agent Modeでプロンプトを送信するコマンドを試行
                await new Promise(resolve => setTimeout(resolve, 500));
                await vscode.commands.executeCommand('workbench.action.chat.submit', prompt);
                
                this.addLog('✅ Prompt submitted to Agent Mode interface');
                
            } catch (chatError) {
                this.addLog(`⚠️ Agent Mode UI launch failed: ${chatError}`);
            }

            // 3. 利用可能なCopilotモデルを検索（フォールバック）
            const allModels = await vscode.lm.selectChatModels();
            this.addLog(`📊 Found ${allModels.length} total language models`);

            // Copilotモデルを特定
            const copilotModels = allModels.filter(model =>
                model.vendor === "copilot" ||
                model.vendor === "github" ||
                model.family.toLowerCase().includes("copilot")
            );

            if (copilotModels.length === 0) {
                throw new Error('No Copilot models found. Make sure GitHub Copilot is installed and authenticated.');
            }

            const selectedModel = copilotModels[0];
            this.addLog(`🤖 Using model: ${selectedModel.vendor}/${selectedModel.family}`);

            // 4. Agent ModeスタイルのプロンプトでLanguage Model API通信
            const agentStyleMessages = [
                vscode.LanguageModelChatMessage.User(`[AGENT MODE] ${prompt}

Operating in autonomous agent mode. Please provide:
1. Workspace context analysis
2. Specific file modification suggestions
3. Tool invocation recommendations
4. Terminal commands for execution
5. Next steps for automation

Respond as if you have agent-level capabilities for autonomous code editing.`)
            ];

            this.addLog('💬 Sending Agent Mode request to Language Model...');
            const chatRequest = await selectedModel.sendRequest(agentStyleMessages, {}, new vscode.CancellationTokenSource().token);
            
            let response = '';
            for await (const fragment of chatRequest.text) {
                response += fragment;
            }

            this.addLog(`✅ Agent Mode response received (${response.length} chars): ${response.substring(0, 100)}...`);

            // レスポンスをエディタに挿入
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const position = editor.selection.active;
                await editor.edit(editBuilder => {
                    editBuilder.insert(position, `\n// === Copilot Debug Response ===\n// Prompt: ${prompt}\n// Response: ${response}\n// =============================\n`);
                });
                this.addLog('📝 Response inserted into active editor');
            } else {
                // アクティブエディタがない場合は新しいドキュメントを作成
                const doc = await vscode.workspace.openTextDocument({
                    content: `// === Copilot Automation Result ===\n// Timestamp: ${new Date().toISOString()}\n// Prompt: ${prompt}\n\n// Response:\n${response}\n\n// ====================================`,
                    language: 'markdown'
                });
                await vscode.window.showTextDocument(doc);
                this.addLog('📝 Response displayed in new document (no active editor was found)');
            }

            vscode.window.showInformationMessage(`✅ Copilot automation successful!`);

        } catch (error) {
            const errorMessage = `❌ Error: ${error}`;
            this.addLog(errorMessage);
            vscode.window.showErrorMessage(errorMessage);
        }
    }

    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'updateLogs',
                logs: this._logs
            });
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Copilot Debug</title>
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    font-size: var(--vscode-font-size);
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                    margin: 0;
                    padding: 10px;
                }
                
                .container {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                }
                
                .input-section {
                    margin-bottom: 10px;
                }
                
                .input-group {
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }
                
                label {
                    font-weight: bold;
                    color: var(--vscode-input-foreground);
                }
                
                textarea {
                    background-color: var(--vscode-input-background);
                    color: var(--vscode-input-foreground);
                    border: 1px solid var(--vscode-input-border);
                    border-radius: 2px;
                    padding: 8px;
                    font-family: inherit;
                    resize: vertical;
                    min-height: 60px;
                }
                
                .button-group {
                    display: flex;
                    gap: 5px;
                    margin-top: 10px;
                }
                
                button {
                    background-color: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    border-radius: 2px;
                    padding: 8px 12px;
                    cursor: pointer;
                    font-family: inherit;
                }
                
                button:hover {
                    background-color: var(--vscode-button-hoverBackground);
                }
                
                .secondary-button {
                    background-color: var(--vscode-button-secondaryBackground);
                    color: var(--vscode-button-secondaryForeground);
                }
                
                .secondary-button:hover {
                    background-color: var(--vscode-button-secondaryHoverBackground);
                }
                
                .logs-section {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    margin-top: 10px;
                    border-top: 1px solid var(--vscode-panel-border);
                    padding-top: 10px;
                }
                
                .logs-header {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                
                .logs-container {
                    flex: 1;
                    background-color: var(--vscode-terminal-background);
                    border: 1px solid var(--vscode-panel-border);
                    border-radius: 2px;
                    padding: 8px;
                    overflow-y: auto;
                    font-family: var(--vscode-editor-font-family);
                    font-size: 12px;
                    line-height: 1.4;
                }
                
                .log-entry {
                    margin-bottom: 2px;
                    word-wrap: break-word;
                }
                
                .log-entry:last-child {
                    margin-bottom: 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="input-section">
                    <div class="input-group">
                        <label for="promptInput">Copilot Prompt:</label>
                        <textarea id="promptInput" placeholder="Enter your prompt for Copilot...">Hello! Please explain what VSCode extensions are.</textarea>
                    </div>
                    <div class="button-group">
                        <button id="sendButton">Send to Copilot</button>
                        <button id="clearButton" class="secondary-button">Clear Logs</button>
                    </div>
                </div>
                
                <div class="logs-section">
                    <div class="logs-header">Debug Logs:</div>
                    <div id="logsContainer" class="logs-container">
                        <div class="log-entry">[Ready] Copilot Debug Panel initialized</div>
                    </div>
                </div>
            </div>

            <script>
                const vscode = acquireVsCodeApi();
                
                document.getElementById('sendButton').addEventListener('click', () => {
                    const prompt = document.getElementById('promptInput').value;
                    if (prompt.trim()) {
                        vscode.postMessage({
                            type: 'sendPrompt',
                            prompt: prompt
                        });
                    }
                });
                
                document.getElementById('clearButton').addEventListener('click', () => {
                    vscode.postMessage({
                        type: 'clearLogs'
                    });
                });
                
                // Handle messages from the extension
                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.type) {
                        case 'updateLogs':
                            const logsContainer = document.getElementById('logsContainer');
                            logsContainer.innerHTML = message.logs.map(log => 
                                \`<div class="log-entry">\${log}</div>\`
                            ).join('');
                            logsContainer.scrollTop = logsContainer.scrollHeight;
                            break;
                    }
                });
            </script>
        </body>
        </html>`;
    }
}
