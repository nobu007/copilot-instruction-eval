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
        try {
            // まず利用可能なモデルを取得
            const allModels = await vscode.lm.selectChatModels();
            console.log(`Available Language Models: ${allModels.length}`);
            
            if (allModels.length === 0) {
                console.warn('No language models available. Please ensure GitHub Copilot is enabled.');
                return null;
            }
            
            // 利用可能なモデルをログ出力
            allModels.forEach(model => {
                console.log(`- ${model.name} (${model.vendor}/${model.family}) ID: ${model.id}`);
            });
            
            // 選択されたモデルがある場合、それを使用
            if (this.selectedModel) {
                const targetModel = allModels.find(m => m.id === this.selectedModel!.id);
                if (targetModel) {
                    console.log(`Using selected model: ${targetModel.name}`);
                    return targetModel;
                }
            }
            
            // デフォルトで最初の利用可能なモデルを使用
            const defaultModel = allModels[0];
            console.log(`Using default model: ${defaultModel.name} (${defaultModel.id})`);
            
            // 内部状態も更新
            this.availableModels = allModels.map(model => ({
                id: model.id,
                name: model.name,
                vendor: model.vendor,
                family: model.family,
                version: model.version,
                maxInputTokens: model.maxInputTokens
            }));
            
            this.selectedModel = {
                id: defaultModel.id,
                name: defaultModel.name,
                vendor: defaultModel.vendor,
                family: defaultModel.family,
                version: defaultModel.version,
                maxInputTokens: defaultModel.maxInputTokens
            };
            
            return defaultModel;
            
        } catch (error) {
            console.error('Failed to get chat model:', error);
            console.error('Please check GitHub Copilot authentication and permissions.');
            return null;
        }
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
