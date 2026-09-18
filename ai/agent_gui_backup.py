# agent.py — Nova Local Device Controller
# Multi-user: asks user to sign in, stores their token, polls with their identity
# Device ID + dynamic app paths + deep folder search
# + Windows auto-start (registers once, runs silently on every reboot)
# + 90s timeouts for Render free tier cold starts

import os
import sys
import time
import uuid
import json
import socket
import subprocess
import threading
import requests
import pyautogui
import psutil
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    print("Missing pycaw. Run: pip install pycaw")
    sys.exit(1)

try:
    import screen_brightness_control as sbc
except ImportError:
    print("Missing screen-brightness-control. Run: pip install screen-brightness-control")
    sys.exit(1)

# ============================================================
# AUTO-START ON WINDOWS
# ============================================================
def add_to_startup():
    """Register agent to auto-start with Windows."""
    try:
        import winreg
        if not getattr(sys, "frozen", False):
            print(">> Running as .py — skipping auto-start registration")
            return
        exe_path = sys.executable
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "NovaAgent", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        print(">> [OK] Added to Windows startup")
    except Exception as e:
        print(f">> Could not add to startup: {e}")

def remove_from_startup():
    """Remove agent from Windows startup."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "NovaAgent")
        winreg.CloseKey(key)
        print(">> Removed from Windows startup")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f">> Could not remove from startup: {e}")

# ============================================================
# DEVICE ID
# ============================================================
def generate_device_id():
    hostname = socket.gethostname().replace(" ", "-")[:15]
    mac_short = str(uuid.getnode())[-6:]
    return f"{hostname}-{mac_short}"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Nova")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEVICE_ID = generate_device_id()

# ============================================================
# CONFIG
# ============================================================
BACKEND_URL = "https://nova-voice-assistant-6vve.onrender.com"
POLL_INTERVAL = 2
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
# CONFIG FILE (device_id + user session + startup flag)
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
        print(f">> Could not save config: {e}")

CONFIG = load_config()

# ============================================================
# LOGIN  (timeout raised to 90s)
# ============================================================
def login(email, password):
    """Call backend /api/login → returns (user_id, token) or (None, None)."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/login",
            json={"email": email, "password": password},
            timeout=90
        )
        if r.status_code != 200:
            print(f">> Login failed: {r.status_code}")
            return None, None
        data = r.json()
        if not data.get("success"):
            print(f">> Login failed: {data}")
            return None, None
        return data.get("user_id"), data.get("access_token")
    except Exception as e:
        print(f">> Login error: {e}")
        return None, None

def ensure_logged_in():
    """Interactive login if no saved session."""
    if CONFIG.get("user_id") and CONFIG.get("access_token"):
        print(f">> Logged in as: {CONFIG.get('user_id')}")
        return True

    print()
    print("=" * 60)
    print("  NOVA AGENT — SIGN IN")
    print("=" * 60)
    print("  Enter your Nova account to enable device control.")
    print()

    while True:
        email = input("Email: ").strip()
        if not email:
            print("Email cannot be empty.")
            continue
        password = input("Password: ").strip()
        if not password:
            print("Password cannot be empty.")
            continue

        user_id, token = login(email, password)
        if user_id and token:
            CONFIG["user_id"] = user_id
            CONFIG["access_token"] = token
            CONFIG["email"] = email
            save_config(CONFIG)
            print(f">> Login successful. Welcome, {email}")
            print(f">> Config saved to: {CONFIG_FILE}")
            return True
        else:
            print(">> Login failed. Please try again.")
            print()


# ============================================================
# LOCAL SERVER (port 5050)
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
    local_app.run(host='127.0.0.1', port=LOCAL_PORT, debug=False, use_reloader=False)


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
            "C:\\Program Files (x86)\\Microsoft Office\\Office16\\WINWORD.EXE",
        ],
        "excel": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\EXCEL.EXE",
        ],
        "powerpoint": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            "C:\\Program Files\\Microsoft Office\\Office16\\POWERPNT.EXE",
        ],
        "outlook": [
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
        ],
        "whatsapp": [
            os.path.join(USER_APPDATA, "WhatsApp", "WhatsApp.exe"),
            os.path.join(USER_APPDATA, "Programs", "WhatsApp", "WhatsApp.exe"),
        ],
        "spotify": [os.path.join(USER_ROAMING, "Spotify", "Spotify.exe")],
        "teams": [
            os.path.join(USER_APPDATA, "Microsoft", "Teams", "current", "Teams.exe"),
            os.path.join(USER_APPDATA, "Microsoft", "Teams", "Update.exe"),
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
    print(f">> open_app: '{app_name}'")

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
        else:
            print(f">> Path missing: {path}, trying dynamic search...")

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
# POLL / REPORT  ← TIMEOUTS 10 → 90
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
        print(f">> Poll: {response}")
        action, data, qid = parse_response(response)
        return action, data, qid
    except Exception as e:
        print(f">> Poll error: {e}")
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
        print(f">> Reported: {r.status_code}")
    except Exception as e:
        print(f">> Report failed: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    # Save device_id on first run
    if not CONFIG.get("device_id"):
        CONFIG["device_id"] = DEVICE_ID
        save_config(CONFIG)

    # Login prompt
    try:
        ensure_logged_in()
    except (KeyboardInterrupt, EOFError):
        print("\n>> Login cancelled. Exiting.")
        return

    # Auto-start on Windows (once)
    if not CONFIG.get("startup_added"):
        add_to_startup()
        CONFIG["startup_added"] = True
        save_config(CONFIG)

    # Start local server (for voice.js to fetch device_id)
    threading.Thread(target=run_local_server, daemon=True).start()
    time.sleep(1)

    print()
    print("=" * 60)
    print(f">> Nova Local Agent is running")
    print(f">> Device ID: {DEVICE_ID}")
    print(f">> User ID:   {CONFIG.get('user_id')}")
    print(f">> Local server: http://127.0.0.1:{LOCAL_PORT}/device_id")
    print("=" * 60)
    print(f">> Kill switch: create '{KILL_SWITCH}' to pause")
    print(f">> Remove auto-start: create '{REMOVE_STARTUP_FLAG}'")
    print(">> Press Ctrl+C to stop\n")

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
                print(">> Auto-start disabled")
                continue

            action, data, qid = poll_backend()
            if action:
                print(f"\n>> Executing: {action}")
                success, message = execute_action(action, data)
                print(f">> Result: {message}")
                report_result(action, data, success, message, qid)

            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n>> Agent stopped.")
            break


if __name__ == "__main__":
    main()