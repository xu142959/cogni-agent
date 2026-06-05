const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  getVersion: () => ipcRenderer.invoke('get-version'),
  openSettings: () => ipcRenderer.send('open-settings'),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),
  // Listen for menu events
  onNewChat: (callback) => ipcRenderer.on('new-chat', callback),
  onVoiceInput: (callback) => ipcRenderer.on('voice-input', callback),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
  onClearChat: (callback) => ipcRenderer.on('clear-chat', callback),
});
