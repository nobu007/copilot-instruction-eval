/**
 * @file CommandHandler.ts
 * @description Maps IPC commands to specific service calls.
 * This acts as a central dispatcher, decoupling the IPC mechanism from the business logic.
 */

import * as vscode from 'vscode';
import { CopilotService, CopilotResponse } from './CopilotService';
import { ModelManager } from './ModelManager';
import { ModeManager, CopilotMode } from './ModeManager';

export interface Command {
    command: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    params: any;
}

export interface CommandResult {
    success: boolean;
    data?: unknown;
    error?: string;
}

export class CommandHandler {
    constructor(
        private copilotService: CopilotService,
        private modelManager: ModelManager,
        private modeManager: ModeManager
    ) {}

    public async executeCommand(command: Command): Promise<CommandResult> {
        console.log(`Executing command: ${command.command}`, command.params);

        try {
            switch (command.command) {
                case 'ping':
                    return await this.handlePing();
                case 'submitPrompt':
                    return await this.handleSubmitPrompt(command.params);
                case 'setMode':
                    return await this.handleSetMode(command.params);
                case 'getCurrentState':
                    return await this.handleGetCurrentState();
                default:
                    return {
                        success: false,
                        error: `Unknown command: ${command.command}`,
                    };
            }
        } catch (e) {
            const error = e instanceof Error ? e : new Error(String(e));
            console.error(`Error executing command ${command.command}:`, error);
            return {
                success: false,
                error: error.message,
            };
        }
    }

    private async handleSubmitPrompt(params: { prompt: string }): Promise<CommandResult> {
        if (!params.prompt) {
            return { success: false, error: 'Prompt parameter is missing' };
        }
        const response: CopilotResponse = await this.copilotService.sendPrompt(params.prompt);
        return {
            success: response.success,
            data: response,
            error: response.error,
        };
    }

    private async handleSetMode(params: { mode: CopilotMode }): Promise<CommandResult> {
        if (!params.mode || !Object.values(CopilotMode).includes(params.mode)) {
            return { success: false, error: `Invalid mode: ${params.mode}` };
        }
        const success = await this.modeManager.switchMode(params.mode);
        if (success) {
            return { success: true, data: { mode: params.mode } };
        } else {
            return { success: false, error: `Failed to switch to mode ${params.mode}` };
        }
    }

    private async handlePing(): Promise<CommandResult> {
        return {
            success: true,
            data: { message: 'pong' },
        };
    }

    private async handleGetCurrentState(): Promise<CommandResult> {
        const model = this.modelManager.getSelectedModel();
        const mode = this.modeManager.getCurrentMode();
        return {
            success: true,
            data: {
                model: model ? { id: model.id, name: model.name } : null,
                mode: mode,
            },
        };
    }
}
