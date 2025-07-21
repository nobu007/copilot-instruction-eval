#!/usr/bin/env node

/**
 * Direct Extension Caller
 * VSCode拡張機能を直接呼び出してCopilot実行結果を取得
 */

const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

async function callCopilotExtension(prompt, model = 'copilot/gpt-4', mode = 'agent') {
    try {
        console.log('🚀 Calling Copilot Extension...');
        console.log(`📝 Prompt: ${prompt}`);
        console.log(`🤖 Model: ${model}`);
        console.log(`⚙️ Mode: ${mode}`);
        
        // VSCode拡張機能のコマンドを直接実行
        const result = await vscode.commands.executeCommand(
            'copilotAutomation.executeBatchPrompt', 
            prompt
        );
        
        console.log('✅ Extension call completed');
        console.log('📊 Result:', JSON.stringify(result, null, 2));
        
        return result;
        
    } catch (error) {
        console.error('❌ Extension call failed:', error);
        return {
            success: false,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

// コマンドライン引数から実行
if (require.main === module) {
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.error('Usage: node call_extension.js "prompt text" [model] [mode]');
        process.exit(1);
    }
    
    const prompt = args[0];
    const model = args[1] || 'copilot/gpt-4';
    const mode = args[2] || 'agent';
    
    callCopilotExtension(prompt, model, mode)
        .then(result => {
            console.log('\n🎯 Final Result:');
            console.log(JSON.stringify(result, null, 2));
            process.exit(result.success ? 0 : 1);
        })
        .catch(error => {
            console.error('\n💥 Fatal Error:', error);
            process.exit(1);
        });
}

module.exports = { callCopilotExtension };
