"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
function activate(context) {
    console.log('🧠 BIT RAGE LABOUR Memory Hot Reload extension activated');
    // Track file watchers
    const fileWatchers = new Map();
    const memoryFiles = [
        'unified_memory_doctrine_system.py',
        'continuous_memory_backup.py',
        'memory_integration_hub.py',
        'memory_doctrine_system.py'
    ];
    let reloadInterval;
    let isHotReloadActive = false;
    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'digitalLabourMemory.showMemoryStatus';
    statusBarItem.tooltip = 'BIT RAGE LABOUR Memory System Status';
    updateStatusBar('$(database) Memory: $(check)');
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('digitalLabourMemory.startHotReload', startHotReload), vscode.commands.registerCommand('digitalLabourMemory.stopHotReload', stopHotReload), vscode.commands.registerCommand('digitalLabourMemory.showMemoryStatus', showMemoryStatus), vscode.commands.registerCommand('digitalLabourMemory.forceReload', forceReload));
    // Auto-start if configured
    const config = vscode.workspace.getConfiguration('digitalLabourMemory');
    if (config.get('autoStart', true)) {
        setTimeout(() => startHotReload(), 2000);
    }
    function updateStatusBar(text) {
        statusBarItem.text = text;
        if (isHotReloadActive) {
            statusBarItem.show();
        }
        else {
            statusBarItem.hide();
        }
    }
    async function startHotReload() {
        if (isHotReloadActive) {
            vscode.window.showInformationMessage('Memory Hot Reload already active');
            return;
        }
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }
        console.log('🔥 Starting Memory Hot Reload...');
        isHotReloadActive = true;
        updateStatusBar('$(sync~spin) Memory: Reloading');
        // Setup file watchers for memory files
        for (const fileName of memoryFiles) {
            const filePath = path.join(workspaceFolder.uri.fsPath, fileName);
            if (fs.existsSync(filePath)) {
                const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(workspaceFolder, fileName));
                watcher.onDidChange(() => handleFileChange(fileName));
                watcher.onDidCreate(() => handleFileChange(fileName));
                watcher.onDidDelete(() => handleFileDeletion(fileName));
                fileWatchers.set(fileName, watcher);
                context.subscriptions.push(watcher);
            }
        }
        // Start periodic reload check
        const reloadIntervalMs = config.get('reloadInterval', 2000);
        reloadInterval = setInterval(async () => {
            await checkForChanges();
        }, reloadIntervalMs);
        updateStatusBar('$(flame) Memory: Hot Reload Active');
        showNotification('🔥 Memory Hot Reload Started', 'Hot reloading active for memory systems');
        // Initial memory system check
        await checkMemorySystem();
    }
    function stopHotReload() {
        console.log('🛑 Stopping Memory Hot Reload...');
        isHotReloadActive = false;
        // Clear interval
        if (reloadInterval) {
            clearInterval(reloadInterval);
            reloadInterval = undefined;
        }
        // Dispose watchers
        fileWatchers.forEach(watcher => watcher.dispose());
        fileWatchers.clear();
        updateStatusBar('$(database) Memory: $(x)');
        showNotification('🛑 Memory Hot Reload Stopped', 'Hot reloading deactivated');
    }
    async function handleFileChange(fileName) {
        console.log(`📝 Memory file changed: ${fileName}`);
        updateStatusBar('$(sync~spin) Memory: Reloading');
        try {
            // Reload the memory system
            await reloadMemorySystem(fileName);
            updateStatusBar('$(flame) Memory: Hot Reload Active');
            showNotification('🔄 Memory System Reloaded', `${fileName} updated and reloaded`);
        }
        catch (error) {
            console.error('Reload error:', error);
            updateStatusBar('$(error) Memory: Reload Failed');
            showNotification('❌ Memory Reload Failed', `Error in ${fileName}: ${error}`);
        }
    }
    function handleFileDeletion(fileName) {
        console.log(`🗑️ Memory file deleted: ${fileName}`);
        showNotification('⚠️ Memory File Deleted', `${fileName} was removed`);
    }
    async function checkForChanges() {
        if (!isHotReloadActive)
            return;
        // Check if memory system is still running
        const isRunning = await checkMemorySystemHealth();
        if (!isRunning) {
            updateStatusBar('$(warning) Memory: System Down');
            showNotification('⚠️ Memory System Down', 'Memory system not responding, attempting restart...');
            await restartMemorySystem();
        }
    }
    async function reloadMemorySystem(fileName) {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder)
            return;
        // Execute Python reload command
        const terminal = vscode.window.createTerminal('Memory Reload');
        terminal.show();
        let reloadCommand;
        if (fileName === 'unified_memory_doctrine_system.py') {
            reloadCommand = 'python -c "from unified_memory_doctrine_system import get_unified_memory_system; m = get_unified_memory_system(); m.prevent_blanks(); print(\'✅ Unified memory reloaded\')"';
        }
        else if (fileName === 'continuous_memory_backup.py') {
            reloadCommand = 'python -c "from continuous_memory_backup import get_continuous_backup_system; b = get_continuous_backup_system(); b.force_backup_now(); print(\'✅ Backup system reloaded\')"';
        }
        else if (fileName === 'memory_integration_hub.py') {
            reloadCommand = 'python -c "from memory_integration_hub import sync_all_memory_systems; sync_all_memory_systems(); print(\'✅ Integration hub reloaded\')"';
        }
        else {
            reloadCommand = `python -c "import ${fileName.replace('.py', '')}; print('✅ ${fileName} reloaded')"`;
        }
        terminal.sendText(`cd "${workspaceFolder.uri.fsPath}" && ${reloadCommand}`);
    }
    async function checkMemorySystem() {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder)
            return false;
        return new Promise((resolve) => {
            const terminal = vscode.window.createTerminal('Memory Check');
            const process = terminal.processId;
            terminal.sendText(`cd "${workspaceFolder.uri.fsPath}" && python -c "
try:
    from memory_integration_hub import get_memory_integration_status
    status = get_memory_integration_status()
    print('MEMORY_STATUS:', 'ACTIVE' if all(status.values()) else 'INACTIVE')
except Exception as e:
    print('MEMORY_STATUS: ERROR -', str(e))
"`);
            // Wait a bit for the command to execute
            setTimeout(() => {
                resolve(true); // Assume success for now
            }, 2000);
        });
    }
    async function checkMemorySystemHealth() {
        // Simple health check - in real implementation would ping the system
        return true;
    }
    async function restartMemorySystem() {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder)
            return;
        const terminal = vscode.window.createTerminal('Memory Restart');
        terminal.show();
        const restartCommand = 'python -c "from memory_integration_hub import start_memory_integration; start_memory_integration(); print(\'🚀 Memory system restarted\')"';
        terminal.sendText(`cd "${workspaceFolder.uri.fsPath}" && ${restartCommand}`);
    }
    async function forceReload() {
        if (!isHotReloadActive) {
            vscode.window.showWarningMessage('Hot reload not active. Start it first.');
            return;
        }
        updateStatusBar('$(sync~spin) Memory: Force Reloading');
        try {
            await reloadMemorySystem('unified_memory_doctrine_system.py');
            await reloadMemorySystem('continuous_memory_backup.py');
            await reloadMemorySystem('memory_integration_hub.py');
            updateStatusBar('$(flame) Memory: Hot Reload Active');
            showNotification('🔄 Force Reload Complete', 'All memory systems reloaded');
        }
        catch (error) {
            updateStatusBar('$(error) Memory: Force Reload Failed');
            showNotification('❌ Force Reload Failed', `Error: ${error}`);
        }
    }
    async function showMemoryStatus() {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }
        const terminal = vscode.window.createTerminal('Memory Status');
        terminal.show();
        const statusCommand = `cd "${workspaceFolder.uri.fsPath}" && python -c "
try:
    from memory_integration_hub import get_memory_integration_status
    from continuous_memory_backup import get_backup_status
    
    integration = get_memory_integration_status()
    backup = get_backup_status()
    
    print('🏢 BIT RAGE LABOUR MEMORY STATUS')
    print('=' * 40)
    print(f'🔗 Integration Active: {all(integration.values())}')
    print(f'🛡️ Backup Running: {backup.get(\"running\", False)}')
    print(f'📦 Total Backups: {backup.get(\"total_backups\", 0)}')
    print(f'💾 Disk Usage: {backup.get(\"backup_disk_usage\", \"Unknown\")}')
    
    for k, v in integration.items():
        status_icon = '✅' if v else '❌'
        print(f'{status_icon} {k}: {v}')
        
except Exception as e:
    print('❌ Status check failed:', str(e))
"`;
        terminal.sendText(statusCommand);
    }
    function showNotification(title, message) {
        const config = vscode.workspace.getConfiguration('digitalLabourMemory');
        if (config.get('showNotifications', true)) {
            vscode.window.showInformationMessage(`${title}: ${message}`);
        }
    }
    // Cleanup on deactivation
    context.subscriptions.push({
        dispose: () => {
            stopHotReload();
            statusBarItem.dispose();
        }
    });
}
exports.activate = activate;
function deactivate() {
    console.log('🧠 BIT RAGE LABOUR Memory Hot Reload extension deactivated');
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map