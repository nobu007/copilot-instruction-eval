import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { CopilotDebugProvider } from './CopilotDebugProvider';
import { CopilotService } from './services/CopilotService';
import { ModelManager } from './services/ModelManager';
import { ModeManager, CopilotMode } from './services/ModeManager';
import { UIManager } from './ui/UIManager';
import { FileRequestHandler } from './FileRequestHandler';
import { LogDisplayProvider } from './ui/LogDisplayProvider';
import * as crypto from 'crypto';

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

const PID_HEARTBEAT_INTERVAL = 15000; // 15秒ごとにPIDを更新
let pidHeartbeatInterval: NodeJS.Timeout | null = null;

function isProcessRunning(pid: number): boolean {
    try {
        // process.kill with signal 0 is a cross-platform way to check for process existence
        process.kill(pid, 0);
        return true;
    } catch (e) {
        return false;
    }
}

function getWorkspaceId(): string | null {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!workspaceFolder) {
        return null;
    }
    // Create a stable, filesystem-safe ID from the workspace path
    return crypto.createHash('md5').update(workspaceFolder).digest('hex');
}

export async function activate(context: vscode.ExtensionContext) {
    // --- Workspace-aware Singleton Lock ---
    const workspaceId = getWorkspaceId();
    if (!workspaceId) {
        const noWorkspaceMsg = '[Singleton] No workspace folder open. The extension requires a workspace to activate.';
        console.warn(noWorkspaceMsg);
        vscode.window.showWarningMessage(noWorkspaceMsg);
        return; // Do not activate without a workspace
    }

    const configForLock = vscode.workspace.getConfiguration('copilotAutomation');
    const baseDirectoryForLock = configForLock.get<string>('baseDirectory', '/tmp/copilot-evaluation');
    const stateDir = path.join(baseDirectoryForLock, 'state');
    const lockFile = path.join(stateDir, `ws.${workspaceId}.lock`);

    try {
        if (!fs.existsSync(stateDir)) {
            fs.mkdirSync(stateDir, { recursive: true });
        }

        if (fs.existsSync(lockFile)) {
            const lockedPid = parseInt(fs.readFileSync(lockFile, 'utf8'), 10);
            if (isProcessRunning(lockedPid)) {
                const message = `[Singleton] Another instance (PID: ${lockedPid}) is already running for this workspace. This instance (PID: ${process.pid}) will now terminate.`;
                console.error(message);
                // This is a critical failure, show a modal message and exit.
                vscode.window.showErrorMessage(message, { modal: true });
                process.exit(0);
            } else {
                console.warn(`[Singleton] Found stale lock file for PID ${lockedPid}. Taking over.`);
                fs.unlinkSync(lockFile); // Remove stale lock
            }
        }

        fs.writeFileSync(lockFile, process.pid.toString());
        console.log(`[Singleton] Acquired lock for workspace ${workspaceId} (PID: ${process.pid})`);

        context.subscriptions.push({
            dispose: () => {
                if (pidHeartbeatInterval) {
                    clearInterval(pidHeartbeatInterval);
                }
                try {
                    if (fs.existsSync(lockFile)) {
                        const lockedPid = parseInt(fs.readFileSync(lockFile, 'utf8'), 10);
                        if (lockedPid === process.pid) {
                            fs.unlinkSync(lockFile);
                            console.log(`[Singleton] Released lock for workspace ${workspaceId} (PID: ${process.pid})`);
                        }
                    }
                } catch (e) {
                    console.error('[Singleton] Failed to release lock file:', e);
                }
            }
        });

        pidHeartbeatInterval = setInterval(() => {
            try {
                fs.writeFileSync(lockFile, process.pid.toString());
            } catch (e) {
                // If this fails, the process might be shutting down, so we can ignore it.
            }
        }, PID_HEARTBEAT_INTERVAL);

    } catch (e) {
        const message = `[Singleton] A critical error occurred during singleton lock check. The extension will not activate. Error: ${e}`;
        console.error(message);
        vscode.window.showErrorMessage(message, { modal: true });
        return; // Do not activate the extension
    }
    // --- End Singleton Lock ---

    console.log('🚀 Copilot Automation Extension (Enhanced) is now active!');

    try {
        // Initialize services
        const copilotService = CopilotService.getInstance();
        const modelManager = ModelManager.getInstance();
        const modeManager = ModeManager.getInstance();
        const uiManager = UIManager.getInstance(context.extensionUri);
        
        // Initialize Log Display Provider
        const logDisplayProvider = new LogDisplayProvider(context.extensionUri);
        context.subscriptions.push(
            vscode.window.registerWebviewViewProvider(
                LogDisplayProvider.viewType,
                logDisplayProvider
            )
        );
        
        // Initialize Copilot service
        await copilotService.initialize();
        logDisplayProvider.log('info', 'Services initialized successfully', 'startup');
        console.log('✅ Services initialized successfully');
        
        // Initialize Enhanced File Request Handler for evaluation framework
        const config = vscode.workspace.getConfiguration('copilotAutomation');
        const baseDirectory = config.get<string>('baseDirectory', '/tmp/copilot-evaluation');
        const autoStart = config.get<boolean>('autoStart', true);
        
        logDisplayProvider.log('info', `Base directory configured: ${baseDirectory}`, 'config');
        
        const { EnhancedFileRequestHandler } = await import('./EnhancedFileRequestHandler');
        const enhancedFileRequestHandler = new EnhancedFileRequestHandler(
            copilotService,
            modelManager,
            modeManager,
            baseDirectory,
            logDisplayProvider
        );
        
        if (autoStart) {
            enhancedFileRequestHandler.start();
            console.log('✅ Enhanced File Request Handler started automatically');
        } else {
            console.log('⏸️ Enhanced File Request Handler ready (not started)');
        }
        
        // グローバルアクセス用にハンドラーを登録（UI再処理機能用）
        (global as any).enhancedFileRequestHandler = enhancedFileRequestHandler;

        // Register cleanup on deactivation
        context.subscriptions.push({
            dispose: () => enhancedFileRequestHandler.stop()
        });

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
        registerCommands(context, copilotService, modelManager, modeManager, logDisplayProvider);

        // Register the single, correct shutdown command
        context.subscriptions.push(vscode.commands.registerCommand('windsurf-dev.copilot-automation-extension.shutdown', () => {
            console.log('Received shutdown command. Exiting process.');
            logDisplayProvider.log('info', 'Shutdown command received. Exiting process...', 'lifecycle');
            // Use process.exit() for a more reliable shutdown from a CLI-triggered command.
            process.exit(0);
        }));
        
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
    modeManager: ModeManager,
    logDisplayProvider: LogDisplayProvider // LogDisplayProviderを追加
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

    // CLI Batch Prompt Execution Command
    const executeBatchPromptCommand = vscode.commands.registerCommand('copilotAutomation.executeBatchPrompt', async (promptText?: string) => {
        try {
            console.log('🚀 CLI Batch Prompt Execution Started');
            
            // Use provided prompt or ask for input
            const prompt = promptText || await vscode.window.showInputBox({
                prompt: 'Enter batch prompt for Copilot',
                placeHolder: 'Batch prompt text...'
            });
            
            if (!prompt) {
                console.log('❌ No prompt provided');
                return { success: false, error: 'No prompt provided' };
            }
            
            // Get current state
            const state = await copilotService.getCopilotState();
            console.log('📊 Current state:', state);
            
            // Send prompt to Copilot
            const response = await copilotService.sendPrompt(prompt);
            
            // Prepare result
            const result = {
                success: true,
                prompt: prompt,
                response: response,
                model: state.selectedModel,
                mode: state.currentMode,
                timestamp: new Date().toISOString(),
                executionId: Date.now().toString()
            };
            
            // Save result to file for CLI access
            await saveExecutionResult(result);
            
            // Output result to stdout for external access
            process.stdout.write('COPILOT_RESULT_START\n');
            process.stdout.write(JSON.stringify(result, null, 2));
            process.stdout.write('\nCOPILOT_RESULT_END\n');
            
            console.log('✅ Batch prompt executed successfully');
            return result;
            
        } catch (error) {
            console.error('❌ Batch prompt execution failed:', error);
            const errorResult = {
                success: false,
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date().toISOString()
            };
            
            await saveExecutionResult(errorResult);
            
            // Output error result to stdout for external access
            process.stdout.write('COPILOT_RESULT_START\n');
            process.stdout.write(JSON.stringify(errorResult, null, 2));
            process.stdout.write('\nCOPILOT_RESULT_END\n');
            
            return errorResult;
        }
    });

    // Get Execution Status Command
    const getExecutionStatusCommand = vscode.commands.registerCommand('copilotAutomation.getExecutionStatus', async () => {
        try {
            const state = await copilotService.getCopilotState();
            const models = await modelManager.getAvailableModels();
            const modes = modeManager.getModesForUI();
            
            const status = {
                extension: {
                    active: true,
                    version: '0.0.1'
                },
                copilot: {
                    availableModelsCount: models.length,
                    selectedModel: state.selectedModel,
                    currentMode: state.currentMode,
                    agentModeEnabled: state.agentModeEnabled
                },
                models: models.map(m => ({
                    id: m.id,
                    name: m.name,
                    selected: m.id === state.selectedModel
                })),
                modes: modes,
                timestamp: new Date().toISOString()
            };
            
            // Save status to file for CLI access
            await saveExecutionStatus(status);
            
            console.log('📊 Execution status retrieved');
            return status;
            
        } catch (error) {
            console.error('❌ Failed to get execution status:', error);
            const errorStatus = {
                extension: { active: false },
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date().toISOString()
            };
            
            await saveExecutionStatus(errorStatus);
            return errorStatus;
        }
    });

    // Export Results Command
    const exportResultsCommand = vscode.commands.registerCommand('copilotAutomation.exportResults', async (outputPath?: string) => {
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            const defaultPath = workspaceFolder ? 
                vscode.Uri.joinPath(workspaceFolder.uri, 'copilot_results.json').fsPath :
                'copilot_results.json';
            
            const filePath = outputPath || defaultPath;
            
            // Get current state and recent results
            const state = await copilotService.getCopilotState();
            const models = await modelManager.getAvailableModels();
            const modes = modeManager.getModesForUI();
            
            const status = {
                extension: {
                    active: true,
                    version: '0.0.1'
                },
                copilot: {
                    availableModelsCount: models.length,
                    selectedModel: state.selectedModel,
                    currentMode: state.currentMode,
                    agentModeEnabled: state.agentModeEnabled
                },
                models: models.map(m => ({
                    id: m.id,
                    name: m.name,
                    selected: m.id === state.selectedModel
                })),
                modes: modes,
                timestamp: new Date().toISOString()
            };
            
            const exportData = {
                exportTimestamp: new Date().toISOString(),
                extensionVersion: '0.0.1',
                currentState: state,
                executionStatus: status,
                metadata: {
                    workspaceFolder: workspaceFolder?.uri.fsPath,
                    exportPath: filePath
                }
            };
            
            // Write to file
            const fs = require('fs').promises;
            await fs.writeFile(filePath, JSON.stringify(exportData, null, 2), 'utf8');
            
            console.log(`📄 Results exported to: ${filePath}`);
            vscode.window.showInformationMessage(`Results exported to: ${filePath}`);
            
            return { success: true, filePath: filePath, data: exportData };
            
        } catch (error) {
            console.error('❌ Export failed:', error);
            vscode.window.showErrorMessage(`Export failed: ${error}`);
            return { success: false, error: error instanceof Error ? error.message : String(error) };
        }
    });

    // Register all commands
    context.subscriptions.push(
        sendPromptCommand,
        sendPromptToUICommand,
        getCopilotStateCommand,
        switchModeCommand,
        selectModelCommand,
        verifyPromptSentCommand,
        executeBatchPromptCommand,
        getExecutionStatusCommand,
        exportResultsCommand
    );
}

/**
 * Helper functions for CLI integration
 */
async function saveExecutionResult(result: any): Promise<void> {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const outputDir = workspaceFolder ? 
            path.join(workspaceFolder.uri.fsPath, '.vscode', 'copilot-automation') :
            path.join(process.cwd(), '.vscode', 'copilot-automation');
        
        // Ensure directory exists
        await fs.promises.mkdir(outputDir, { recursive: true });
        
        const filePath = path.join(outputDir, 'execution_result.json');
        await fs.promises.writeFile(filePath, JSON.stringify(result, null, 2), 'utf8');
        
        console.log(`💾 Execution result saved to: ${filePath}`);
    } catch (error) {
        console.error('❌ Failed to save execution result:', error);
    }
}

async function saveExecutionStatus(status: any): Promise<void> {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const outputDir = workspaceFolder ? 
            path.join(workspaceFolder.uri.fsPath, '.vscode', 'copilot-automation') :
            path.join(process.cwd(), '.vscode', 'copilot-automation');
        
        // Ensure directory exists
        await fs.promises.mkdir(outputDir, { recursive: true });
        
        const filePath = path.join(outputDir, 'execution_status.json');
        await fs.promises.writeFile(filePath, JSON.stringify(status, null, 2), 'utf8');
        
        console.log(`📊 Execution status saved to: ${filePath}`);
    } catch (error) {
        console.error('❌ Failed to save execution status:', error);
    }
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
    if (pidHeartbeatInterval) {
        clearInterval(pidHeartbeatInterval);
    }
    console.log('Deactivating extension and releasing resources.');
    console.log('🔄 Enhanced Copilot Automation Extension deactivated');
}
