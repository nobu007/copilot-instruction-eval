import * as vscode from 'vscode';

export enum CopilotMode {
    CHAT = 'chat',
    AGENT = 'agent'
}

export interface ModeConfig {
    mode: CopilotMode;
    enabled: boolean;
    description: string;
    features: string[];
}

export class ModeManager {
    private static instance: ModeManager;
    private currentMode: CopilotMode = CopilotMode.AGENT;
    private modeConfigs: Map<CopilotMode, ModeConfig> = new Map();

    private constructor() {
        this.initializeModeConfigs();
    }

    public static getInstance(): ModeManager {
        if (!ModeManager.instance) {
            ModeManager.instance = new ModeManager();
        }
        return ModeManager.instance;
    }

    private initializeModeConfigs(): void {
        this.modeConfigs.set(CopilotMode.CHAT, {
            mode: CopilotMode.CHAT,
            enabled: true,
            description: 'Traditional chat-based interaction with Copilot',
            features: [
                'Question & Answer format',
                'Code suggestions',
                'Manual conversation flow',
                'Single response per query'
            ]
        });

        this.modeConfigs.set(CopilotMode.AGENT, {
            mode: CopilotMode.AGENT,
            enabled: true,
            description: 'Autonomous agent mode with multi-step problem solving',
            features: [
                'Autonomous multi-file editing',
                'Tool invocation capabilities',
                'Iterative problem solving',
                'Terminal command execution',
                'Self-directed workflow'
            ]
        });
    }

    /**
     * 現在のモードを取得
     */
    public getCurrentMode(): CopilotMode {
        return this.currentMode;
    }

    /**
     * モードを切り替え
     */
    public async switchMode(mode: CopilotMode): Promise<boolean> {
        try {
            console.log(`⚙️ Switching to ${mode} mode...`);
            
            // Agent Modeの場合は事前に有効化を試行
            if (mode === CopilotMode.AGENT) {
                console.log('🤖 Preparing Agent Mode...');
                await this.enableAgentMode();
                console.log('✅ Agent Mode preparation completed');
            }
            
            // モード切替え実行
            this.currentMode = mode;
            console.log(`✅ Successfully switched to ${mode} mode`);
            
            // モード設定を更新
            const modeConfig = this.modeConfigs.get(mode);
            if (modeConfig) {
                modeConfig.enabled = true;
                console.log(`📊 Mode config updated:`, modeConfig);
            }
            
            // UI通知
            vscode.window.showInformationMessage(
                `✅ Copilot mode switched to: ${mode.toUpperCase()}`
            );
            
            return true;
        } catch (error) {
            console.error(`❌ Failed to switch to ${mode} mode:`, error);
            
            // エラー詳細をログ出力
            if (error instanceof Error) {
                console.error('❌ Error details:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                });
            }
            
            vscode.window.showErrorMessage(`❌ Failed to switch to ${mode} mode: ${error instanceof Error ? error.message : String(error)}`);
            return false;
        }
    }

    /**
     * Agent Modeを有効化
     */
    private async enableAgentMode(): Promise<void> {
        try {
            console.log('🤖 Attempting to enable Agent Mode...');
            
            // 複数の設定キーを試行
            const configs = [
                { section: 'github.copilot.chat', key: 'agent.enabled' },
                { section: 'github.copilot', key: 'chat.agent.enabled' },
                { section: 'github.copilot', key: 'agent.enabled' }
            ];
            
            let enabledCount = 0;
            
            for (const { section, key } of configs) {
                try {
                    const config = vscode.workspace.getConfiguration(section);
                    const currentValue = config.get(key, false);
                    
                    console.log(`🔍 Checking ${section}.${key}: ${currentValue}`);
                    
                    if (!currentValue) {
                        await config.update(key, true, vscode.ConfigurationTarget.Global);
                        console.log(`✅ Enabled ${section}.${key}`);
                        enabledCount++;
                    } else {
                        console.log(`ℹ️ ${section}.${key} already enabled`);
                    }
                } catch (configError) {
                    console.warn(`⚠️ Failed to update ${section}.${key}:`, configError);
                }
            }
            
            console.log(`🎆 Agent Mode configuration completed (${enabledCount} settings updated)`);
            
        } catch (error) {
            console.error('❌ Failed to enable agent mode:', error);
            // Agent Mode有効化に失敗してもモード切替え自体は続行
            console.log('🔄 Continuing with mode switch despite agent enablement failure');
        }
    }

    /**
     * モード設定情報を取得
     */
    public getModeConfig(mode: CopilotMode): ModeConfig | undefined {
        return this.modeConfigs.get(mode);
    }

    /**
     * 全モード情報を取得
     */
    public getAllModes(): ModeConfig[] {
        return Array.from(this.modeConfigs.values());
    }

    /**
     * UI表示用のモード情報を取得
     */
    public getModesForUI(): any[] {
        return this.getAllModes().map(config => ({
            id: config.mode,
            name: config.mode.toUpperCase(),
            description: config.description,
            features: config.features,
            enabled: config.enabled,
            selected: config.mode === this.currentMode
        }));
    }

    /**
     * 現在のモードに応じたプロンプト形式を取得
     */
    public formatPromptForCurrentMode(prompt: string): string {
        switch (this.currentMode) {
            case CopilotMode.AGENT:
                return `@workspace ${prompt}

Please act as an autonomous agent and:
1. Analyze the request thoroughly
2. Break down into actionable steps
3. Execute necessary file edits, tool usage, or commands
4. Provide iterative improvements
5. Ensure complete solution delivery

Use your full agent capabilities including multi-file editing, terminal commands, and autonomous problem-solving.`;

            case CopilotMode.CHAT:
            default:
                return prompt;
        }
    }

    /**
     * モードに応じたCopilot UI開始方法を取得
     */
    public async openCopilotUI(): Promise<boolean> {
        try {
            // 基本的なCopilot Chatを開く（両モード共通）
            await vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
            
            // Agent Modeの場合は追加設定
            if (this.currentMode === CopilotMode.AGENT) {
                console.log('🤖 Opening Copilot in Agent Mode');
                // Agent Mode用の追加処理（将来の拡張用）
                // 現在のVSCodeではAgent Modeは設定で有効化済みであれば自動的に利用可能
            } else {
                console.log('💬 Opening Copilot in Chat Mode');
            }
            
            return true;
        } catch (error) {
            console.error(`Failed to open Copilot UI for ${this.currentMode} mode:`, error);
            
            // フォールバック: 基本的なCopilot Chatコマンドを試行
            try {
                await vscode.commands.executeCommand('github.copilot.chat.open');
                return true;
            } catch (fallbackError) {
                console.error('Fallback command also failed:', fallbackError);
                return false;
            }
        }
    }
}
