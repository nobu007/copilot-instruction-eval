import * as vscode from 'vscode';
import { ModelManager } from '../services/ModelManager';
import { ModeManager, CopilotMode } from '../services/ModeManager';
import { CopilotService } from '../services/CopilotService';

export class UIManager {
    private static instance: UIManager;
    private webviewView: vscode.WebviewView | undefined;
    private modelManager: ModelManager;
    private modeManager: ModeManager;
    private copilotService: CopilotService;

    private constructor(private extensionUri: vscode.Uri) {
        this.modelManager = ModelManager.getInstance();
        this.modeManager = ModeManager.getInstance();
        this.copilotService = CopilotService.getInstance();
    }

    public static getInstance(extensionUri: vscode.Uri): UIManager {
        if (!UIManager.instance) {
            UIManager.instance = new UIManager(extensionUri);
        }
        return UIManager.instance;
    }

    public setWebviewView(webviewView: vscode.WebviewView): void {
        this.webviewView = webviewView;
    }

    /**
     * WebView用のHTMLを生成
     */
    public getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copilot Automation</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 10px;
            margin: 0;
        }
        
        .section {
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid var(--vscode-panel-border);
            border-radius: 5px;
            background-color: var(--vscode-editor-background);
        }
        
        .section-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: var(--vscode-textLink-foreground);
            font-size: 14px;
        }
        
        .control-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: var(--vscode-foreground);
        }
        
        select, input, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--vscode-input-border);
            border-radius: 3px;
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            font-family: inherit;
            font-size: inherit;
            box-sizing: border-box;
        }
        
        select:focus, input:focus, textarea:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        
        button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 3px;
            cursor: pointer;
            font-family: inherit;
            font-size: inherit;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        
        button:disabled {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            cursor: not-allowed;
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-active { background-color: #4CAF50; }
        .status-inactive { background-color: #757575; }
        
        .mode-info {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
            margin-top: 5px;
        }
        
        .model-info {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 3px;
        }
        
        .log-area {
            background-color: var(--vscode-terminal-background);
            color: var(--vscode-terminal-foreground);
            padding: 10px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family);
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .feature-list {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 5px;
            padding-left: 15px;
        }
        
        .feature-list li {
            margin-bottom: 2px;
        }
        
        .refresh-btn {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            padding: 4px 8px;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <!-- Model Selection Section -->
    <div class="section">
        <div class="section-title">🤖 Model Selection</div>
        <div class="control-group">
            <label for="modelSelect">Select Language Model:</label>
            <select id="modelSelect">
                <option value="">Loading models...</option>
            </select>
            <div class="model-info" id="modelInfo">Select a model to see details</div>
            <button class="refresh-btn" onclick="refreshModels()">🔄 Refresh</button>
        </div>
    </div>

    <!-- Mode Selection Section -->
    <div class="section">
        <div class="section-title">⚙️ Copilot Mode</div>
        <div class="control-group">
            <label for="modeSelect">Select Mode:</label>
            <select id="modeSelect">
                <option value="agent">🤖 Agent Mode</option>
                <option value="chat">💬 Chat Mode</option>
            </select>
            <div class="mode-info" id="modeInfo">
                <strong>Agent Mode:</strong> Autonomous multi-file editing, tool invocation, iterative problem solving
            </div>
        </div>
    </div>

    <!-- Prompt Section -->
    <div class="section">
        <div class="section-title">💬 Send Prompt</div>
        <div class="control-group">
            <label for="promptInput">Enter your prompt:</label>
            <textarea id="promptInput" rows="4" placeholder="Enter your prompt here..."></textarea>
        </div>
        <div class="control-group">
            <button onclick="sendPrompt()">🚀 Send Prompt</button>
            <button onclick="sendPromptToUI()">📤 Send to Copilot UI</button>
            <button onclick="getCopilotState()">📊 Get State</button>
        </div>
    </div>

    <!-- Status Section -->
    <div class="section">
        <div class="section-title">📊 Status</div>
        <div id="statusInfo">
            <div><span class="status-indicator status-inactive"></span>Ready</div>
        </div>
    </div>

    <!-- Logs Section -->
    <div class="section">
        <div class="section-title">📝 Logs</div>
        <div class="log-area" id="logArea">Extension loaded. Ready to use.</div>
        <button onclick="clearLogs()">🗑️ Clear Logs</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        // Initialize UI
        window.addEventListener('load', () => {
            refreshModels();
            refreshModes();
            updateStatus();
        });

        function refreshModels() {
            vscode.postMessage({ type: 'refreshModels' });
            addLog('Refreshing available models...');
        }

        function refreshModes() {
            vscode.postMessage({ type: 'refreshModes' });
        }

        function sendPrompt() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) {
                addLog('❌ Please enter a prompt');
                return;
            }
            
            vscode.postMessage({ 
                type: 'sendPrompt', 
                prompt: prompt 
            });
            addLog(\`🚀 Sending prompt: \${prompt.substring(0, 50)}...\`);
        }

        function sendPromptToUI() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) {
                addLog('❌ Please enter a prompt');
                return;
            }
            
            vscode.postMessage({ 
                type: 'sendPromptToUI', 
                prompt: prompt 
            });
            addLog(\`📤 Sending prompt to Copilot UI: \${prompt.substring(0, 50)}...\`);
        }

        function getCopilotState() {
            vscode.postMessage({ type: 'getCopilotState' });
            addLog('📊 Getting Copilot state...');
        }

        function clearLogs() {
            document.getElementById('logArea').textContent = '';
        }

        function updateStatus() {
            vscode.postMessage({ type: 'getStatus' });
        }

        function addLog(message) {
            const logArea = document.getElementById('logArea');
            const timestamp = new Date().toLocaleTimeString();
            logArea.textContent += \`[\${timestamp}] \${message}\\n\`;
            logArea.scrollTop = logArea.scrollHeight;
        }

        // Handle model selection change
        document.getElementById('modelSelect').addEventListener('change', (e) => {
            const modelId = e.target.value;
            if (modelId) {
                vscode.postMessage({ 
                    type: 'selectModel', 
                    modelId: modelId 
                });
                addLog(\`🤖 Selected model: \${e.target.options[e.target.selectedIndex].text}\`);
            }
        });

        // Handle mode selection change
        document.getElementById('modeSelect').addEventListener('change', (e) => {
            const mode = e.target.value;
            vscode.postMessage({ 
                type: 'switchMode', 
                mode: mode 
            });
            addLog(\`⚙️ Switching to \${mode} mode...\`);
        });

        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'updateModels':
                    updateModelSelect(message.models);
                    break;
                case 'updateModes':
                    updateModeSelect(message.modes);
                    break;
                case 'updateStatus':
                    updateStatusDisplay(message.status);
                    break;
                case 'log':
                    addLog(message.message);
                    break;
                case 'error':
                    addLog(\`❌ Error: \${message.message}\`);
                    break;
                case 'success':
                    addLog(\`✅ \${message.message}\`);
                    break;
            }
        });

        function updateModelSelect(models) {
            const select = document.getElementById('modelSelect');
            const modelInfo = document.getElementById('modelInfo');
            
            select.innerHTML = '';
            
            if (models.length === 0) {
                select.innerHTML = '<option value="">No models available</option>';
                modelInfo.textContent = 'No models found. Please check your Copilot setup.';
                return;
            }
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.displayName;
                if (model.selected) {
                    option.selected = true;
                    modelInfo.innerHTML = \`<strong>\${model.name}</strong> by \${model.vendor}\`;
                }
                select.appendChild(option);
            });
            
            addLog(\`🤖 Loaded \${models.length} models\`);
        }

        function updateModeSelect(modes) {
            const select = document.getElementById('modeSelect');
            const modeInfo = document.getElementById('modeInfo');
            
            modes.forEach(mode => {
                if (mode.selected) {
                    select.value = mode.id;
                    modeInfo.innerHTML = \`<strong>\${mode.name}:</strong> \${mode.description}\`;
                }
            });
        }

        function updateStatusDisplay(status) {
            const statusInfo = document.getElementById('statusInfo');
            const indicator = status.ready ? 'status-active' : 'status-inactive';
            const statusText = status.ready ? 'Ready' : 'Not Ready';
            
            statusInfo.innerHTML = \`
                <div><span class="status-indicator \${indicator}"></span>\${statusText}</div>
                <div style="font-size: 11px; color: var(--vscode-descriptionForeground); margin-top: 5px;">
                    Model: \${status.selectedModel || 'None'}<br>
                    Mode: \${status.currentMode || 'Unknown'}<br>
                    Models Available: \${status.availableModelsCount || 0}
                </div>
            \`;
        }
    </script>
</body>
</html>`;
    }

    /**
     * WebViewからのメッセージを処理
     */
    public async handleMessage(message: any): Promise<void> {
        console.log('📨 UIManager received message:', message.type, message);
        try {
            switch (message.type) {
                case 'refreshModels':
                    await this.handleRefreshModels();
                    break;
                case 'refreshModes':
                    await this.handleRefreshModes();
                    break;
                case 'selectModel':
                    await this.handleSelectModel(message.modelId);
                    break;
                case 'switchMode':
                    await this.handleSwitchMode(message.mode);
                    break;
                case 'sendPrompt':
                    await this.handleSendPrompt(message.prompt);
                    break;
                case 'sendPromptToUI':
                    await this.handleSendPromptToUI(message.prompt);
                    break;
                case 'getCopilotState':
                    await this.handleGetCopilotState();
                    break;
                case 'getStatus':
                    await this.handleGetStatus();
                    break;
                default:
                    console.warn('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error handling message:', error);
            this.sendMessage({
                type: 'error',
                message: error instanceof Error ? error.message : String(error)
            });
        }
    }

    private async handleRefreshModels(): Promise<void> {
        console.log('🔄 UIManager: handleRefreshModels called');
        
        if (!this.modelManager) {
            console.error('❌ ModelManager not initialized!');
            this.sendMessage({
                type: 'error',
                message: 'ModelManager not available'
            });
            return;
        }
        
        const models = await this.modelManager.refreshAvailableModels();
        const modelsForUI = this.modelManager.getModelsForUI();
        
        console.log(`📊 Found ${models.length} models:`, modelsForUI);
        
        this.sendMessage({
            type: 'updateModels',
            models: modelsForUI
        });
        
        this.sendMessage({
            type: 'log',
            message: `🔄 Refreshed models: ${models.length} available`
        });
    }

    private async handleRefreshModes(): Promise<void> {
        const modesForUI = this.modeManager.getModesForUI();
        
        this.sendMessage({
            type: 'updateModes',
            modes: modesForUI
        });
    }

    private async handleSelectModel(modelId: string): Promise<void> {
        console.log('🎯 UIManager: handleSelectModel called with:', modelId);
        
        if (!this.modelManager) {
            console.error('❌ ModelManager not initialized!');
            this.sendMessage({
                type: 'error',
                message: 'ModelManager not available'
            });
            return;
        }
        
        const success = this.modelManager.selectModel(modelId);
        if (success) {
            const selectedModel = this.modelManager.getSelectedModel();
            console.log('✅ Model selected successfully:', selectedModel?.name);
            this.sendMessage({
                type: 'success',
                message: `Model selected: ${selectedModel?.name}`
            });
        } else {
            console.error('❌ Failed to select model:', modelId);
            this.sendMessage({
                type: 'error',
                message: 'Failed to select model'
            });
        }
        
        await this.handleGetStatus();
    }

    private async handleSwitchMode(mode: string): Promise<void> {
        console.log('⚙️ UIManager: handleSwitchMode called with:', mode);
        
        if (!this.modeManager) {
            console.error('❌ ModeManager not initialized!');
            this.sendMessage({
                type: 'error',
                message: 'ModeManager not available'
            });
            return;
        }
        
        const copilotMode = mode as CopilotMode;
        const success = await this.modeManager.switchMode(copilotMode);
        
        if (success) {
            console.log('✅ Mode switched successfully to:', mode);
            this.sendMessage({
                type: 'success',
                message: `Switched to ${mode} mode`
            });
        } else {
            this.sendMessage({
                type: 'error',
                message: `Failed to switch to ${mode} mode`
            });
        }
        
        await this.handleGetStatus();
    }

    private async handleSendPrompt(prompt: string): Promise<void> {
        const response = await this.copilotService.sendPrompt(prompt);
        
        if (response.success) {
            await this.copilotService.displayResponse(response);
            this.sendMessage({
                type: 'success',
                message: `Response received from ${response.model}`
            });
        } else {
            this.sendMessage({
                type: 'error',
                message: `Failed to get response: ${response.error}`
            });
        }
    }

    private async handleSendPromptToUI(prompt: string): Promise<void> {
        const success = await this.copilotService.sendPromptToUI(prompt);
        
        if (success) {
            this.sendMessage({
                type: 'success',
                message: 'Prompt sent to Copilot UI'
            });
        } else {
            this.sendMessage({
                type: 'error',
                message: 'Failed to send prompt to UI'
            });
        }
    }

    private async handleGetCopilotState(): Promise<void> {
        const state = await this.copilotService.getCopilotState();
        this.sendMessage({
            type: 'log',
            message: `State: ${JSON.stringify(state, null, 2)}`
        });
    }

    private async handleGetStatus(): Promise<void> {
        const selectedModel = this.modelManager.getSelectedModel();
        const currentMode = this.modeManager.getCurrentMode();
        const availableModels = this.modelManager.getAvailableModels();
        
        this.sendMessage({
            type: 'updateStatus',
            status: {
                ready: selectedModel !== null,
                selectedModel: selectedModel?.name || null,
                currentMode: currentMode,
                availableModelsCount: availableModels.length
            }
        });
    }

    private sendMessage(message: any): void {
        if (this.webviewView) {
            this.webviewView.webview.postMessage(message);
        }
    }
}
