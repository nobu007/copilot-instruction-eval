/**
 * Log Display WebView Provider
 * 
 * リアルタイムログ表示・設定管理UI
 */

import * as vscode from 'vscode';
import * as path from 'path';

export interface LogEntry {
    timestamp: string;
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
    category: string;
    data?: any;
}

export class LogDisplayProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'copilotAutomation.logDisplay';
    
    private _view?: vscode.WebviewView;
    private _logs: LogEntry[] = [];
    private _maxLogs = 1000;
    
    constructor(private readonly _extensionUri: vscode.Uri) {}
    
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
        
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
        
        // メッセージハンドラー
        webviewView.webview.onDidReceiveMessage(
            message => {
                console.log('🔍 Received message:', message);
                const messageType = message.type || message.command;
                console.log('📝 Message type:', messageType);
                
                switch (messageType) {
                    case 'clearLogs':
                        this.clearLogs();
                        break;
                    case 'exportLogs':
                        this.exportLogs();
                        break;
                    case 'reprocessFailedRequests':
                        this.reprocessFailedRequests();
                        break;
                    case 'reprocessRequest':
                        if (message.requestId) {
                            this.reprocessSingleRequest(message.requestId);
                        }
                        break;
                    case 'setLogLevel':
                        this.setLogLevel(message.level);
                        break;
                    case 'setBaseDirectory':
                        this.setBaseDirectory(message.directory);
                        break;
                    case 'getStatus':
                        this.sendStatus();
                        break;
                }
            },
            undefined,
            []
        );
        
        // 初期状態送信
        this.sendStatus();
        this.sendAllLogs();
    }
    
    public addLog(entry: LogEntry) {
        entry.timestamp = new Date().toISOString();
        this._logs.push(entry);
        
        // ログ数制限
        if (this._logs.length > this._maxLogs) {
            this._logs = this._logs.slice(-this._maxLogs);
        }
        
        // WebViewに送信
        if (this._view) {
            this._view.webview.postMessage({
                type: 'newLog',
                log: entry
            });
        }
    }
    
    public log(level: LogEntry['level'], message: string, category: string = 'general', data?: any) {
        this.addLog({
            timestamp: new Date().toISOString(),
            level,
            message,
            category,
            data
        });
    }
    
    public clearLogs() {
        this._logs = [];
        if (this._view) {
            this._view.webview.postMessage({
                type: 'clearLogs'
            });
        }
    }
    
    public sendAllLogs() {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'allLogs',
                logs: this._logs
            });
        }
    }
    
    public sendStatus() {
        const config = vscode.workspace.getConfiguration('copilotAutomation');
        const baseDirectory = config.get<string>('baseDirectory', '/tmp/copilot-evaluation');
        const logLevel = config.get<string>('logLevel', 'info');
        
        if (this._view) {
            this._view.webview.postMessage({
                type: 'status',
                status: {
                    baseDirectory,
                    logLevel,
                    totalLogs: this._logs.length,
                    extensionActive: true
                }
            });
        }
    }
    
    private async exportLogs() {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `copilot-logs-${timestamp}.json`;
            
            const uri = await vscode.window.showSaveDialog({
                defaultUri: vscode.Uri.file(filename),
                filters: {
                    'JSON files': ['json'],
                    'All files': ['*']
                }
            });
            
            if (uri) {
                const logsData = {
                    timestamp: new Date().toISOString(),
                    logs: this._logs,
                    baseDirectory: vscode.workspace.getConfiguration('copilotAutomation').get<string>('baseDirectory', '/tmp/copilot-evaluation'),
                    logLevel: vscode.workspace.getConfiguration('copilotAutomation').get<string>('logLevel', 'info')
                };
                
                await vscode.workspace.fs.writeFile(uri, Buffer.from(JSON.stringify(logsData, null, 2)));
                vscode.window.showInformationMessage(`Logs exported to: ${uri.fsPath}`);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to export logs: ${error}`);
        }
    }
    
    private async reprocessFailedRequests() {
        console.log('♻️ Starting reprocessFailedRequests...');
        this.log('info', 'Starting reprocess all failed requests', 'reprocessing');
        
        try {
            const handler = (global as any).enhancedFileRequestHandler;
            console.log('🔍 Handler available:', !!handler);
            
            if (!handler) {
                console.error('❌ File request handler not available');
                vscode.window.showErrorMessage('File request handler not available');
                this.log('error', 'File request handler not available', 'reprocessing');
                return;
            }
            
            const count = await handler.reprocessFailedRequests();
            this.log('info', `Reprocessed ${count} failed requests`, 'reprocessing');
            vscode.window.showInformationMessage(`Successfully reprocessed ${count} failed requests`);
            
        } catch (error) {
            this.log('error', `Failed to reprocess requests: ${error}`, 'reprocessing');
            vscode.window.showErrorMessage(`Failed to reprocess requests: ${error}`);
        }
    }
    
    private async reprocessSingleRequest(requestId: string) {
        console.log(`🔄 Starting reprocessSingleRequest for: ${requestId}`);
        this.log('info', `Starting reprocess single request: ${requestId}`, 'reprocessing');
        
        try {
            const handler = (global as any).enhancedFileRequestHandler;
            console.log('🔍 Handler available:', !!handler);
            
            if (!handler) {
                console.error('❌ File request handler not available');
                vscode.window.showErrorMessage('File request handler not available');
                this.log('error', 'File request handler not available', 'reprocessing');
                return;
            }
            
            const success = await handler.reprocessRequest(requestId);
            if (success) {
                this.log('info', `Reprocessed request: ${requestId}`, 'reprocessing');
                vscode.window.showInformationMessage(`Successfully reprocessed: ${requestId}`);
            } else {
                this.log('warn', `Failed to reprocess: ${requestId}`, 'reprocessing');
                vscode.window.showWarningMessage(`Failed to reprocess: ${requestId}`);
            }
            
        } catch (error) {
            this.log('error', `Failed to reprocess ${requestId}: ${error}`, 'reprocessing');
            vscode.window.showErrorMessage(`Failed to reprocess ${requestId}: ${error}`);
        }
    }
    
    private async setLogLevel(level: string) {
        const config = vscode.workspace.getConfiguration('copilotAutomation');
        await config.update('logLevel', level, vscode.ConfigurationTarget.Global);
        
        this.log('info', `Log level changed to: ${level}`, 'config');
        this.sendStatus();
    }
    
    private async setBaseDirectory(directory: string) {
        try {
            // ディレクトリの存在確認
            const uri = vscode.Uri.file(directory);
            const stat = await vscode.workspace.fs.stat(uri);
            
            if (stat.type === vscode.FileType.Directory) {
                const config = vscode.workspace.getConfiguration('copilotAutomation');
                await config.update('baseDirectory', directory, vscode.ConfigurationTarget.Global);
                
                this.log('info', `Base directory changed to: ${directory}`, 'config');
                this.sendStatus();
                
                vscode.window.showInformationMessage(`Base directory updated: ${directory}`);
            } else {
                throw new Error('Path is not a directory');
            }
        } catch (error) {
            this.log('error', `Failed to set base directory: ${error}`, 'config');
            vscode.window.showErrorMessage(`Invalid directory: ${directory}`);
        }
    }
    
    private _getHtmlForWebview(webview: vscode.Webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copilot Automation Logs</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            margin: 0;
            padding: 10px;
        }
        
        .header {
            margin-bottom: 15px;
            padding: 10px;
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 5px;
            margin-bottom: 10px;
            font-size: 0.9em;
        }
        
        .status-label {
            font-weight: bold;
        }
        
        .controls {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.9em;
        }
        
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        
        input, select {
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .logs-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
        }
        
        .log-entry {
            padding: 8px;
            border-bottom: 1px solid var(--vscode-panel-border);
            font-family: var(--vscode-editor-font-family);
            font-size: 0.85em;
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .log-timestamp {
            color: var(--vscode-descriptionForeground);
            font-size: 0.8em;
        }
        
        .log-level {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
        }
        
        .log-level.info {
            background-color: #0066cc;
            color: white;
        }
        
        .log-level.warn {
            background-color: #ff9900;
            color: white;
        }
        
        .log-level.error {
            background-color: #cc0000;
            color: white;
        }
        
        .log-level.debug {
            background-color: #666666;
            color: white;
        }
        
        .log-message {
            margin: 4px 0;
        }
        
        .log-category {
            color: var(--vscode-descriptionForeground);
            font-style: italic;
            font-size: 0.8em;
        }
        
        .log-data {
            background-color: var(--vscode-textCodeBlock-background);
            padding: 4px;
            border-radius: 3px;
            margin-top: 4px;
            font-family: var(--vscode-editor-font-family);
            font-size: 0.8em;
            white-space: pre-wrap;
        }
        
        .no-logs {
            text-align: center;
            color: var(--vscode-descriptionForeground);
            padding: 20px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>🤖 Copilot Automation Monitor</h3>
        <div class="status-grid">
            <span class="status-label">Base Directory:</span>
            <span id="baseDirectory">Loading...</span>
            <span class="status-label">Log Level:</span>
            <span id="logLevel">Loading...</span>
            <span class="status-label">Total Logs:</span>
            <span id="totalLogs">0</span>
            <span class="status-label">Status:</span>
            <span id="extensionStatus">Loading...</span>
        </div>
    </div>
    
    <div class="controls">
        <div class="control-group">
            <label>Base Dir:</label>
            <input type="text" id="baseDirInput" placeholder="/tmp/copilot-evaluation" style="width: 200px;">
            <button onclick="setBaseDirectory()">Set</button>
        </div>
        
        <div class="control-group">
            <label>Log Level:</label>
            <select id="logLevelSelect" onchange="setLogLevel()">
                <option value="debug">Debug</option>
                <option value="info">Info</option>
                <option value="warn">Warn</option>
                <option value="error">Error</option>
            </select>
        </div>
        
        <button onclick="refreshStatus()">🔄 Refresh</button>
        <button onclick="clearLogs()">🗑️ Clear Logs</button>
        <button onclick="exportLogs()">💾 Export Logs</button>
        <button onclick="reprocessFailedRequests()" class="reprocess-btn">♻️ Reprocess All Failed</button>
        <button onclick="showReprocessDialog()" class="reprocess-btn">🔄 Reprocess Single</button>
    </div>
    
    <div class="logs-container" id="logsContainer">
        <div class="no-logs">No logs yet. Waiting for activity...</div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let logs = [];
        
        // メッセージリスナー
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'newLog':
                    addLogEntry(message.log);
                    break;
                case 'allLogs':
                    logs = message.logs;
                    renderAllLogs();
                    break;
                case 'clearLogs':
                    logs = [];
                    renderAllLogs();
                    break;
                case 'status':
                    updateStatus(message.status);
                    break;
            }
        });
        
        function addLogEntry(log) {
            logs.push(log);
            renderLogEntry(log);
            scrollToBottom();
        }
        
        function renderLogEntry(log) {
            const container = document.getElementById('logsContainer');
            
            // "No logs" メッセージを削除
            if (container.querySelector('.no-logs')) {
                container.innerHTML = '';
            }
            
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            const timestamp = new Date(log.timestamp).toLocaleTimeString();
            
            entry.innerHTML = \`
                <div class="log-header">
                    <span class="log-timestamp">\${timestamp}</span>
                    <span class="log-level \${log.level}">\${log.level.toUpperCase()}</span>
                </div>
                <div class="log-message">\${log.message}</div>
                <div class="log-category">[\${log.category}]</div>
                \${log.data ? \`<div class="log-data">\${JSON.stringify(log.data, null, 2)}</div>\` : ''}
            \`;
            
            container.appendChild(entry);
        }
        
        function renderAllLogs() {
            const container = document.getElementById('logsContainer');
            container.innerHTML = '';
            
            if (logs.length === 0) {
                container.innerHTML = '<div class="no-logs">No logs yet. Waiting for activity...</div>';
                return;
            }
            
            logs.forEach(log => renderLogEntry(log));
            scrollToBottom();
        }
        
        function updateStatus(status) {
            document.getElementById('baseDirectory').textContent = status.baseDirectory;
            document.getElementById('logLevel').textContent = status.logLevel;
            document.getElementById('totalLogs').textContent = status.totalLogs;
            document.getElementById('extensionStatus').textContent = status.extensionActive ? '✅ Active' : '❌ Inactive';
            
            document.getElementById('baseDirInput').value = status.baseDirectory;
            document.getElementById('logLevelSelect').value = status.logLevel;
        }
        
        function scrollToBottom() {
            const container = document.getElementById('logsContainer');
            container.scrollTop = container.scrollHeight;
        }
        
        function setBaseDirectory() {
            const directory = document.getElementById('baseDirInput').value;
            if (directory.trim()) {
                vscode.postMessage({
                    type: 'setBaseDirectory',
                    directory: directory.trim()
                });
            }
        }
        
        function setLogLevel() {
            const level = document.getElementById('logLevelSelect').value;
            vscode.postMessage({
                type: 'setLogLevel',
                level: level
            });
        }
        
        function refreshStatus() {
            vscode.postMessage({ type: 'getStatus' });
        }
        
        function clearLogs() {
            vscode.postMessage({ type: 'clearLogs' });
        }
        
        function exportLogs() {
            vscode.postMessage({
                command: 'exportLogs'
            });
        }
        
        function reprocessFailedRequests() {
            if (confirm('すべての失敗したリクエストを再処理しますか？')) {
                vscode.postMessage({
                    command: 'reprocessFailedRequests'
                });
            }
        }
        
        function showReprocessDialog() {
            const requestId = prompt('再処理するリクエストIDを入力してください（例: req_test001）:');
            if (requestId && requestId.trim()) {
                vscode.postMessage({
                    command: 'reprocessRequest',
                    requestId: requestId.trim()
                });
            }
        }
        
        // 初期化
        refreshStatus();
    </script>
</body>
</html>`;
    }
}
