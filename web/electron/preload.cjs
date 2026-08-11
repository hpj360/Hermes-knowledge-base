/**
 * Hermes 知识库 - Electron 预加载脚本
 *
 * 在 contextIsolation 模式下安全地暴露少量 API 给渲染进程。
 * 当前仅暴露 appInfo（版本/平台），不暴露文件系统或子进程能力。
 */
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  isElectron: true,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
});
