const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

let mainWindow
let flaskProcess

function startFlask() {
    let exePath

    if (app.isPackaged) {
        // Production: use bundled flask_backend.exe from resources
        exePath = path.join(process.resourcesPath, 'flask_backend.exe')
        flaskProcess = spawn(exePath, [], {
            windowsHide: true,
            env: { ...process.env }
        })
    } else {
        // Development: use Python venv
        const pythonPath = path.join(__dirname, 'beam_env', 'Scripts', 'python.exe')
        const scriptPath = path.join(__dirname, 'backend', 'app.py')
        flaskProcess = spawn(pythonPath, [scriptPath], {
            windowsHide: true,
            env: { ...process.env }
        })
    }

    flaskProcess.stdout.on('data', (d) => {
        console.log('Flask:', d.toString().trim())
    })
    flaskProcess.stderr.on('data', (d) => {
        console.log('Flask:', d.toString().trim())
    })
    flaskProcess.on('error', (err) => {
        console.error('Failed to start Flask:', err)
    })
}

function waitForFlask(callback, attempts) {
    attempts = attempts || 0
    if (attempts > 30) {
        console.error('Flask server did not start within 15 seconds')
        callback()
        return
    }
    http.get('http://127.0.0.1:5000/ping', (res) => {
        callback()
    }).on('error', () => {
        setTimeout(() => waitForFlask(callback, attempts + 1), 500)
    })
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        frame: false,
        titleBarStyle: 'hidden',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        },
        backgroundColor: '#0a0a0a',
        show: false
    })

    mainWindow.loadFile('frontend/index.html')

    mainWindow.once('ready-to-show', () => {
        mainWindow.show()
        mainWindow.focus()
        mainWindow.setAlwaysOnTop(true)
        setTimeout(() => {
            mainWindow.setAlwaysOnTop(false)
        }, 1000)
    })

    mainWindow.on('closed', () => {
        mainWindow = null
    })
}

// IPC handlers for custom window controls
ipcMain.on('win-minimize', () => {
    if (mainWindow) mainWindow.minimize()
})
ipcMain.on('zoom-in', () => {
    if (mainWindow) {
        const wc = mainWindow.webContents
        const z = wc.getZoomFactor()
        wc.setZoomFactor(Math.min(z + 0.1, 2.0))
    }
})
ipcMain.on('zoom-out', () => {
    if (mainWindow) {
        const wc = mainWindow.webContents
        const z = wc.getZoomFactor()
        wc.setZoomFactor(Math.max(z - 0.1, 0.5))
    }
})
ipcMain.on('zoom-reset', () => {
    if (mainWindow) mainWindow.webContents.setZoomFactor(1.0)
})
ipcMain.on('win-maximize', () => {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize()
        } else {
            mainWindow.maximize()
        }
    }
})
ipcMain.on('win-close', () => {
    if (mainWindow) mainWindow.close()
})

app.whenReady().then(() => {
    startFlask()
    waitForFlask(() => createWindow())
})

app.on('window-all-closed', () => {
    if (flaskProcess) {
        flaskProcess.kill()
    }
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('before-quit', () => {
    if (flaskProcess) {
        flaskProcess.kill()
    }
})
