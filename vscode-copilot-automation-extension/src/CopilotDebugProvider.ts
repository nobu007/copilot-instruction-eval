import * as vscode from 'vscode';
import { CopilotService } from './services/CopilotService';
import { ModelManager } from './services/ModelManager';
import { ModeManager } from './services/ModeManager';
import { UIManager } from './ui/UIManager';

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

/**
 * Copilot Automation Debug WebView Provider
 * Provides a debug interface in the VSCode side panel.
 * Enhanced with model selection and mode switching capabilities.
 */
export class CopilotDebugProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'copilotAutomation.debugView';
    
    private _view?: vscode.WebviewView;
    private _logs: string[] = [];
    
    // Enhanced services
    private copilotService?: CopilotService;
    private modelManager?: ModelManager;
    private modeManager?: ModeManager;
    private uiManager?: UIManager;

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
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        // Use enhanced UI if UIManager is available, otherwise use legacy UI
        if (this.uiManager) {
            this.uiManager.setWebviewView(webviewView);
            webviewView.webview.html = this.uiManager.getHtmlForWebview(webviewView.webview);
            
            webviewView.webview.onDidReceiveMessage(async (message) => {
                if (this.uiManager) {
                    await this.uiManager.handleMessage(message);
                }
            });
            
            console.log('✅ Enhanced UI with UIManager initialized');
            return;
        }
        
        // Fallback to legacy UI
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(message => {
            switch (message.type) {
                case 'sendPrompt':
                    this.sendPromptToCopilot(message.prompt);
                    break;
                case 'clearLogs':
                    this.clearLogs();
                    break;
                case 'shutdown':
                    vscode.commands.executeCommand('workbench.action.closeWindow');
                    break;
                case 'getPid':
                    if (this._view) {
                        this._view.webview.postMessage({ type: 'setPid', pid: process.pid });
                    }
                    break;
            }
        });
    }

    public addLog(message: string) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}`;
        this._logs.push(logEntry);
        
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

            this.addLog('🚀 Launching Copilot Agent Mode...');
            
            try {
                await vscode.commands.executeCommand('workbench.action.chat.open', { query: '@agent /new' });
                this.addLog('✅ Copilot Agent Mode session started.');
            } catch (e: any) {
                this.addLog(`❌ Failed to open Copilot Chat in Agent Mode: ${e.message}`);
                this.addLog('ℹ️ Attempting to fall back to Language Model API.');
                
                if (this.copilotService) {
                    await this.copilotService.sendPromptToUI(prompt);
                } else {
                    this.addLog('❌ CopilotService not available for fallback.');
                }
                return;
            }

            await new Promise(resolve => setTimeout(resolve, 2000));

            const llm = await vscode.lm.selectChatModels({ vendor: 'copilot', family: 'gpt-4' });
            if (!llm || llm.length === 0) {
                this.addLog('❌ No suitable Copilot language model found.');
                return;
            }
            const model = llm[0];
            this.addLog(`✅ Using language model: ${model.name} | ${model.vendor}`);

            const messages: vscode.LanguageModelChatMessage[] = [
                new vscode.LanguageModelChatMessage(vscode.LanguageModelChatMessageRole.User, 
                    `You are an autonomous AI agent. Your task is to fulfill the user's request. This is the request: "${prompt}"`
                )
            ];

            this.addLog('💬 Sending request to language model...');
            const chatResponse = await model.sendRequest(messages, {}, new vscode.CancellationTokenSource().token);
            
            let fullResponse = '';
            for await (const chunk of chatResponse.stream) {
                fullResponse += chunk;
            }
            this.addLog(`✅ Received response from language model.`);

            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor) {
                activeEditor.edit(editBuilder => {
                    editBuilder.insert(activeEditor.selection.active, fullResponse);
                });
                this.addLog('✅ Response inserted into active editor.');
            } else {
                const newDocument = await vscode.workspace.openTextDocument({ content: fullResponse, language: 'markdown' });
                await vscode.window.showTextDocument(newDocument);
                this.addLog('✅ Response inserted into a new document.');
            }

        } catch (error: any) {
            const errorMessage = error.message || 'An unknown error occurred';
            this.addLog(`❌ Error sending prompt to Copilot: ${errorMessage}`);
            vscode.window.showErrorMessage(`Failed to send prompt to Copilot: ${errorMessage}`);
        }
    }

    private _updateWebview() {
        if (this._view) {
            this._view.webview.postMessage({ type: 'updateLogs', logs: this._logs });
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const nonce = getNonce();
        const script = `
            (function() {
                const vscode = acquireVsCodeApi();

                function escapeHtml(text) {
                    if (typeof text !== 'string') {
                        return text;
                    }
                    return text
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#039;');
                }

                document.getElementById('sendButton').addEventListener('click', () => {
                    const promptInput = document.getElementById('promptInput');
                    if (promptInput) {
                        vscode.postMessage({ type: 'sendPrompt', prompt: promptInput.value });
                    }
                });

                document.getElementById('clearButton').addEventListener('click', () => {
                    vscode.postMessage({ type: 'clearLogs' });
                });

                document.getElementById('shutdownButton').addEventListener('click', () => {
                    vscode.postMessage({ type: 'shutdown' });
                });

                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.type) {
                        case 'updateLogs':
                            const logsContainer = document.getElementById('logsContainer');
                            if (logsContainer) {
                                logsContainer.innerHTML = message.logs.map(log => 
                                    '<div class="log-entry">' + escapeHtml(log) + '</div>'
                                ).join('');
                                logsContainer.scrollTop = logsContainer.scrollHeight;
                            }
                            break;
                        case 'setPid':
                            const pidElement = document.getElementById('pid');
                            if (pidElement) {
                                pidElement.textContent = message.pid;
                            }
                            break;
                    }
                });

                vscode.postMessage({ type: 'getPid' });
            }());
        `;

        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Copilot Debug</title>
            <style>
                body { font-family: sans-serif; padding: 10px; background-color: #252526; color: #cccccc; }
                .status-bar { position: fixed; top: 0; left: 0; right: 0; background-color: #1e1e1e; padding: 5px 10px; font-size: 12px; border-bottom: 1px solid #444; z-index: 100; }
                #pid { font-weight: bold; color: #4ec9b0; }
                .container { margin-top: 40px; }
                textarea { width: 100%; box-sizing: border-box; height: 150px; background-color: #3c3c3c; color: #cccccc; border: 1px solid #444; margin-bottom: 10px; }
                button { background-color: #0e639c; color: white; border: none; padding: 10px 15px; margin-right: 5px; cursor: pointer; }
                button:hover { background-color: #1177bb; }
                .danger-button { background-color: #d13438; }
                .danger-button:hover { background-color: #e54b4f; }
                #logsContainer { margin-top: 10px; height: 300px; overflow-y: auto; border: 1px solid #444; padding: 10px; background-color: #1e1e1e; }
                .log-entry { white-space: pre-wrap; margin-bottom: 5px; border-bottom: 1px solid #333; padding-bottom: 5px; }
            </style>
        </head>
        <body>
            <div class="status-bar">
                Attached to Process ID: <span id="pid">loading...</span>
            </div>
            <div class="container">
                <textarea id="promptInput" placeholder="Enter your prompt here..."></textarea>
                <button id="sendButton">Send Prompt</button>
                <button id="clearButton">Clear Logs</button>
                <button id="shutdownButton" class="danger-button">Shutdown Window</button>
                <div id="logsContainer"></div>
            </div>
            <script nonce="${nonce}">${script}</script>
        </body>
        </html>`;
    }

    public setCopilotService(service: CopilotService): void {
        this.copilotService = service;
    }

    public setModelManager(manager: ModelManager): void {
        this.modelManager = manager;
    }

    public setModeManager(manager: ModeManager): void {
        this.modeManager = manager;
    }

    public setUIManager(manager: UIManager): void {
        this.uiManager = manager;
        console.log('🔧 UIManager set, will be used when WebView is initialized');
    }
}
