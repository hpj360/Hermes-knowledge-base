/**
 * Hermes 知识库 - Electron 主进程
 *
 * 职责：
 * 1. 创建 BrowserWindow（1200x800）
 * 2. 开发模式：加载 Vite dev server（localhost:5173）
 *    生产模式：加载 dist/index.html
 * 3. 生产模式：自动启动 Python 后端（uvicorn）子进程
 * 4. 应用退出时清理后端子进程
 */
const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const isDev = !app.isPackaged;
const BACKEND_PORT = process.env.KB_PORT || "8765";
const DEV_SERVER_URL = "http://localhost:5173";

// 沙箱/便携模式：将用户数据目录设为项目内，避免 %AppData% 写入限制
const userDataPath = path.join(__dirname, "..", ".electron-data");
if (!fs.existsSync(userDataPath)) {
  fs.mkdirSync(userDataPath, { recursive: true });
}
app.setPath("userData", userDataPath);

/** @type {import("child_process").ChildProcess | null} */
let backendProcess = null;

/**
 * 启动 Python 后端（仅生产模式）。
 * 开发模式假设后端已手动启动（uvicorn hermes.main:app）。
 */
function startBackend() {
  if (isDev) {
    console.log("[electron] dev mode: backend should be running manually");
    return;
  }

  // 查找后端可执行文件（PyInstaller 打包后）或 Python 模块
  const resourcesPath = process.resourcesPath || __dirname;
  const backendExe = path.join(resourcesPath, "backend", "hermes-server.exe");
  const backendPy = path.join(resourcesPath, "backend", "run.py");

  let cmd, args;
  if (fs.existsSync(backendExe)) {
    cmd = backendExe;
    args = [];
  } else if (fs.existsSync(backendPy)) {
    cmd = "python";
    args = [backendPy];
  } else {
    console.warn("[electron] backend not found, running without backend");
    return;
  }

  console.log(`[electron] starting backend: ${cmd} ${args.join(" ")}`);
  backendProcess = spawn(cmd, args, {
    env: {
      ...process.env,
      KB_PORT: String(BACKEND_PORT),
      KB_HOST: "127.0.0.1",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProcess.stdout?.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });
  backendProcess.stderr?.on("data", (data) => {
    console.error(`[backend] ${data.toString().trim()}`);
  });
  backendProcess.on("exit", (code) => {
    console.log(`[electron] backend exited with code ${code}`);
    backendProcess = null;
  });
}

/** 等待后端就绪（轮询 /api/health）。 */
async function waitForBackend(maxRetries = 30, intervalMs = 1000) {
  const http = require("http");
  for (let i = 0; i < maxRetries; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(
          `http://127.0.0.1:${BACKEND_PORT}/api/health`,
          (res) => {
            res.resume();
            res.statusCode === 200 ? resolve() : reject(new Error(String(res.statusCode)));
          }
        );
        req.on("error", reject);
        req.setTimeout(2000, () => reject(new Error("timeout")));
      });
      console.log("[electron] backend ready");
      return true;
    } catch {
      if (i === maxRetries - 1) {
        console.warn("[electron] backend not ready, loading anyway");
        return false;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
  return false;
}

/** 创建主窗口。 */
async function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "Hermes 知识库",
    backgroundColor: "#1a1a1a",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 外部链接用系统浏览器打开
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http") && !url.startsWith(DEV_SERVER_URL)) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  if (isDev) {
    await win.loadURL(DEV_SERVER_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    // 等待后端就绪再加载
    await waitForBackend();
    await win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

// ---- App 生命周期 ----

app.whenReady().then(async () => {
  startBackend();
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
