#!/bin/bash
"""
Support Information Collector - VSCode Copilot Automation System
トラブルシューティング用のシステム情報収集スクリプト

Usage:
    ./scripts/collect_support_info.sh > support_info.txt
"""

echo "=== VSCode Copilot Automation System - Support Information ==="
echo "Generated: $(date)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo ""

echo "=== System Information ==="
echo "OS: $(uname -a)"
echo "Python Version: $(python3 --version 2>&1)"
echo "Node Version: $(node --version 2>&1 || echo 'Node.js not found')"
echo "VSCode Version: $(code --version 2>&1 | head -1 || echo 'VSCode not found')"
echo ""

echo "=== Process Information ==="
echo "VSCode Processes:"
ps aux | grep -E "(code|extensionHost)" | grep -v grep || echo "No VSCode processes found"
echo ""

echo "=== Extension Information ==="
echo "Installed Extensions:"
code --list-extensions 2>&1 | grep -E "(copilot|automation)" || echo "No relevant extensions found"
echo ""

echo "=== Directory Structure ==="
echo "IPC Directories:"
ls -la /tmp/copilot-evaluation/ 2>/dev/null || echo "/tmp/copilot-evaluation not found"
echo ""

echo "Recent Requests (last 5):"
ls -lt /tmp/copilot-evaluation/requests/ 2>/dev/null | head -6 || echo "No requests directory"
echo ""

echo "Recent Responses (last 5):"  
ls -lt /tmp/copilot-evaluation/responses/ 2>/dev/null | head -6 || echo "No responses directory"
echo ""

echo "Recent Failed Requests (last 5):"
ls -lt /tmp/copilot-evaluation/failed/ 2>/dev/null | head -6 || echo "No failed directory"
echo ""

echo "=== Project Files ==="
echo "Project Directory:"
ls -la . | grep -E "\.(py|json|md|sh)$"
echo ""

echo "Extension Directory:"
ls -la vscode-copilot-automation-extension/ 2>/dev/null || echo "Extension directory not found"
echo ""

echo "=== Database Information ==="
for db in *.db; do
    if [ -f "$db" ]; then
        echo "Database: $db"
        echo "Size: $(ls -lh "$db" | awk '{print $5}')"
        echo "Tables: $(sqlite3 "$db" ".tables" 2>/dev/null || echo 'Cannot read database')"
        echo "Recent records:"
        sqlite3 "$db" "SELECT COUNT(*) as total_records FROM execution_results;" 2>/dev/null || echo "No execution_results table"
        echo ""
    fi
done

echo "=== Network Connectivity ==="
echo "Localhost connectivity:"
curl -s --max-time 5 http://localhost:8080 >/dev/null && echo "Port 8080: Available" || echo "Port 8080: Not available"
echo ""

echo "=== Resource Usage ==="
echo "Disk Usage:"
df -h /tmp 2>/dev/null || echo "Cannot check /tmp disk usage"
echo ""

echo "Memory Usage:"
free -h 2>/dev/null || echo "Cannot check memory usage"
echo ""

echo "=== Recent Logs ==="
if [ -f "/tmp/copilot-evaluation/logs/system.log" ]; then
    echo "Last 10 lines from system log:"
    tail -10 /tmp/copilot-evaluation/logs/system.log
else
    echo "No system log found"
fi
echo ""

echo "=== Configuration Files ==="
echo "Instructions files:"
ls -la *.json 2>/dev/null | grep -E "(instruction|test)" || echo "No instruction files found"
echo ""

echo "Package.json (if exists):"
[ -f "package.json" ] && cat package.json | head -20 || echo "No package.json found"
echo ""

echo "=== Health Check Result ==="
echo "Running quick health check..."
if [ -f "scripts/health_check.py" ]; then
    python3 scripts/health_check.py 2>&1 | tail -10
else
    echo "Health check script not found"
fi
echo ""

echo "=== End of Support Information ==="
echo "Generated: $(date)"