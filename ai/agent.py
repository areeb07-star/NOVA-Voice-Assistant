# agent.py — Nova Local Device Controller (GUI Edition)
# GUI login popup, hidden console, auto-start on Windows
# + Faster polling (0.5s) for snappier response

import os
import sys
import time
import uuid
import json
import socket
import subprocess
import threading
import logging
import requests
import pyautogui
import psutil
from flask import Flask, jsonify
from flask_cors import CORS

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    pass

try:
    import screen_brightness_control as sbc
except ImportError:
    pass

# ============================================================
# LOGGING
# ============================================================
CONFIG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Nova")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "agent.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nova")

def log(msg):
    try:
        print(msg)
    except Exception:
        pass
    try:
        logger.info(msg)
    except Exception:
        pass


# ============================================================
# AUTO-START ON WINDOWS
# ============================================================
def add_to_startup():
    try:
        import winreg
        if not getattr(sys, "frozen", False):
            log(">> Running as .py — skipping auto-start registration")
            return
        exe_path = sys.executable
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "NovaAgent", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        log(">> [OK] Added to Windows startup")
    except Exception as e:
        log(f">> Could not add to startup: {e}")

def remove_from_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "NovaAgent")
        winreg.CloseKey(key)
        log(">> Removed from Windows startup")
    except FileNotFoundError:
        pass
    except Exception as e:
        log(f">> Could not remove from startup: {e}")


# ============================================================
# DEVICE ID
# ============================================================
def generate_device_id():
    hostname = socket.gethostname().replace(" ", "-")[:15]
    mac_short = str(uuid.getnode())[-6:]
    return f"{hostname}-{mac_short}"

DEVICE_ID = generate_device_id()

# ============================================================
# CONFIG
# ============================================================
BACKEND_URL = "https://nova-voice-assistant-6vve.onrender.com"
POLL_INTERVAL = 0.5          # ← was 2, now 0.5 for faster response
KILL_SWITCH = os.path.join(os.path.expanduser("~"), "Desktop", "nova.pause")
REMOVE_STARTUP_FLAG = os.path.join(os.path.expanduser("~"), "Desktop", "nova.remove_startup")
LOCAL_PORT = 5050

USER_HOME = os.path.expanduser("~")
USER_APPDATA = os.path.join(USER_HOME, "AppData", "Local")
USER_ROAMING = os.path.join(USER_HOME, "AppData", "Roaming")

ALLOWED_APPS = {
    "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "code": os.path.join(USER_APPDATA, "Programs", "Microsoft VS Code", "Code.exe"),
    "vscode": os.path.join(USER_APPDATA, "Programs", "Microsoft VS Code", "Code.exe"),
    "calc": "C:\\Windows\\System32\\calc.exe",
    "calculator": "C:\\Windows\\System32\\calc.exe",
    "notepad": "C:\\Windows\\System32\\notepad.exe",
    "explorer": "C:\\Windows\\explorer.exe",
    "cmd": "C:\\Windows\\System32\\cmd.exe",
    "terminal": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
    "paint": "C:\\Windows\\System32\\mspaint.exe",
    "whatsapp": os.path.join(USER_APPDATA, "WhatsApp", "WhatsApp.exe"),
    "spotify": os.path.join(USER_ROAMING, "Spotify", "Spotify.exe"),
    "word": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
    "excel": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
    "powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
    "outlook": "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
    "teams": os.path.join(USER_APPDATA, "Microsoft", "Teams", "current", "Teams.exe"),
    "telegram": os.path.join(USER_ROAMING, "Telegram Desktop", "Telegram.exe"),
    "zoom": os.path.join(USER_ROAMING, "Zoom", "bin", "Zoom.exe"),
    "vlc": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "steam": "C:\\Program Files (x86)\\Steam\\steam.exe",
}

APP_ALIASES = {
    "google chrome": "chrome", "chrome browser": "chrome",
    "ms word": "word", "microsoft word": "word",
    "ms excel": "excel", "microsoft excel": "excel",
    "ms teams": "teams", "microsoft teams": "teams",
    "power point": "powerpoint",
    "vs code": "code", "visual studio code": "code",
    "ms paint": "paint",
    "command prompt": "cmd", "powershell": "terminal",
    "file explorer": "explorer", "files": "explorer",
}

REFUSE_APPS = {
    "laptop", "computer", "pc", "my laptop", "my computer",
    "internet", "screen", "monitor", "keyboard", "mouse",
}

ALLOWED_ACTIONS = {
    "OPEN_APP", "OPEN_FOLDER", "OPEN_URL",
    "CREATE_FOLDER", "FIND_FILE",
    "MUTE", "UNMUTE", "VOLUME_UP", "VOLUME_DOWN", "SET_VOLUME",
    "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SET_BRIGHTNESS",
    "TAKE_SCREENSHOT", "CLOSE_APP"
}

COMMON_FOLDERS = {
    "downloads": "Downloads", "download": "Downloads",
    "desktop": "Desktop",
    "documents": "Documents", "document": "Documents",
    "pictures": "Pictures", "picture": "Pictures",
    "music": "Music",
    "videos": "Videos", "video": "Videos",
    "home": "",
}


# ============================================================
# CONFIG FILE
# ============================================================
def load_config():
    global DEVICE_ID
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
            if cfg.get("device_id"):
                DEVICE_ID = cfg["device_id"]
            return cfg
        except Exception:
            pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log(f">> Could not save config: {e}")

CONFIG = load_config()


# ============================================================
# LOGIN
# ============================================================
def login(email, password):
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/login",
            json={"email": email, "password": password},
            timeout=90
        )
        if r.status_code != 200:
            log(f">> Login failed: {r.status_code}")
            return None, None
        data = r.json()
        if not data.get("success"):
            log(f">> Login failed: {data}")
            return None, None
        return data.get("user_id"), data.get("access_token")
    except Exception as e:
        log(f">> Login error: {e}")
        return None, None


def gui_login():
    """Dark-themed tkinter login window. Returns True if login succeeds."""
    import tkinter as tk

    if CONFIG.get("user_id") and CONFIG.get("access_token"):
        log(f">> Logged in as: {CONFIG.get('user_id')}")
        return True

    result = {"ok": False}

    root = tk.Tk()
    root.title("Nova Agent — Sign In")
    root.geometry("420x460")
    root.configure(bg="#0a0c1a")
    root.resizable(False, False)

    root.update_idletasks()
    w, h = 420, 460
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    try:
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
            ico = os.path.join(base, "nova.ico")
            if os.path.exists(ico):
                root.iconbitmap(ico)
    except Exception:
        pass

    tk.Label(root, text="⚡", font=("Segoe UI Emoji", 36),
             bg="#0a0c1a", fg="#22d3ee").pack(pady=(30, 5))

    tk.Label(root, text="Nova Agent",
             font=("Segoe UI", 18, "bold"),
             bg="#0a0c1a", fg="#f1f5f9").pack()

    tk.Label(root, text="Sign in to enable device control",
             font=("Segoe UI", 10),
             bg="#0a0c1a", fg="#94a3b8").pack(pady=(4, 20))

    tk.Label(root, text="Email", font=("Segoe UI", 9, "bold"),
             bg="#0a0c1a", fg="#cbd5e1", anchor="w").pack(fill="x", padx=50, pady=(0, 4))

    email_var = tk.StringVar()
    email_entry = tk.Entry(root, textvariable=email_var,
                           font=("Segoe UI", 11),
                           bg="#12152d", fg="#f1f5f9",
                           insertbackground="#22d3ee",
                           relief="flat", bd=0)
    email_entry.pack(fill="x", padx=50, ipady=8)

    tk.Label(root, text="Password", font=("Segoe UI", 9, "bold"),
             bg="#0a0c1a", fg="#cbd5e1", anchor="w").pack(fill="x", padx=50, pady=(14, 4))

    password_var = tk.StringVar()
    password_entry = tk.Entry(root, textvariable=password_var, show="•",
                              font=("Segoe UI", 11),
                              bg="#12152d", fg="#f1f5f9",
                              insertbackground="#22d3ee",
                              relief="flat", bd=0)
    password_entry.pack(fill="x", padx=50, ipady=8)

    status_var = tk.StringVar(value="")
    tk.Label(root, textvariable=status_var,
             font=("Segoe UI", 9),
             bg="#0a0c1a", fg="#f87171", wraplength=320).pack(pady=(12, 0))

    def do_login(event=None):
        email = email_var.get().strip()
        password = password_var.get().strip()
        if not email or not password:
            status_var.set("Please enter email and password.")
            return
        status_var.set("Signing in...")
        root.update()

        user_id, token = login(email, password)
        if user_id and token:
            CONFIG["user_id"] = user_id
            CONFIG["access_token"] = token
            CONFIG["email"] = email
            save_config(CONFIG)
            result["ok"] = True
            root.destroy()
        else:
            status_var.set("Login failed. Check your email/password.")

    tk.Button(root, text="Sign In",
              font=("Segoe UI", 11, "bold"),
              bg="#22d3ee", fg="#05060f",
              activebackground="#8b5cf6", activeforeground="#fff",
              relief="flat", bd=0, cursor="hand2",
              command=do_login).pack(fill="x", padx=50, pady=(20, 10), ipady=10)

    tk.Label(root, text="Stored locally at %APPDATA%\\Nova\\config.json",
             font=("Segoe UI", 8),
             bg="#0a0c1a", fg="#475569").pack(pady=(4, 0))

    root.bind("<Return>", do_login)
    email_entry.focus_set()
    root.mainloop()
    return result["ok"]


# ============================================================
# LOCAL SERVER
# ============================================================
local_app = Flask(__name__)
CORS(local_app)

@local_app.route('/device_id', methods=['GET'])
def serve_device_id():
    return jsonify({'device_id': DEVICE_ID, 'hostname': socket.gethostname()})

@local_app.route('/health', methods=['GET'])
def local_health():
    return jsonify({'status': 'ok', 'device_id': DEVICE_ID})

def run_local_server():
    try:
        local_app.run(host='127.0.0.1', port=LOCAL_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log(f">> Local server error: {e}")


# ============================================================
# DYNAMIC APP PATH DETECTION
# ============================================================
def find_app_path(app_name):
    app_name = app_name.lower()
    search_paths = {
        "word": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE",
        ],
        "excel": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        ],
        "powerpoint": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
        ],
        "outlook": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
        ],
        "whatsapp": [
            os.path.join(USER_APPDATA, "WhatsApp", "WhatsApp.exe"),
            os.path.join(USER_APPDATA, "Programs", "WhatsApp", "WhatsApp.exe"),
        ],
        "spotify": [os.path.join(USER_ROAMING, "Spotify", "Spotify.exe")],
        "teams": [
            os.path.join(USER_APPDATA, "Microsoft", "Teams", "current", "Teams.exe"),
        ],
        "vlc": [
            "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
            "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
        ],
    }
    for path in search_paths.get(app_name, []):
        if os.path.exists(path):
            return path
    return None


# ============================================================
# OPEN APP
# ============================================================
def open_app(app_name):
    app_name = app_name.lower().strip()
    if app_name in REFUSE_APPS:
        return False, f"'{app_name}' cannot be opened"
    if app_name in APP_ALIASES:
        app_name = APP_ALIASES[app_name]
    log(f">> open_app: '{app_name}'")

    if app_name == "settings":
        try: os.startfile("ms-settings:"); return True, "Opened Settings"
        except Exception as e: return False, str(e)
    if app_name in ["sound_settings", "mic", "microphone"]:
        try: os.startfile("ms-settings:sound"); return True, "Opened Sound Settings"
        except Exception as e: return False, str(e)
    if app_name in ["display_settings", "display"]:
        try: os.startfile("ms-settings:display"); return True, "Opened Display Settings"
        except Exception as e: return False, str(e)
    if app_name == "bluetooth":
        try: os.startfile("ms-settings:bluetooth"); return True, "Opened Bluetooth"
        except Exception as e: return False, str(e)
    if app_name in ["wifi", "wifi_settings"]:
        try: os.startfile("ms-settings:network-wifi"); return True, "Opened WiFi"
        except Exception as e: return False, str(e)
    if app_name == "notifications":
        try: os.startfile("ms-settings:notifications"); return True, "Opened Notifications"
        except Exception as e: return False, str(e)
    if app_name == "update":
        try: os.startfile("ms-settings:windowsupdate"); return True, "Opened Update"
        except Exception as e: return False, str(e)
    if app_name in ["store", "microsoft store"]:
        try: os.startfile("ms-windows-store:"); return True, "Opened Store"
        except Exception as e: return False, str(e)

    if app_name in ALLOWED_APPS:
        path = ALLOWED_APPS[app_name]
        if os.path.exists(path):
            try:
                os.startfile(path)
                return True, f"Opened {app_name}"
            except Exception as e:
                return False, str(e)

    dynamic = find_app_path(app_name)
    if dynamic:
        try:
            os.startfile(dynamic)
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, str(e)

    try:
        result = subprocess.run(["cmd", "/c", "start", "", app_name],
                                capture_output=True, timeout=5, shell=False)
        if result.returncode == 0:
            return True, f"Opened {app_name}"
        return False, f"App '{app_name}' not found"
    except subprocess.TimeoutExpired:
        return False, f"Timeout opening '{app_name}'"
    except Exception as e:
        return False, str(e)


# ============================================================
# OPEN URL
# ============================================================
def open_url(url, browser=None):
    if not url:
        return False, "No URL provided"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        if browser and browser.lower() == "chrome":
            chrome_path = ALLOWED_APPS.get("chrome")
            if chrome_path and os.path.exists(chrome_path):
                subprocess.Popen([chrome_path, url])
                return True, f"Opened {url} in Chrome"
        os.startfile(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, str(e)


# ============================================================
# OPEN FOLDER
# ============================================================
def open_folder(folder_name):
    if not folder_name:
        folder_name = "downloads"
    folder_name = folder_name.strip()

    lower = folder_name.lower()
    if lower in COMMON_FOLDERS:
        real = COMMON_FOLDERS[lower]
        path = os.path.join(USER_HOME, real) if real else USER_HOME
        if os.path.exists(path):
            try:
                subprocess.Popen(f'explorer "{path}"')
                return True, f"Opened {folder_name}"
            except Exception as e:
                try:
                    os.startfile(path)
                    return True, f"Opened {folder_name}"
                except Exception as e2:
                    return False, str(e2)

    candidates = [
        os.path.join(USER_HOME, folder_name),
        os.path.join(USER_HOME, "Desktop", folder_name),
        os.path.join(USER_HOME, "Downloads", folder_name),
        os.path.join(USER_HOME, "Documents", folder_name),
        os.path.join(USER_HOME, "Pictures", folder_name),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                subprocess.Popen(f'explorer "{path}"')
                return True, f"Opened {folder_name}"
            except Exception as e:
                return False, str(e)

    skip = {"AppData", "node_modules", ".git", "__pycache__", "venv", ".venv"}
    for root, dirs, files in os.walk(USER_HOME):
        dirs[:] = [d for d in dirs if d not in skip]
        for d in dirs:
            if d.lower() == folder_name.lower():
                path = os.path.join(root, d)
                try:
                    subprocess.Popen(f'explorer "{path}"')
                    return True, f"Opened {folder_name}"
                except Exception as e:
                    return False, str(e)
    return False, f"Folder '{folder_name}' not found"


# ============================================================
# CLOSE APP
# ============================================================
def close_app(app_name):
    app_name = app_name.lower().strip()
    if app_name in APP_ALIASES:
        app_name = APP_ALIASES[app_name]
    try:
        killed = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and app_name in proc.info['name'].lower():
                    proc.kill(); killed = True
            except: continue
        return (True, f"Closed {app_name}") if killed else (False, f"{app_name} not running")
    except Exception as e:
        return False, str(e)


# ============================================================
# CREATE FOLDER
# ============================================================
def create_folder(folder_name):
    if not folder_name:
        return False, "No folder name provided"
    path = os.path.join(USER_HOME, "Desktop", folder_name)
    try:
        os.makedirs(path, exist_ok=True)
        return True, f"Created folder '{folder_name}' on Desktop"
    except Exception as e:
        return False, str(e)


# ============================================================
# FIND FILE
# ============================================================
def find_file(search_term, folder=None):
    results = []
    if not search_term:
        return False, "No search term provided"

    if folder:
        folder_key = folder.strip().lower()
        if folder_key in COMMON_FOLDERS:
            real = COMMON_FOLDERS[folder_key]
            base = os.path.join(USER_HOME, real) if real else USER_HOME
        else:
            base = os.path.join(USER_HOME, folder.strip())
    else:
        base = USER_HOME

    if not os.path.exists(base):
        return False, f"Folder '{folder}' not found"

    skip_folders = {"AppData", "node_modules", ".git", "__pycache__", "venv", ".venv"}
    term = search_term.lower()
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in skip_folders]
        for name in files + dirs:
            if term in name.lower():
                results.append(os.path.join(root, name))
                if len(results) >= 5:
                    return True, results
    if not results:
        return True, f"No files or folders found matching '{search_term}'"
    return True, results


# ============================================================
# AUDIO / BRIGHTNESS / SCREENSHOT
# ============================================================
def _vol(): return AudioUtilities.GetSpeakers().EndpointVolume

def mute():
    try: _vol().SetMute(1, None); return True, "Muted"
    except Exception as e: return False, str(e)

def unmute():
    try: _vol().SetMute(0, None); return True, "Unmuted"
    except Exception as e: return False, str(e)

def volume_up():
    try:
        v = _vol(); c = v.GetMasterVolumeLevelScalar()
        new = min(1.0, c + 0.1); v.SetMasterVolumeLevelScalar(new, None)
        return True, f"Volume up to {int(new * 100)}%"
    except Exception as e: return False, str(e)

def volume_down():
    try:
        v = _vol(); c = v.GetMasterVolumeLevelScalar()
        new = max(0.0, c - 0.1); v.SetMasterVolumeLevelScalar(new, None)
        return True, f"Volume down to {int(new * 100)}%"
    except Exception as e: return False, str(e)

def set_volume(value):
    try:
        value = max(0, min(100, int(value)))
        _vol().SetMasterVolumeLevelScalar(value / 100.0, None)
        return True, f"Volume set to {value}%"
    except Exception as e: return False, str(e)

def brightness_up():
    try:
        c = sbc.get_brightness()[0]; new = min(100, c + 10)
        sbc.set_brightness(new); return True, f"Brightness up to {new}%"
    except Exception as e: return False, str(e)

def brightness_down():
    try:
        c = sbc.get_brightness()[0]; new = max(0, c - 10)
        sbc.set_brightness(new); return True, f"Brightness down to {new}%"
    except Exception as e: return False, str(e)

def set_brightness(value):
    try:
        value = max(0, min(100, int(value)))
        sbc.set_brightness(value); return True, f"Brightness set to {value}%"
    except Exception as e: return False, str(e)

def take_screenshot():
    try:
        desktop = os.path.join(USER_HOME, "Desktop")
        filepath = os.path.join(desktop, f"screenshot_{int(time.time())}.png")
        pyautogui.screenshot(filepath)
        return True, f"Screenshot saved to {filepath}"
    except Exception as e: return False, str(e)


# ============================================================
# EXECUTOR
# ============================================================
def execute_action(action, data):
    if action not in ALLOWED_ACTIONS:
        return False, f"Action '{action}' not allowed"
    try:
        if action == "OPEN_APP": return open_app(data.get("app", ""))
        elif action == "OPEN_FOLDER": return open_folder(data.get("folder", "downloads"))
        elif action == "OPEN_URL": return open_url(data.get("url", ""), data.get("browser"))
        elif action == "CREATE_FOLDER": return create_folder(data.get("folder_name", ""))
        elif action == "CLOSE_APP": return close_app(data.get("app", ""))
        elif action == "FIND_FILE":
            return find_file(data.get("search_term", ""), data.get("folder"))
        elif action == "MUTE": return mute()
        elif action == "UNMUTE": return unmute()
        elif action == "VOLUME_UP": return volume_up()
        elif action == "VOLUME_DOWN": return volume_down()
        elif action == "SET_VOLUME": return set_volume(data.get("level", data.get("value", 50)))
        elif action == "BRIGHTNESS_UP": return brightness_up()
        elif action == "BRIGHTNESS_DOWN": return brightness_down()
        elif action == "SET_BRIGHTNESS": return set_brightness(data.get("level", data.get("value", 50)))
        elif action == "TAKE_SCREENSHOT": return take_screenshot()
    except Exception as e:
        return False, str(e)
    return False, "Unknown action"


# ============================================================
# POLL / REPORT
# ============================================================
def parse_response(response):
    if not isinstance(response, dict): return None, {}, None
    if response.get("device_action"):
        da = response["device_action"]
        action = da.get("action") or da.get("type")
        data = da.get("data", {})
        qid = da.get("queue_id")
        if action: return action, data, qid
    if response.get("action"):
        return response["action"], response.get("data", {}), response.get("queue_id")
    return None, {}, None

def poll_backend():
    try:
        payload = {"device_id": DEVICE_ID, "user_id": CONFIG.get("user_id")}
        headers = {"Authorization": f"Bearer {CONFIG.get('access_token', '')}"}
        r = requests.post(f"{BACKEND_URL}/api/agent/poll",
                          json=payload, headers=headers, timeout=90)
        response = r.json()
        log(f">> Poll: {response}")
        action, data, qid = parse_response(response)
        return action, data, qid
    except Exception as e:
        log(f">> Poll error: {e}")
    return None, {}, None

def report_result(action, data, success, message, qid):
    try:
        payload = {
            "device_id": DEVICE_ID, "action": action, "success": success,
            "message": message, "data": data, "user_id": CONFIG.get("user_id"),
        }
        if qid: payload["queue_id"] = qid
        headers = {"Authorization": f"Bearer {CONFIG.get('access_token', '')}"}
        r = requests.post(f"{BACKEND_URL}/api/agent/result", json=payload,
                          headers=headers, timeout=90)
        log(f">> Reported: {r.status_code}")
    except Exception as e:
        log(f">> Report failed: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    if not CONFIG.get("device_id"):
        CONFIG["device_id"] = DEVICE_ID
        save_config(CONFIG)

    if getattr(sys, "frozen", False):
        ok = gui_login()
    else:
        print("=" * 60)
        print("  NOVA AGENT — SIGN IN (console mode)")
        print("=" * 60)
        ok = False
        if CONFIG.get("user_id") and CONFIG.get("access_token"):
            print(f">> Logged in as: {CONFIG.get('user_id')}")
            ok = True
        else:
            email = input("Email: ").strip()
            password = input("Password: ").strip()
            user_id, token = login(email, password)
            if user_id and token:
                CONFIG["user_id"] = user_id
                CONFIG["access_token"] = token
                CONFIG["email"] = email
                save_config(CONFIG)
                print(f">> Login successful. Welcome, {email}")
                ok = True

    if not ok:
        log(">> Login cancelled or failed. Exiting.")
        return

    if not CONFIG.get("startup_added"):
        add_to_startup()
        CONFIG["startup_added"] = True
        save_config(CONFIG)

    threading.Thread(target=run_local_server, daemon=True).start()
    time.sleep(1)

    log("=" * 60)
    log(f">> Nova Local Agent is running")
    log(f">> Device ID: {DEVICE_ID}")
    log(f">> User ID:   {CONFIG.get('user_id')}")
    log("=" * 60)

    while True:
        try:
            if os.path.exists(KILL_SWITCH):
                time.sleep(5); continue

            if os.path.exists(REMOVE_STARTUP_FLAG):
                remove_from_startup()
                try:
                    os.remove(REMOVE_STARTUP_FLAG)
                except Exception:
                    pass
                log(">> Auto-start disabled")
                continue

            action, data, qid = poll_backend()
            if action:
                log(f"\n>> Executing: {action}")
                success, message = execute_action(action, data)
                log(f">> Result: {message}")
                report_result(action, data, success, message, qid)

            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            log("\n>> Agent stopped.")
            break
        except Exception as e:
            log(f">> Loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()