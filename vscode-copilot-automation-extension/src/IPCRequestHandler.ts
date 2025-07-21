/**
 * @file IPCRequestHandler.ts
 * @description Handles file-based Inter-Process Communication (IPC) based on the defined architecture.
 * This class is a strict implementation of the server-side responsibilities:
 * 1. Watch the `requests` directory.
 * 2. Process a request by passing it to a `CommandHandler`.
 * 3. Write the outcome to the `responses` directory.
 * 4. It is STATELESS and does not manage retries, file cleanup, or complex workflows.
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { CommandHandler, Command } from './services/CommandHandler';

interface IPCRequest extends Command {
    request_id: string;
}

export class IPCRequestHandler {
    private requestsDir: string;
    private responsesDir: string;
    private failedDir: string;
    private watcher: fs.FSWatcher | null = null;
    private isProcessing = new Set<string>(); // A simple in-memory lock to prevent double processing

    constructor(
        private commandHandler: CommandHandler,
        baseDir: string = '/tmp/copilot-evaluation'
    ) {
        this.requestsDir = path.join(baseDir, 'requests');
        this.responsesDir = path.join(baseDir, 'responses');
        this.failedDir = path.join(baseDir, 'failed');
        this.ensureDirectories();
    }

    private ensureDirectories(): void {
        [this.requestsDir, this.responsesDir, this.failedDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`[IPC] Created directory: ${dir}`);
            }
        });
    }

    public start(): void {
        if (this.watcher) {
            console.warn('[IPC] Watcher is already running.');
            return;
        }
        console.log(`[IPC] Starting to watch directory: ${this.requestsDir}`);

        this.watcher = fs.watch(this.requestsDir, (eventType, filename) => {
            if (eventType === 'rename' && filename && filename.endsWith('.json')) {
                const filePath = path.join(this.requestsDir, filename);
                
                // A brief delay to ensure the file write is complete.
                setTimeout(() => {
                    if (fs.existsSync(filePath)) {
                        this.handleFile(filePath);
                    }
                }, 200);
            }
        });

        // Process any files that might exist on startup
        this.processExistingFiles();
    }

    public stop(): void {
        if (this.watcher) {
            this.watcher.close();
            this.watcher = null;
            console.log('[IPC] Stopped watching directory.');
        }
    }

    private processExistingFiles(): void {
        fs.readdir(this.requestsDir, (err, files) => {
            if (err) {
                console.error('[IPC] Failed to read existing files:', err);
                return;
            }
            for (const file of files) {
                if (file.endsWith('.json')) {
                    this.handleFile(path.join(this.requestsDir, file));
                }
            }
        });
    }

    private async handleFile(filePath: string): Promise<void> {
        const filename = path.basename(filePath);
        const requestId = path.basename(filename, '.json');
        const responsePath = path.join(this.responsesDir, filename);

        if (this.isProcessing.has(requestId) || fs.existsSync(responsePath)) {
            return;
        }

        this.isProcessing.add(requestId);

        try {
            const fileContent = await fs.promises.readFile(filePath, 'utf8');
            const request: IPCRequest = JSON.parse(fileContent);

            if (request.request_id !== requestId) {
                throw new Error(`Request ID mismatch: file says ${request.request_id}, filename is ${requestId}`);
            }

            const attemptsResults: any[] = [];
            let isSuccess = false;
            const maxAttempts = 2;

            for (let i = 1; i <= maxAttempts; i++) {
                console.log(`[IPC] Attempt ${i}/${maxAttempts} for request ${requestId}`);
                const result = await this.commandHandler.executeCommand(request);
                const attemptLog = {
                    attempt: i,
                    success: result.success,
                    data: result.data ?? null,
                    error: result.error ?? null,
                    timestamp: new Date().toISOString(),
                };
                attemptsResults.push(attemptLog);

                if (result.success) {
                    isSuccess = true;
                    console.log(`[IPC] Request ${requestId} succeeded on attempt ${i}.`);
                    break;
                }

                console.warn(`[IPC] Attempt ${i} for ${requestId} failed: ${result.error}`);
                if (i < maxAttempts) {
                    await new Promise(resolve => setTimeout(resolve, 2000 * i)); // Wait before retry
                }
            }

            const finalResponse = {
                request_id: requestId,
                final_status: isSuccess ? 'success' : 'failed',
                attempts: attemptsResults,
            };

            await fs.promises.writeFile(responsePath, JSON.stringify(finalResponse, null, 2));
            console.log(`[IPC] Wrote final response for ${requestId} with status: ${finalResponse.final_status}`);

            if (!isSuccess) {
                const failedRequestPath = path.join(this.failedDir, filename);
                await fs.promises.copyFile(responsePath, failedRequestPath);
                console.log(`[IPC] Copied failed request ${requestId} to ${this.failedDir}`);
            }

        } catch (error: any) {
            console.error(`[IPC] Critical error processing ${requestId}:`, error);
            const errorResponse = {
                request_id: requestId,
                final_status: 'error',
                error_message: `Extension-side critical error: ${error.message}`,
                attempts: [],
            };
            await fs.promises.writeFile(responsePath, JSON.stringify(errorResponse, null, 2));
        } finally {
            // Always clean up the original request file
            if (fs.existsSync(filePath)) {
                await fs.promises.unlink(filePath);
                console.log(`[IPC] Cleaned up request file: ${filename}`);
            }
            this.isProcessing.delete(requestId);
        }
    }
}
