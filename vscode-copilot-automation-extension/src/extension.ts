import * as vscode from 'vscode';
import { CopilotDebugProvider } from './CopilotDebugProvider';
import { CopilotService } from './services/CopilotService';
import { ModelManager } from './services/ModelManager';
import { ModeManager, CopilotMode } from './services/ModeManager';
import { UIManager } from './ui/UIManager';

/**
 * VSCode Extension for Copilot Automation - Refactored Version
 * 内部APIを使用してGitHub Copilotとの確実な自動化を実現
 * 
 * Features:
 * - Model selection (Copilot, GPT-4, Claude, etc.)
 * - Agent/Chat mode switching
 * - Clean modular architecture
 * - Enhanced UI with WebView
 */

export async function activate(context: vscode.ExtensionContext) {
    console.log('🚀 Copilot Automation Extension (Enhanced) is now active!');

    try {
        // Initialize services
        const copilotService = CopilotService.getInstance();
        const modelManager = ModelManager.getInstance();
        const modeManager = ModeManager.getInstance();
        const uiManager = UIManager.getInstance(context.extensionUri);
        
        // Initialize Copilot service
        await copilotService.initialize();
        console.log('✅ Services initialized successfully');

        // Register WebView Provider with enhanced functionality
        const debugProvider = new CopilotDebugProvider(context.extensionUri);
        
        // Inject services into the debug provider
        debugProvider.setCopilotService(copilotService);
        debugProvider.setModelManager(modelManager);
        debugProvider.setModeManager(modeManager);
        debugProvider.setUIManager(uiManager);
        
        context.subscriptions.push(
            vscode.window.registerWebviewViewProvider(CopilotDebugProvider.viewType, debugProvider)
        );

        // Register commands
        registerCommands(context, copilotService, modelManager, modeManager);
        
        console.log('🎉 Copilot Automation Extension activated successfully!');
        vscode.window.showInformationMessage('🤖 Enhanced Copilot Automation Extension is ready!');
        
    } catch (error) {
        console.error('❌ Failed to activate extension:', error);
        vscode.window.showErrorMessage(`Failed to activate Copilot Automation: ${error}`);
    }
}

function registerCommands(
    context: vscode.ExtensionContext,
    copilotService: CopilotService,
    modelManager: ModelManager,
    modeManager: ModeManager
) {
    // Send Prompt Command
    const sendPromptCommand = vscode.commands.registerCommand('copilotAutomation.sendPrompt', async () => {
        try {
            const prompt = await vscode.window.showInputBox({
                prompt: 'Enter your prompt for Copilot',
                placeHolder: 'What would you like Copilot to help you with?'
            });
            
            if (!prompt) {
                return;
            }
            
            const response = await copilotService.sendPrompt(prompt);
            await copilotService.displayResponse(response);
            
        } catch (error) {
            console.error('Error in sendPrompt command:', error);
            vscode.window.showErrorMessage(`Failed to send prompt: ${error}`);
        }
    });

    // Send Prompt to UI Command
    const sendPromptToUICommand = vscode.commands.registerCommand('copilotAutomation.sendPromptToUI', async () => {
        try {
            const prompt = await vscode.window.showInputBox({
                prompt: 'Enter your prompt to send to Copilot UI',
                placeHolder: 'This will open Copilot UI and send your prompt'
            });
            
            if (!prompt) {
                return;
            }
            
            await copilotService.sendPromptToUI(prompt);
            
        } catch (error) {
            console.error('Error in sendPromptToUI command:', error);
            vscode.window.showErrorMessage(`Failed to send prompt to UI: ${error}`);
        }
    });

    // Get Copilot State Command
    const getCopilotStateCommand = vscode.commands.registerCommand('copilotAutomation.getCopilotState', async () => {
        try {
            const state = await copilotService.getCopilotState();
            const stateMessage = `Models: ${state.availableModelsCount || 0}, Mode: ${state.currentMode}, Selected: ${state.selectedModel?.name || 'None'}`;
            
            console.log('Copilot state:', state);
            vscode.window.showInformationMessage(`Copilot State - ${stateMessage}`);
            
        } catch (error) {
            console.error('Error getting Copilot state:', error);
            vscode.window.showErrorMessage(`Failed to get state: ${error}`);
        }
    });

    // Switch Mode Command
    const switchModeCommand = vscode.commands.registerCommand('copilotAutomation.switchMode', async () => {
        try {
            const currentMode = modeManager.getCurrentMode();
            const modes = modeManager.getAllModes();
            
            const items = modes.map(mode => ({
                label: `${mode.mode === currentMode ? '✅' : '⚪'} ${mode.mode.toUpperCase()} Mode`,
                description: mode.description,
                detail: mode.features.join(', '),
                mode: mode.mode
            }));
            
            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select Copilot mode',
                title: 'Switch Copilot Mode'
            });
            
            if (selected && selected.mode !== currentMode) {
                await modeManager.switchMode(selected.mode as CopilotMode);
            }
            
        } catch (error) {
            console.error('Error switching mode:', error);
            vscode.window.showErrorMessage(`Failed to switch mode: ${error}`);
        }
    });

    // Select Model Command
    const selectModelCommand = vscode.commands.registerCommand('copilotAutomation.selectModel', async () => {
        try {
            await modelManager.refreshAvailableModels();
            const models = modelManager.getAvailableModels();
            const selectedModel = modelManager.getSelectedModel();
            
            if (models.length === 0) {
                vscode.window.showWarningMessage('No models available. Please check your Copilot setup.');
                return;
            }
            
            const items = models.map(model => ({
                label: `${model.id === selectedModel?.id ? '✅' : '⚪'} ${model.name}`,
                description: `${model.vendor} - ${model.family}`,
                detail: `Max tokens: ${model.maxInputTokens || 'Unknown'}`,
                modelId: model.id
            }));
            
            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select a language model',
                title: 'Choose Copilot Model'
            });
            
            if (selected) {
                const success = modelManager.selectModel(selected.modelId);
                if (success) {
                    vscode.window.showInformationMessage(`Selected model: ${selected.label.replace('✅ ', '').replace('⚪ ', '')}`);
                }
            }
            
        } catch (error) {
            console.error('Error selecting model:', error);
            vscode.window.showErrorMessage(`Failed to select model: ${error}`);
        }
    });

    // Verify Extension Command
    const verifyPromptSentCommand = vscode.commands.registerCommand('copilotAutomation.verifyPromptSent', async () => {
        try {
            const state = await copilotService.getCopilotState();
            const message = `Extension is working! Models: ${state.availableModelsCount}, Mode: ${state.currentMode}`;
            
            console.log('Verification successful:', message);
            vscode.window.showInformationMessage(message);
            
        } catch (error) {
            console.error('Verification failed:', error);
            vscode.window.showErrorMessage(`Verification failed: ${error}`);
        }
    });

    // Register all commands
    context.subscriptions.push(
        sendPromptCommand,
        sendPromptToUICommand,
        getCopilotStateCommand,
        switchModeCommand,
        selectModelCommand,
        verifyPromptSentCommand
    );
}

/**
 * Enhanced WebView Provider with new UI
 */
class EnhancedCopilotDebugProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'copilotAutomation.enhancedDebugView';
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly uiManager: UIManager
    ) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;
        this.uiManager.setWebviewView(webviewView);

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this.uiManager.getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(
            async (message) => {
                await this.uiManager.handleMessage(message);
            },
            undefined,
        );
    }
}

export function deactivate() {
    console.log('🔄 Enhanced Copilot Automation Extension deactivated');
}
