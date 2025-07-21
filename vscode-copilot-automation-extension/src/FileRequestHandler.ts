/**
 * File-based Request Handler for Copilot Evaluation
 * 
 * ファイル監視によるリクエスト処理と結果記録システム
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
}

export class FileRequestHandler {
    private watchDir: string;
    private requestsDir: string;
    private responsesDir: string;
    private configDir: string;
    private watcher: fs.FSWatcher | null = null;
    
    constructor(
        private copilotService: CopilotService,
        private modelManager: ModelManager,
        private modeManager: ModeManager,
        baseDir: string = '/tmp/copilot-evaluation'
    ) {
        this.watchDir = baseDir;
        this.requestsDir = path.join(baseDir, 'requests');
        this.responsesDir = path.join(baseDir, 'responses');
        this.configDir = path.join(baseDir, 'config');
        
        this.ensureDirectories();
    }
    
    private ensureDirectories(): void {
        [this.watchDir, this.requestsDir, this.responsesDir, this.configDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`📁 Created directory: ${dir}`);
            }
        });
    }
    
    public start(): void {
        console.log('🔍 Starting file request handler...');
        console.log(`📁 Watching directory: ${this.requestsDir}`);
        
        // Watch for new request files
        this.watcher = fs.watch(this.requestsDir, (eventType, filename) => {
            if (eventType === 'rename' && filename && filename.endsWith('.json')) {
                const filePath = path.join(this.requestsDir, filename);
                
                // Check if file exists (not deleted)
                if (fs.existsSync(filePath)) {
                    console.log(`📥 New request file detected: ${filename}`);
                    this.processRequestFile(filePath);
                }
            }
        });
        
        // Save current configuration
        this.saveCurrentConfig();
        
        console.log('✅ File request handler started');
    }
    
    public stop(): void {
        if (this.watcher) {
            this.watcher.close();
            this.watcher = null;
            console.log('🛑 File request handler stopped');
        }
    }
    
    private async processRequestFile(filePath: string): Promise<void> {
        try {
            console.log(`🚀 Processing request file: ${path.basename(filePath)}`);
            const startTime = Date.now();
            
            // Read request
            const requestData = fs.readFileSync(filePath, 'utf8');
            const request: EvaluationRequest = JSON.parse(requestData);
            
            console.log(`📝 Request ID: ${request.request_id}`);
            console.log(`📝 Test ID: ${request.test_id}`);
            console.log(`📝 Prompt: ${request.prompt.substring(0, 100)}...`);
            console.log(`🤖 Model: ${request.model}`);
            console.log(`⚙️ Mode: ${request.mode}`);
            
            // Set model and mode if specified
            if (request.model) {
                const success = this.modelManager.selectModel(request.model);
                if (!success) {
                    console.warn(`⚠️ Failed to select model: ${request.model}`);
                }
            }
            
            if (request.mode) {
                await this.modeManager.switchMode(request.mode as any);
            }
            
            // Execute Copilot request
            let response: EvaluationResponse;
            
            try {
                const copilotResponse = await this.copilotService.sendPrompt(request.prompt);
                const executionTime = (Date.now() - startTime) / 1000;
                
                // Get current state for verification
                const currentState = await this.copilotService.getCopilotState();
                
                // Extract response text from CopilotResponse
                const responseText = copilotResponse?.content || '';
                
                response = {
                    request_id: request.request_id,
                    timestamp: new Date().toISOString(),
                    success: true,
                    execution_time: executionTime,
                    response: responseText,
                    model_used: currentState.selectedModel?.id || 'unknown',
                    mode_used: currentState.currentMode || 'unknown',
                    response_length: responseText.length,
                    error_message: null
                };
                
                console.log(`✅ Request completed successfully`);
                console.log(`⏱️ Execution time: ${executionTime.toFixed(2)}s`);
                console.log(`📊 Response length: ${response.response_length} chars`);
                
            } catch (error) {
                const executionTime = (Date.now() - startTime) / 1000;
                const errorMessage = error instanceof Error ? error.message : String(error);
                
                response = {
                    request_id: request.request_id,
                    timestamp: new Date().toISOString(),
                    success: false,
                    execution_time: executionTime,
                    response: '',
                    model_used: 'unknown',
                    mode_used: 'unknown',
                    response_length: 0,
                    error_message: errorMessage
                };
                
                console.error(`❌ Request failed: ${errorMessage}`);
            }
            
            // Save response
            const responseFileName = `resp_${request.request_id.replace('req_', '')}.json`;
            const responseFilePath = path.join(this.responsesDir, responseFileName);
            
            fs.writeFileSync(responseFilePath, JSON.stringify(response, null, 2));
            console.log(`💾 Response saved: ${responseFileName}`);
            
            // Delete processed request file
            fs.unlinkSync(filePath);
            console.log(`🗑️ Request file deleted: ${path.basename(filePath)}`);
            
        } catch (error) {
            console.error(`❌ Error processing request file: ${error}`);
            
            // Create error response if possible
            try {
                const filename = path.basename(filePath, '.json');
                const requestId = filename.replace('req_', '');
                
                const errorResponse: EvaluationResponse = {
                    request_id: `req_${requestId}`,
                    timestamp: new Date().toISOString(),
                    success: false,
                    execution_time: 0,
                    response: '',
                    model_used: 'unknown',
                    mode_used: 'unknown',
                    response_length: 0,
                    error_message: error instanceof Error ? error.message : String(error)
                };
                
                const responseFileName = `resp_${requestId}.json`;
                const responseFilePath = path.join(this.responsesDir, responseFileName);
                fs.writeFileSync(responseFilePath, JSON.stringify(errorResponse, null, 2));
                
                // Delete failed request file
                fs.unlinkSync(filePath);
                
            } catch (cleanupError) {
                console.error(`❌ Error during cleanup: ${cleanupError}`);
            }
        }
    }
    
    private async saveCurrentConfig(): Promise<void> {
        try {
            // Get current state
            const state = await this.copilotService.getCopilotState();
            const models = this.modelManager.getAvailableModels();
            const modes = this.modeManager.getModesForUI();
            
            const config = {
                timestamp: new Date().toISOString(),
                extension_version: '0.0.1',
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
                available_modes: modes
            };
            
            const configPath = path.join(this.configDir, 'current_state.json');
            fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
            
            console.log(`💾 Configuration saved: ${configPath}`);
            
        } catch (error) {
            console.error(`❌ Error saving configuration: ${error}`);
        }
    }
    
    public getStatus(): any {
        return {
            active: this.watcher !== null,
            watch_directory: this.requestsDir,
            response_directory: this.responsesDir,
            config_directory: this.configDir
        };
    }
}
