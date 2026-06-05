const { app, BrowserWindow, Menu, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let pythonProcess = null;

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
const DEV_URL = process.env.DEV_URL || 'http://localhost:5173';
const BACKEND_PORT = process.env.COGNI_AGENT_PORT || '8099';

function findBackendScript() {
  const candidates = [
    path.join(__dirname, '../../backend_server.py'),
    path.join(process.resourcesPath || '', 'backend_server.py'),
    path.join(app.getAppPath(), 'backend_server.py'),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'CogniAgent',
    icon: path.join(__dirname, '../assets/icon.png'),
    backgroundColor: '#F8F9FA',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL(DEV_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => { mainWindow = null; });
  setupMenu();
}

function setupMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{ label: 'CogniAgent', submenu: [
      { label: '关于 CogniAgent', role: 'about' },
      { type: 'separator' },
      { label: '设置', accelerator: 'Cmd+,', click: () => mainWindow?.webContents.send('open-settings') },
      { type: 'separator' },
      { label: '退出 CogniAgent', accelerator: 'Cmd+Q', role: 'quit' },
    ]}] : []),
    { label: '文件', submenu: [
      { label: '新建对话', accelerator: 'CmdOrCtrl+N', click: () => mainWindow?.webContents.send('new-chat') },
      { label: '语音输入', accelerator: 'CmdOrCtrl+M', click: () => mainWindow?.webContents.send('voice-input') },
      { type: 'separator' },
      { label: '退出', accelerator: isMac ? 'Cmd+Q' : 'Alt+F4', role: 'quit' },
    ]},
    { label: '编辑', submenu: [
      { role: 'undo', label: '撤销' }, { role: 'redo', label: '重做' },
      { type: 'separator' },
      { role: 'cut', label: '剪切' }, { role: 'copy', label: '复制' }, { role: 'paste', label: '粘贴' },
    ]},
    { label: '视图', submenu: [
      { role: 'reload', label: '重新加载' },
      { role: 'toggleDevTools', label: '开发者工具' },
      { type: 'separator' },
      { role: 'zoomIn', label: '放大' }, { role: 'zoomOut', label: '缩小' }, { role: 'resetZoom', label: '重置缩放' },
    ]},
    { label: '帮助', submenu: [
      { label: '关于 CogniAgent', click: () => mainWindow?.webContents.send('open-settings') },
      { type: 'separator' },
      { label: 'GitHub', click: () => shell.openExternal('https://github.com/xu142959/cogni-agent') },
      { label: '反馈问题', click: () => shell.openExternal('https://github.com/xu142959/cogni-agent/issues') },
    ]},
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function startPythonBackend() {
  const scriptPath = findBackendScript();
  if (!scriptPath) {
    console.log('Backend not found - running frontend-only mode.');
    return;
  }

  console.log(`Starting Python backend: ${scriptPath}`);
  pythonProcess = spawn('python3', [scriptPath], {
    env: { ...process.env, COGNI_AGENT_PORT: BACKEND_PORT, PYTHONUNBUFFERED: '1' },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  pythonProcess.stdout.on('data', (d) => process.stdout.write(`[Backend] ${d}`));
  pythonProcess.stderr.on('data', (d) => process.stderr.write(`[Backend] ${d}`));
  pythonProcess.on('close', (code) => { console.log(`Backend exited (${code})`); pythonProcess = null; });
}

ipcMain.handle('get-platform', () => process.platform);
ipcMain.handle('get-version', () => app.getVersion());
ipcMain.handle('get-backend-url', () => `http://127.0.0.1:${BACKEND_PORT}`);

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (pythonProcess) { pythonProcess.kill(); }
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => { if (mainWindow === null) createWindow(); });
