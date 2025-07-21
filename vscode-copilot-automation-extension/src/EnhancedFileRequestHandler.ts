/**
 * Enhanced File-based Request Handler with Reprocessing & Timestamp Validation
 * 
 * 再処理機能・タイムスタンプ整合性チェック付きファイル監視システム
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { CopilotService } from './services/CopilotService';
import { ModelManager } from './services/ModelManager';
import { ModeManager } from './services/ModeManager';

interface EvaluationRequest {
    request_id: string;
    timestamp: string;
    test_id: string;
    prompt: string;
    model: string;
    mode: string;
    timeout: number;
    expected_elements: string[];
    category: string;
    retry_count?: number;
    max_retries?: number;
}

interface EvaluationResponse {
    request_id: string;
    timestamp: string;
    success: boolean;
    execution_time: number;
    response: string;
    model_used: string;
    mode_used: string;
    response_length: number;
    error_message: string | null;
    retry_count: number;
    request_timestamp: string; // 元リクエストのタイムスタンプ
}

interface ProcessingState {
    request_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'retry';
    start_time: string;
    last_update: string;
    retry_count: number;
    error_message?: string;
}

export class EnhancedFileRequestHandler {
    private watchDir: string;
    private requestsDir: string;
    private responsesDir: string;
    private configDir: string;
    private processingDir: string;
    private failedDir: string;
    private logsDir: string;
    private stateDir: string;
    
    private watcher: fs.FSWatcher | null = null;
    private processingStates: Map<string, ProcessingState> = new Map();
    private cleanupInterval: NodeJS.Timeout | null = null;
    
    constructor(
        private copilotService: CopilotService,
        private modelManager: ModelManager,
        private modeManager: ModeManager,
        baseDir: string = '/tmp/copilot-evaluation',
        private logger?: any
    ) {
        this.watchDir = baseDir;
        this.requestsDir = path.join(baseDir, 'requests');
        this.responsesDir = path.join(baseDir, 'responses');
        this.configDir = path.join(baseDir, 'config');
        this.processingDir = path.join(baseDir, 'processing');
        this.failedDir = path.join(baseDir, 'failed');
        this.logsDir = path.join(baseDir, 'logs');
        this.stateDir = path.join(baseDir, 'state');
        
        this.ensureDirectories();
        this.loadProcessingState();
    }
    
    private log(level: 'info' | 'warn' | 'error' | 'debug', message: string, category: string, requestId?: string) {
        const timestamp = new Date().toISOString();
        const logMessage = `${timestamp} [${level.toUpperCase()}] [${category}] ${message}`;
        
        // 既存のロガーへの出力
        if (this.logger && typeof this.logger.log === 'function') {
            this.logger.log(level, message, category);
        }
        // フォールバック: コンソールログ
        console.log(logMessage);
        
        // ログファイルへの自動ダンプ
        this.dumpLogToFile(logMessage, requestId);
    }
    
    private dumpLogToFile(logMessage: string, requestId?: string): void {
        try {
            let logFile: string;
            if (requestId) {
                // リクエスト固有のログファイル
                logFile = path.join(this.logsDir, `${requestId}.log`);
            } else {
                // システム全体のログファイル
                logFile = path.join(this.logsDir, 'system.log');
            }
            
            // ログファイルに追記
            fs.appendFileSync(logFile, logMessage + '\n');
        } catch (error) {
            console.error('Failed to dump log to file:', error);
        }
    }
    
    private ensureDirectories(): void {
        // メインディレクトリ作成
        [this.requestsDir, this.responsesDir, this.processingDir, this.failedDir, this.configDir, this.logsDir, this.stateDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        });
    }
    
    private loadProcessingState(): void {
        try {
            const stateFile = path.join(this.stateDir, 'processing_state.json');
            if (fs.existsSync(stateFile)) {
                const stateData = fs.readFileSync(stateFile, 'utf8');
                const stateObj = JSON.parse(stateData);
                
                for (const [requestId, state] of Object.entries(stateObj)) {
                    this.processingStates.set(requestId, state as ProcessingState);
                }
                
                console.log(`💾 Loaded ${this.processingStates.size} processing states`);
            }
        } catch (error) {
            console.error('❌ Error loading processing state:', error);
        }
    }
    
    private saveProcessingState(): void {
        try {
            const stateFile = path.join(this.stateDir, 'processing_state.json');
            const stateObj: Record<string, ProcessingState> = {};
            for (const [requestId, state] of this.processingStates.entries()) {
                stateObj[requestId] = state;
            }
            
            fs.writeFileSync(stateFile, JSON.stringify(stateObj, null, 2));
        } catch (error) {
            console.error('❌ Error saving processing state:', error);
        }
    }
    
    public start(): void {
        this.log('info', 'Starting enhanced file request handler...', 'startup');
        this.log('info', `Watching directory: ${this.requestsDir}`, 'startup');
        console.log('🔍 Starting enhanced file request handler...');
        console.log(`📁 Watching directory: ${this.requestsDir}`);
        
        // 未処理リクエストの復旧処理
        this.recoverPendingRequests();
        
        // Watch for new request files
        this.watcher = fs.watch(this.requestsDir, (eventType, filename) => {
            // 総合的なデバッグログを追加
            this.log('debug', `File system event: type=${eventType}, filename=${filename}`, 'watcher');

            if (filename && filename.endsWith('.json')) {
                const filePath = path.join(this.requestsDir, filename);

                // ファイル書き込み完了を待つための短い遅延
                setTimeout(() => {
                    try {
                        if (fs.existsSync(filePath)) {
                            this.log('info', `New request file detected: ${filename}`, 'watcher');
                            
                            // 非同期処理のエラーを確実にキャッチ
                            this.processRequestFile(filePath).catch(error => {
                                this.log('error', `Unhandled error in processRequestFile for ${filename}: ${error}`, 'watcher');
                            });

                        } else {
                            this.log('debug', `File ${filename} disappeared before processing.`, 'watcher');
                        }
                    } catch (err) {
                        this.log('error', `Error in watcher callback for ${filename}: ${err}`, 'watcher');
                    }
                }, 100); // 100msの遅延を追加
            }
        });
        
        // 定期クリーンアップ・状態チェック（設定可能間隔）
        const maintenanceInterval = vscode.workspace.getConfiguration('copilotAutomation').get<number>('maintenanceInterval', 30000);
        this.cleanupInterval = setInterval(() => {
            this.performMaintenance();
        }, maintenanceInterval);
        
        // Save current configuration
        this.saveCurrentConfig();
        
        console.log('✅ Enhanced file request handler started');
    }
    
    public stop(): void {
        if (this.watcher) {
            this.watcher.close();
            this.watcher = null;
        }
        
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }
        
        this.saveProcessingState();
        console.log('🛑 Enhanced file request handler stopped');
    }
    
    /**
     * 失敗したリクエストを再処理
     */
    public async reprocessFailedRequests(): Promise<number> {
        let reprocessedCount = 0;
        
        try {
            // failedディレクトリから失敗したリクエストを取得
            const failedFiles = fs.readdirSync(this.failedDir)
                .filter(file => file.endsWith('.json'))
                .map(file => path.join(this.failedDir, file));
            
            console.log(`🔄 Found ${failedFiles.length} failed requests to reprocess`);
            
            for (const failedFile of failedFiles) {
                try {
                    const requestData = fs.readFileSync(failedFile, 'utf8');
                    const request: EvaluationRequest = JSON.parse(requestData);
                    
                    // リトライカウントをリセット
                    request.retry_count = 0;
                    request.timestamp = new Date().toISOString();
                    
                    // requestsディレクトリに移動して再処理
                    const newRequestFile = path.join(this.requestsDir, `${request.request_id}.json`);
                    fs.writeFileSync(newRequestFile, JSON.stringify(request, null, 2));
                    
                    // 元のfailedファイルを削除
                    fs.unlinkSync(failedFile);
                    
                    console.log(`♻️ Reprocessing: ${request.request_id}`);
                    reprocessedCount++;
                    
                } catch (error) {
                    console.error(`❌ Failed to reprocess ${failedFile}:`, error);
                }
            }
            
            console.log(`✅ Reprocessed ${reprocessedCount} failed requests`);
            return reprocessedCount;
            
        } catch (error) {
            console.error('❌ Error during reprocessing:', error);
            return 0;
        }
    }
    
    /**
     * 特定のリクエストIDを再処理
     */
    public async reprocessRequest(requestId: string): Promise<boolean> {
        try {
            // failedディレクトリから該当ファイルを探す
            const failedFile = path.join(this.failedDir, `${requestId}.json`);
            
            if (!fs.existsSync(failedFile)) {
                console.warn(`⚠️ Failed request not found: ${requestId}`);
                return false;
            }
            
            const requestData = fs.readFileSync(failedFile, 'utf8');
            const request: EvaluationRequest = JSON.parse(requestData);
            
            // リトライカウントをリセット
            request.retry_count = 0;
            request.timestamp = new Date().toISOString();
            
            // requestsディレクトリに移動して再処理
            const newRequestFile = path.join(this.requestsDir, `${requestId}.json`);
            fs.writeFileSync(newRequestFile, JSON.stringify(request, null, 2));
            
            // 元のfailedファイルを削除
            fs.unlinkSync(failedFile);
            
            console.log(`♻️ Reprocessing single request: ${requestId}`);
            return true;
            
        } catch (error) {
            console.error(`❌ Failed to reprocess ${requestId}:`, error);
            return false;
        }
    }
    
    private recoverPendingRequests(): void {
        console.log('🔄 Recovering pending requests...');
        
        // processing ディレクトリの未完了リクエストを復旧
        const processingFiles = fs.readdirSync(this.processingDir).filter(f => f.endsWith('.json'));
        
        for (const filename of processingFiles) {
            const filePath = path.join(this.processingDir, filename);
            console.log(`🔄 Recovering: ${filename}`);
            this.processRequestFile(filePath, true);
        }
        
        // 古い処理中状態をクリーンアップ
        const now = new Date();
        for (const [requestId, state] of this.processingStates.entries()) {
            const lastUpdate = new Date(state.last_update);
            const timeDiff = now.getTime() - lastUpdate.getTime();
            
            // 5分以上更新されていない処理中状態は失敗とみなす
            if (timeDiff > 5 * 60 * 1000 && state.status === 'processing') {
                console.log(`⏰ Marking stale request as failed: ${requestId}`);
                state.status = 'failed';
                state.error_message = 'Processing timeout during recovery';
                this.moveToFailedDirectory(requestId);
            }
        }
        
        console.log(`✅ Recovery completed`);
    }
    
    private async processRequestFile(filePath: string, isRecovery: boolean = false): Promise<void> {
        let requestId = 'unknown';
        try {
            console.log(`🚀 Processing request file: ${path.basename(filePath)}`);
            
            // Read request
            const requestData = fs.readFileSync(filePath, 'utf8');
            const request: EvaluationRequest = JSON.parse(requestData);
            requestId = request.request_id;
            
            this.log('info', `Processing request: ${request.prompt.substring(0, 100)}...`, 'processing', requestId);
            
            // タイムスタンプ整合性チェック
            if (!isRecovery && !this.isRequestValid(request)) {
                this.log('warn', 'Invalid or outdated request', 'validation', requestId);
                this.moveToFailedDirectory(request.request_id, 'Invalid timestamp or outdated request');
                fs.unlinkSync(filePath);
                return;
            }
            
            // 重複処理チェック
            const existingState = this.processingStates.get(request.request_id);
            if (existingState && existingState.status === 'completed') {
                console.log(`⏭️ Request already completed: ${request.request_id}`);
                fs.unlinkSync(filePath);
                return;
            }
            
            // リトライ回数チェック
            const retryCount = request.retry_count || 0;
            const maxRetries = request.max_retries || 3;
            
            if (retryCount >= maxRetries) {
                this.log('warn', `Max retries exceeded (${retryCount}/${maxRetries})`, 'retry', requestId);
                this.moveToFailedDirectory(request.request_id, 'Max retries exceeded');
                fs.unlinkSync(filePath);
                return;
            }
            
            // 処理状態を更新
            const processingState: ProcessingState = {
                request_id: request.request_id,
                status: 'processing',
                start_time: new Date().toISOString(),
                last_update: new Date().toISOString(),
                retry_count: retryCount
            };
            
            this.processingStates.set(request.request_id, processingState);
            this.saveProcessingState();
            
            // リクエストファイルをprocessingディレクトリに移動
            const processingFilePath = path.join(this.processingDir, path.basename(filePath));
            fs.renameSync(filePath, processingFilePath);
            
            console.log(`📝 Request ID: ${request.request_id} (retry: ${retryCount})`);
            console.log(`📝 Test ID: ${request.test_id}`);
            console.log(`🤖 Model: ${request.model}, Mode: ${request.mode}`);
            
            // 実際の処理実行
            this.log('info', `Executing request with model: ${request.model}, mode: ${request.mode}`, 'execution', requestId);
            const response = await this.executeRequest(request, processingState);
            
            // レスポンス保存
            await this.saveResponse(response);
            this.log('info', 'Response saved successfully', 'response', requestId);
            
            // 成功時の処理
            processingState.status = 'completed';
            processingState.last_update = new Date().toISOString();
            this.saveProcessingState();
            
            // 処理済みファイル削除
            fs.unlinkSync(processingFilePath);
            
            this.log('info', 'Request completed successfully', 'completion', requestId);
            
        } catch (error) {
            this.log('error', `Error processing request: ${error}`, 'error', requestId);
            await this.handleProcessingError(filePath, error);
        }
    }
    
    private isRequestValid(request: EvaluationRequest): boolean {
        try {
            const requestTime = new Date(request.timestamp);
            const now = new Date();
            
            // リクエストが未来の時刻でないかチェック
            if (requestTime > now) {
                console.warn(`⚠️ Request timestamp is in the future: ${request.timestamp}`);
                return false;
            }
            
            // リクエストが古すぎないかチェック（24時間以内）
            const timeDiff = now.getTime() - requestTime.getTime();
            const maxAge = 24 * 60 * 60 * 1000; // 24時間
            
            if (timeDiff > maxAge) {
                console.warn(`⚠️ Request is too old: ${request.timestamp}`);
                return false;
            }
            
            // 既存のレスポンスがより新しいかチェック
            const responseFile = path.join(this.responsesDir, `resp_${request.request_id.replace('req_', '')}.json`);
            if (fs.existsSync(responseFile)) {
                const responseData = fs.readFileSync(responseFile, 'utf8');
                const response = JSON.parse(responseData);
                const responseTime = new Date(response.timestamp);
                
                if (responseTime >= requestTime) {
                    console.log(`⏭️ Response is newer than request: ${request.request_id}`);
                    return false;
                }
            }
            
            return true;
            
        } catch (error) {
            console.error(`❌ Error validating request timestamp: ${error}`);
            return false;
        }
    }
    
    private async executeRequest(request: EvaluationRequest, state: ProcessingState): Promise<EvaluationResponse> {
        const startTime = Date.now();
        
        try {
            // Set model and mode if specified
            if (request.model) {
                // まず利用可能なモデルを更新
                await this.modelManager.refreshAvailableModels();
                
                // モデル選択を試行
                const success = this.modelManager.selectModel(request.model);
                if (!success) {
                    // 指定されたモデルが見つからない場合、利用可能なモデルをログ出力
                    const availableModels = this.modelManager.getAvailableModels();
                    console.warn(`⚠️ Requested model "${request.model}" not found.`);
                    console.warn(`Available models: ${availableModels.map(m => m.id).join(', ')}`);
                    
                    // デフォルトモデルを使用するか、エラーとするかの選択
                    // ここでは警告を出しつつ処理を続行（デフォルトモデル使用）
                    console.warn(`Using default model instead of ${request.model}`);
                }
            }
            
            if (request.mode) {
                await this.modeManager.switchMode(request.mode as any);
            }
            
            // 状態更新
            state.last_update = new Date().toISOString();
            this.saveProcessingState();
            
            // Execute Copilot request
            const copilotResponse = await this.copilotService.sendPrompt(request.prompt);
            const executionTime = (Date.now() - startTime) / 1000;
            
            // Get current state for verification
            const currentState = await this.copilotService.getCopilotState();
            
            // Extract response text from CopilotResponse
            const responseText = copilotResponse?.content || '';
            
            return {
                request_id: request.request_id,
                timestamp: new Date().toISOString(),
                success: true,
                execution_time: executionTime,
                response: responseText,
                model_used: currentState.selectedModel?.id || 'unknown',
                mode_used: currentState.currentMode || 'unknown',
                response_length: responseText.length,
                error_message: null,
                retry_count: request.retry_count || 0,
                request_timestamp: request.timestamp
            };
            
        } catch (error) {
            const executionTime = (Date.now() - startTime) / 1000;
            const errorMessage = error instanceof Error ? error.message : String(error);
            
            return {
                request_id: request.request_id,
                timestamp: new Date().toISOString(),
                success: false,
                execution_time: executionTime,
                response: '',
                model_used: 'unknown',
                mode_used: 'unknown',
                response_length: 0,
                error_message: errorMessage,
                retry_count: request.retry_count || 0,
                request_timestamp: request.timestamp
            };
        }
    }
    
    private async saveResponse(response: EvaluationResponse): Promise<void> {
        // Save response (unified filename)
        const baseFileName = response.request_id.replace('req_', '');
        const responseFileName = `${baseFileName}.json`;
        const responseFilePath = path.join(this.responsesDir, responseFileName);
        
        fs.writeFileSync(responseFilePath, JSON.stringify(response, null, 2));
        console.log(`💾 Response saved: ${responseFileName}`);
    }
    
    private async handleProcessingError(filePath: string, error: any): Promise<void> {
        try {
            const requestData = fs.readFileSync(filePath, 'utf8');
            const request: EvaluationRequest = JSON.parse(requestData);
            
            const retryCount = (request.retry_count || 0) + 1;
            const maxRetries = request.max_retries || 3;
            
            if (retryCount < maxRetries) {
                // リトライ処理
                console.log(`🔄 Retrying request: ${request.request_id} (${retryCount}/${maxRetries})`);
                
                request.retry_count = retryCount;
                
                // リトライファイルを作成
                const retryFilePath = path.join(this.requestsDir, `${request.request_id}_retry_${retryCount}.json`);
                fs.writeFileSync(retryFilePath, JSON.stringify(request, null, 2));
                
                // 処理状態更新
                const state = this.processingStates.get(request.request_id);
                if (state) {
                    state.status = 'retry';
                    state.retry_count = retryCount;
                    state.last_update = new Date().toISOString();
                    state.error_message = error instanceof Error ? error.message : String(error);
                }
                
            } else {
                // 最大リトライ回数に達した場合
                console.error(`❌ Max retries reached for: ${request.request_id}`);
                this.moveToFailedDirectory(request.request_id, error instanceof Error ? error.message : String(error));
            }
            
            // 元のファイル削除
            if (fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
            }
            
        } catch (cleanupError) {
            console.error(`❌ Error during error handling: ${cleanupError}`);
        }
    }
    
    private moveToFailedDirectory(requestId: string, errorMessage?: string): void {
        try {
            const processingFile = path.join(this.processingDir, `${requestId}.json`);
            const failedFile = path.join(this.failedDir, `${requestId}_failed_${Date.now()}.json`);
            
            if (fs.existsSync(processingFile)) {
                // エラー情報を追加
                const requestData = fs.readFileSync(processingFile, 'utf8');
                const request = JSON.parse(requestData);
                request.failure_reason = errorMessage;
                request.failed_at = new Date().toISOString();
                
                fs.writeFileSync(failedFile, JSON.stringify(request, null, 2));
                fs.unlinkSync(processingFile);
                
                console.log(`🗂️ Moved to failed directory: ${requestId}`);
            }
            
            // 処理状態更新
            const state = this.processingStates.get(requestId);
            if (state) {
                state.status = 'failed';
                state.error_message = errorMessage;
                state.last_update = new Date().toISOString();
            }
            
        } catch (error) {
            console.error(`❌ Error moving to failed directory: ${error}`);
        }
    }
    
    private performMaintenance(): void {
        // 古い処理状態のクリーンアップ
        const now = new Date();
        let cleanedCount = 0;
        
        for (const [requestId, state] of this.processingStates.entries()) {
            const lastUpdate = new Date(state.last_update);
            const timeDiff = now.getTime() - lastUpdate.getTime();
            
            // 完了済みで1時間以上経過した状態を削除
            if (state.status === 'completed' && timeDiff > 60 * 60 * 1000) {
                this.processingStates.delete(requestId);
                cleanedCount++;
            }
            
            // 処理中で10分以上更新されていない状態をタイムアウト
            if (state.status === 'processing' && timeDiff > 10 * 60 * 1000) {
                console.warn(`⏰ Processing timeout: ${requestId}`);
                this.moveToFailedDirectory(requestId, 'Processing timeout');
                state.status = 'failed';
            }
        }
        
        if (cleanedCount > 0) {
            console.log(`🧹 Cleaned ${cleanedCount} old processing states`);
            this.saveProcessingState();
        }
    }
    
    private async saveCurrentConfig(): Promise<void> {
        try {
            // Get current state
            const state = await this.copilotService.getCopilotState();
            const models = this.modelManager.getAvailableModels();
            const modes = this.modeManager.getModesForUI();
            const states = Array.from(this.processingStates.values());
            
            const config = {
                timestamp: new Date().toISOString(),
                extension_version: '0.0.2',
                copilot_state: {
                    available_models_count: models.length,
                    selected_model: state.selectedModel,
                    current_mode: state.currentMode,
                    agent_mode_enabled: state.agentModeEnabled
                },
                available_models: models.map(m => ({
                    id: m.id,
                    name: m.name,
                    vendor: m.vendor,
                    family: m.family
                })),
                available_modes: modes,
                processing_directory: this.processingDir,
                failed_directory: this.failedDir,
                config_directory: this.configDir,
                features: {
                    reprocessing: true,
                    timestamp_validation: true,
                    retry_mechanism: true,
                    state_recovery: true
                },
                statistics: {
                    total_states: states.length,
                    pending: states.filter(s => s.status === 'pending').length,
                    processing: states.filter(s => s.status === 'processing').length,
                    completed: states.filter(s => s.status === 'completed').length,
                    failed: states.filter(s => s.status === 'failed').length,
                    retry: states.filter(s => s.status === 'retry').length
                }
            };
            
            const configFile = path.join(this.configDir, 'current_config.json');
            fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
            console.log(`💾 Configuration saved: ${configFile}`);
            
        } catch (error) {
            console.error('❌ Error saving configuration:', error);
        }
    }
}
