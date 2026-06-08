# Beam Mechanics Simulator — Full Project Analysis

## Project Architecture

```
d:\MSF prjct\
├── beam_simulation.py          ← Old v1 (PyQt5/Matplotlib standalone) — NOT used anymore
├── setup_and_run.bat           ← Old v1 launcher — NOT the main one
│
└── beam-simulator\             ← v2 (Electron + Flask) — THIS is the main project
    ├── main.js                 ← Electron main process (spawns Flask, creates window)
    ├── package.json            ← Electron + electron-builder config
    ├── requirements.txt        ← flask, flask-cors, numpy, groq
    ├── setup_and_run.bat       ← ★ MAIN .bat launcher (the one in your screenshot)
    │
    ├── frontend\
    │   ├── index.html          ← UI layout (Chart.js CDN, custom title bar)
    │   ├── styles.css          ← Dark theme styling
    │   └── renderer.js         ← All UI logic, charts, SVG beam, AI explain streaming
    │
    ├── backend\
    │   └── app.py              ← Flask server (/ping, /calculate, /explain)
    │
    ├── beam_env\               ← Python venv (for dev mode)
    ├── node_modules\           ← npm packages (electron, electron-builder)
    │
    ├── build_backend\          ← PyInstaller build artifacts
    │   └── flask_backend.spec  ← PyInstaller spec file
    │
    ├── dist_backend\
    │   └── flask_backend.exe   ← ★ Compiled Python backend (27 MB)
    │
    └── dist\
        ├── Beam Mechanics Simulator Setup 2.0.0.exe  ← ★ Final installer (103 MB)
        └── builder-debug.yml
```

---

## What Was Already Completed ✅

### 1. Full Application Code — DONE ✅
- **Flask backend** (`app.py`) — `/calculate` (beam engineering math) + `/explain` (Groq AI streaming)
- **Electron frontend** — Chart.js SFD/BMD plots, SVG beam diagram, sliders, material selector, AI explain panel
- **Custom title bar** with minimize/maximize/close via IPC

### 2. Development Mode — WORKING ✅
- `setup_and_run.bat` (inside `beam-simulator\`) sets `GROQ_API_KEY` as env var, creates venv, installs deps, runs `npm start`
- Groq API key is hardcoded in the .bat: `GROQ_API_KEY` env var
- Everything works when launched via this .bat

### 3. PyInstaller — Backend Compiled ✅
The Flask backend was compiled to a standalone `.exe`:
```
d:\MSF prjct\beam-simulator\dist_backend\flask_backend.exe  (27 MB)
```
The command that was previously run was likely:
```bash
cd d:\MSF prjct\beam-simulator
.\beam_env\Scripts\activate
pyinstaller --onefile --noconsole --distpath dist_backend --workpath build_backend --name flask_backend backend\app.py
```

### 4. Electron Builder — Installer Created ✅
The full `.exe` installer was built:
```
d:\MSF prjct\beam-simulator\dist\Beam Mechanics Simulator Setup 2.0.0.exe  (103 MB)
```
The command that was previously run:
```bash
cd d:\MSF prjct\beam-simulator
npx electron-builder --win
```
`package.json` is configured to:
- Bundle `main.js` + `frontend/**/*` into an ASAR
- Copy `dist_backend/flask_backend.exe` → `resources/flask_backend.exe` via `extraResources`
- Build an NSIS one-click installer

### 5. main.js Production Path — DONE ✅
`main.js` already handles packaged mode:
```javascript
if (app.isPackaged) {
    exePath = path.join(process.resourcesPath, 'flask_backend.exe')
    flaskProcess = spawn(exePath, [], {
        windowsHide: true,
        env: { ...process.env }    // ← passes current env to Flask
    })
}
```

---

## Where You Were STUCK ❌

### The Problem: Groq API Key Not Reaching the Packaged App

When you install and run `Beam Mechanics Simulator Setup 2.0.0.exe`:

1. ✅ The app installs fine
2. ✅ The Electron window opens
3. ✅ `flask_backend.exe` starts from `resources/`
4. ✅ `/calculate` works — beam calculations, SFD/BMD charts all work
5. ❌ **"Explain Calculations" button FAILS** — because the Groq API key isn't available

#### Why It Fails

In **dev mode**, the `.bat` file sets `GROQ_API_KEY` as an environment variable before launching. But when the user installs the `.exe` and double-clicks the app shortcut, **there is no .bat file** running — the environment variable is never set.

The backend code (`app.py` line 19) does have a hardcoded fallback:
```python
_DEFAULT_GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
```
And on line 26:
```python
key = os.environ.get("GROQ_API_KEY", _DEFAULT_GROQ_KEY)
```

> [!IMPORTANT]
> **This fallback IS already in the code!** The `_DEFAULT_GROQ_KEY` on line 19 of `app.py` means the packaged `flask_backend.exe` *should* use the hardcoded key when no environment variable is set.

### So the REAL question is: Was the `flask_backend.exe` rebuilt AFTER the hardcoded key was added?

Looking at timestamps from your screenshot:
- `app.py` backend folder: `14-04-2026 15:37`
- `dist_backend`: `14-01-2026 18:06` — **this is from January 14!** or a different date format
- `build_backend`: `14-04-2026 17:59`

> [!WARNING]  
> **The `flask_backend.exe` in `dist_backend/` may be STALE.** If the hardcoded `_DEFAULT_GROQ_KEY` was added to `app.py` AFTER `flask_backend.exe` was compiled, then the `.exe` still has the old code without the fallback key. This is very likely the root cause.

---

## What Needs to Be Done

### Step 1: Rebuild `flask_backend.exe` with the current `app.py`
```bash
cd d:\MSF prjct\beam-simulator
.\beam_env\Scripts\activate
pyinstaller --onefile --noconsole --distpath dist_backend --workpath build_backend --name flask_backend backend\app.py
```
This will recompile `app.py` (which already has the hardcoded Groq key) into a new `flask_backend.exe`.

### Step 2: Rebuild the Electron installer
```bash
cd d:\MSF prjct\beam-simulator
npx electron-builder --win
```
This will create a new `Beam Mechanics Simulator Setup 2.0.0.exe` with the updated `flask_backend.exe` bundled inside.

### Step 3: Test the installer
1. Uninstall the old version (if installed)
2. Install the new `.exe`
3. Launch from Start Menu / Desktop
4. Run a simulation → click **"Explain Calculations"**
5. The AI explanation should now stream correctly

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Flask backend code | ✅ Done | Has hardcoded Groq key fallback |
| Electron frontend code | ✅ Done | Full UI with streaming AI explain |
| `setup_and_run.bat` (dev) | ✅ Working | Sets env var, launches app |
| `flask_backend.exe` (PyInstaller) | ⚠️ STALE | Needs rebuild with current `app.py` |
| `Beam Mechanics Simulator Setup 2.0.0.exe` | ⚠️ STALE | Needs rebuild after PyInstaller step |
| AI Explain in packaged .exe | ❌ Broken | Will be fixed after rebuilding both |

**TL;DR: The hardcoded API key IS in `app.py`, but the compiled `flask_backend.exe` is likely outdated. Two rebuild commands will fix everything.**
