import * as vscode from 'vscode';

export interface ModelInfo {
    id: string;
    name: string;
    vendor: string;
    family: string;
    version?: string;
    maxInputTokens?: number;
}

export class ModelManager {
    private static instance: ModelManager;
    private availableModels: ModelInfo[] = [];
    private selectedModel: ModelInfo | null = null;

    private constructor() {}

    public static getInstance(): ModelManager {
        if (!ModelManager.instance) {
            ModelManager.instance = new ModelManager();
        }
        return ModelManager.instance;
    }

    /**
     * 利用可能なモデルを取得・更新
     */
    public async refreshAvailableModels(): Promise<ModelInfo[]> {
        try {
            const models = await vscode.lm.selectChatModels();
            this.availableModels = models.map(model => ({
                id: model.id,
                name: model.name,
                vendor: model.vendor,
                family: model.family,
                version: model.version,
                maxInputTokens: model.maxInputTokens
            }));
            
            console.log(`Found ${this.availableModels.length} available models:`, this.availableModels);
            return this.availableModels;
        } catch (error) {
            console.error('Failed to refresh available models:', error);
            return [];
        }
    }

    /**
     * 利用可能なモデル一覧を取得
     */
    public getAvailableModels(): ModelInfo[] {
        return this.availableModels;
    }

    /**
     * モデルを選択
     */
    public selectModel(modelId: string): boolean {
        const model = this.availableModels.find(m => m.id === modelId);
        if (model) {
            this.selectedModel = model;
            console.log(`Selected model: ${model.name} (${model.id})`);
            return true;
        }
        return false;
    }

    /**
     * 現在選択されているモデルを取得
     */
    public getSelectedModel(): ModelInfo | null {
        return this.selectedModel;
    }

    /**
     * 選択されたモデルでChatModelを取得
     */
    public async getSelectedChatModel(): Promise<vscode.LanguageModelChat | null> {
        if (!this.selectedModel) {
            // デフォルトでCopilotを選択
            await this.refreshAvailableModels();
            const copilotModel = this.availableModels.find(m => 
                m.vendor.toLowerCase().includes('copilot') || 
                m.name.toLowerCase().includes('copilot')
            );
            if (copilotModel) {
                this.selectModel(copilotModel.id);
            }
        }

        if (this.selectedModel) {
            try {
                const models = await vscode.lm.selectChatModels({ 
                    vendor: this.selectedModel.vendor,
                    family: this.selectedModel.family
                });
                return models.find(m => m.id === this.selectedModel!.id) || models[0] || null;
            } catch (error) {
                console.error('Failed to get selected chat model:', error);
                return null;
            }
        }
        return null;
    }

    /**
     * モデル情報をJSON形式で取得（UI表示用）
     */
    public getModelsForUI(): any[] {
        return this.availableModels.map(model => ({
            id: model.id,
            name: model.name,
            vendor: model.vendor,
            displayName: `${model.name} (${model.vendor})`,
            selected: this.selectedModel?.id === model.id
        }));
    }
}
