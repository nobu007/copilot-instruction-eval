import * as vscode from 'vscode';
import { ModelManager } from './ModelManager';
import { ModeManager, CopilotMode } from './ModeManager';

export interface CopilotResponse {
    content: string;
    model: string;
    mode: CopilotMode;
    timestamp: Date;
    success: boolean;
    error?: string;
}

export class CopilotService {
    private static instance: CopilotService;
    private modelManager: ModelManager;
    private modeManager: ModeManager;

    private constructor() {
        this.modelManager = ModelManager.getInstance();
        this.modeManager = ModeManager.getInstance();
    }

    public static getInstance(): CopilotService {
        if (!CopilotService.instance) {
            CopilotService.instance = new CopilotService();
        }
        return CopilotService.instance;
    }

    /**
     * Copilotにプロンプトを送信して応答を取得
     */
    public async sendPrompt(prompt: string): Promise<CopilotResponse> {
        const startTime = new Date();
        
        try {
            // 選択されたモデルを取得
            const chatModel = await this.modelManager.getSelectedChatModel();
            if (!chatModel) {
                throw new Error('No chat model available');
            }

            // 現在のモードに応じてプロンプトをフォーマット
            const formattedPrompt = this.modeManager.formatPromptForCurrentMode(prompt);

            console.log(`Sending prompt to ${chatModel.name} in ${this.modeManager.getCurrentMode()} mode:`, formattedPrompt);

            // Copilotにリクエスト送信
            const request = await chatModel.sendRequest([
                vscode.LanguageModelChatMessage.User(formattedPrompt)
            ], {}, new vscode.CancellationTokenSource().token);

            let response = '';
            for await (const fragment of request.text) {
                response += fragment;
            }

            return {
                content: response,
                model: chatModel.name,
                mode: this.modeManager.getCurrentMode(),
                timestamp: startTime,
                success: true
            };

        } catch (error) {
            console.error('Failed to send prompt to Copilot:', error);
            return {
                content: '',
                model: 'unknown',
                mode: this.modeManager.getCurrentMode(),
                timestamp: startTime,
                success: false,
                error: error instanceof Error ? error.message : String(error)
            };
        }
    }

    /**
     * Copilot UIを開いてプロンプトを送信
     */
    public async sendPromptToUI(prompt: string): Promise<boolean> {
        try {
            // 現在のモードに応じてCopilot UIを開く
            const uiOpened = await this.modeManager.openCopilotUI();
            if (!uiOpened) {
                throw new Error('Failed to open Copilot UI');
            }

            // 少し待ってからプロンプトを送信
            await new Promise(resolve => setTimeout(resolve, 1000));

            // 現在のモードに応じてプロンプトをフォーマット
            const formattedPrompt = this.modeManager.formatPromptForCurrentMode(prompt);

            // クリップボードにプロンプトをコピー
            await vscode.env.clipboard.writeText(formattedPrompt);

            // Copilot入力欄にペーストを試行
            try {
                await vscode.commands.executeCommand('editor.action.clipboardPasteAction');
            } catch (error) {
                console.log('Direct paste failed, using keyboard shortcut');
                // フォールバック: Ctrl+V
                await vscode.commands.executeCommand('workbench.action.terminal.paste');
            }

            console.log(`Prompt sent to Copilot UI in ${this.modeManager.getCurrentMode()} mode`);
            return true;

        } catch (error) {
            console.error('Failed to send prompt to Copilot UI:', error);
            vscode.window.showErrorMessage(`Failed to send prompt: ${error}`);
            return false;
        }
    }

    /**
     * Copilotの状態を取得
     */
    public async getCopilotState(): Promise<any> {
        try {
            const selectedModel = this.modelManager.getSelectedModel();
            const currentMode = this.modeManager.getCurrentMode();
            const availableModels = this.modelManager.getAvailableModels();

            return {
                selectedModel: selectedModel ? {
                    id: selectedModel.id,
                    name: selectedModel.name,
                    vendor: selectedModel.vendor
                } : null,
                currentMode,
                availableModelsCount: availableModels.length,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Failed to get Copilot state:', error);
            return {
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * レスポンスを適切な場所に表示
     */
    public async displayResponse(response: CopilotResponse): Promise<void> {
        if (!response.success || !response.content) {
            vscode.window.showErrorMessage(`Copilot request failed: ${response.error || 'Unknown error'}`);
            return;
        }

        try {
            // アクティブエディタがあるかチェック
            const activeEditor = vscode.window.activeTextEditor;
            
            if (activeEditor) {
                // アクティブエディタに挿入
                const position = activeEditor.selection.active;
                await activeEditor.edit(editBuilder => {
                    editBuilder.insert(position, `\n\n--- Copilot Response (${response.model}, ${response.mode}) ---\n${response.content}\n--- End Response ---\n\n`);
                });
            } else {
                // 新規ドキュメントを作成して表示
                const document = await vscode.workspace.openTextDocument({
                    content: `# Copilot Response\n\n**Model:** ${response.model}\n**Mode:** ${response.mode}\n**Timestamp:** ${response.timestamp.toISOString()}\n\n---\n\n${response.content}`,
                    language: 'markdown'
                });
                await vscode.window.showTextDocument(document);
            }

            vscode.window.showInformationMessage(`Copilot response received from ${response.model} (${response.mode} mode)`);

        } catch (error) {
            console.error('Failed to display response:', error);
            vscode.window.showErrorMessage(`Failed to display response: ${error}`);
        }
    }

    /**
     * サービスの初期化
     */
    public async initialize(): Promise<void> {
        try {
            // 利用可能なモデルを更新
            await this.modelManager.refreshAvailableModels();
            
            // デフォルトモードをAgent Modeに設定
            await this.modeManager.switchMode(CopilotMode.AGENT);
            
            console.log('CopilotService initialized successfully');
        } catch (error) {
            console.error('Failed to initialize CopilotService:', error);
            throw error;
        }
    }
}
