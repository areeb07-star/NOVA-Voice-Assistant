# agent.py — Nova Local Device Controller
# Person 4 — Final. No copy/move. Dynamic paths. Searches files AND folders.

import os
import time
import uuid
import socket
import subprocess
import threading
import requests
import pyautogui
import psutil
from flask import Flask, jsonify
from flask_cors import CORS

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    print("Missing pycaw. Run: pip install pycaw")
    exit()

try:
    import screen_brightness_control as sbc
except ImportError:
    print("Missing screen-brightness-control. Run: pip install screen-brightness-control")
    exit()


# ============================================================
# AUTO-GENERATE UNIQUE DEVICE ID
# ============================================================
def generate_device_id():
    hostname = socket.gethostname().replace(" ", "-")[:15]
    mac_short = str(uuid.getnode())[-6:]
    return f"{hostname}-{mac_short}"

DEVICE_ID = generate_device_id()

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".nova_device_id")
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        DEVICE_ID = f.read().strip()


# ============================================================
# CONFIGURATION
# ============================================================
BACKEND_URL = "https://nova-voice-assistant-6vve.onrender.com"
POLL_INTERVAL = 2
KILL_SWITCH = os.path.join(os.path.expanduser("~"), "Desktop", "nova.pause")
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
# LOCAL SERVER (port 5050)
# ============================================================
local_app = Flask(__name__)
CORS(local_app)

@local_app.route('/device_id', methods=['GET'])
def serve_device_id():
    return jsonify({
        'device_id': DEVICE_ID,
        'hostname': socket.gethostname()
    })

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
        "spotify": [
            os.path.join(USER_ROAMING, "Spotify", "Spotify.exe"),
        ],
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
            print(f">> Found {app_name} at: {path}")
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

    # Windows Settings URIs
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

    # Try known ALLOWED_APPS path
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

    # Try dynamic detection
    dynamic = find_app_path(app_name)
    if dynamic:
        try:
            os.startfile(dynamic)
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, str(e)

    # Fallback to Windows start
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
    print(f">> open_url: '{url}' (browser: {browser})")
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
# OPEN FOLDER (with explorer + startfile fallback)
# ============================================================
def open_folder(folder_name):
    if not folder_name:
        folder_name = "downloads"

    folder_name = folder_name.strip()
    print(f">> open_folder: '{folder_name}'")

    lower = folder_name.lower()
    if lower in COMMON_FOLDERS:
        real = COMMON_FOLDERS[lower]
        path = os.path.join(USER_HOME, real) if real else USER_HOME
        if os.path.exists(path):
            try:
                subprocess.Popen(f'explorer "{path}"')
                return True, f"Opened {folder_name}"
            except Exception as e:
                print(f"explorer failed: {e}, trying startfile")
                try:
                    os.startfile(path)
                    return True, f"Opened {folder_name} via startfile"
                except Exception as e2:
                    return False, f"Could not open: {e2}"

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
                return True, f"Opened {folder_name} at {path}"
            except Exception as e:
                return False, str(e)

    print(f">> Searching for folder '{folder_name}' in home...")
    skip = {"AppData", "node_modules", ".git", "__pycache__", "venv", ".venv",
            "System Volume Information", "$Recycle.Bin"}
    for root, dirs, files in os.walk(USER_HOME):
        dirs[:] = [d for d in dirs if d not in skip]
        for d in dirs:
            if d.lower() == folder_name.lower():
                path = os.path.join(root, d)
                try:
                    subprocess.Popen(f'explorer "{path}"')
                    return True, f"Found and opened {folder_name}"
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
                    proc.kill()
                    killed = True
            except:
                continue
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
# FIND FILE (files AND folders)
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

    print(f">> find_file: search='{search_term}' in base='{base}'")

    skip_folders = {"AppData", "node_modules", ".git", "__pycache__",
                    "venv", ".venv", "System Volume Information", "$Recycle.Bin"}

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
def _get_volume_interface():
    return AudioUtilities.GetSpeakers().EndpointVolume

def mute():
    try: _get_volume_interface().SetMute(1, None); return True, "Muted"
    except Exception as e: return False, str(e)

def unmute():
    try: _get_volume_interface().SetMute(0, None); return True, "Unmuted"
    except Exception as e: return False, str(e)

def volume_up():
    try:
        vol = _get_volume_interface(); c = vol.GetMasterVolumeLevelScalar()
        new = min(1.0, c + 0.1); vol.SetMasterVolumeLevelScalar(new, None)
        return True, f"Volume up to {int(new * 100)}%"
    except Exception as e: return False, str(e)

def volume_down():
    try:
        vol = _get_volume_interface(); c = vol.GetMasterVolumeLevelScalar()
        new = max(0.0, c - 0.1); vol.SetMasterVolumeLevelScalar(new, None)
        return True, f"Volume down to {int(new * 100)}%"
    except Exception as e: return False, str(e)

def set_volume(value):
    try:
        value = max(0, min(100, int(value)))
        _get_volume_interface().SetMasterVolumeLevelScalar(value / 100.0, None)
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
    print(f">> execute_action: {action} | data: {data}")
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
        elif action == "SET_VOLUME": return set_volume(data.get("value", 50))
        elif action == "BRIGHTNESS_UP": return brightness_up()
        elif action == "BRIGHTNESS_DOWN": return brightness_down()
        elif action == "SET_BRIGHTNESS": return set_brightness(data.get("value", 50))
        elif action == "TAKE_SCREENSHOT": return take_screenshot()
    except Exception as e:
        return False, str(e)
    return False, "Unknown action"


# ============================================================
# PARSING / POLLING / REPORTING
# ============================================================
def parse_response(response):
    if not isinstance(response, dict):
        return None, {}, None
    if response.get("device_action"):
        da = response["device_action"]
        action = da.get("action") or da.get("type")
        data = da.get("data", {})
        qid = da.get("queue_id")
        if action:
            return action, data, qid
    if response.get("action"):
        return response["action"], response.get("data", {}), response.get("queue_id")
    return None, {}, None

def poll_backend():
    try:
        r = requests.post(f"{BACKEND_URL}/api/agent/poll",
                          json={"device_id": DEVICE_ID}, timeout=10)
        response = r.json()
        print(f">> Poll [{DEVICE_ID}]: {response}")
        action, data, qid = parse_response(response)
        return action, data, qid
    except requests.exceptions.RequestException as e:
        print(f">> Poll error: {e}")
    except Exception as e:
        print(f">> Unexpected error: {e}")
    return None, {}, None

def report_result(action, data, success, message, qid):
    try:
        payload = {
            "device_id": DEVICE_ID, "action": action, "success": success,
            "message": message, "data": data, "user_id": data.get("user_id"),
        }
        if qid:
            payload["queue_id"] = qid
        r = requests.post(f"{BACKEND_URL}/api/agent/result", json=payload, timeout=10)
        print(f">> Reported: {r.status_code}")
    except Exception as e:
        print(f">> Report failed: {e}")


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            f.write(DEVICE_ID)

    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()
    time.sleep(1)

    print("=" * 60)
    print(f">> Nova Local Agent is running")
    print(f">> Device ID: {DEVICE_ID}")
    print(f">> Local server: http://127.0.0.1:{LOCAL_PORT}/device_id")
    print("=" * 60)
    print(f">> Kill switch: create '{KILL_SWITCH}' to pause")
    print(">> Press Ctrl+C to stop\n")

    while True:
        if os.path.exists(KILL_SWITCH):
            print(">> Kill switch active. Pausing...")
            time.sleep(5)
            continue

        action, data, qid = poll_backend()
        if action:
            print(f"\n>> Executing: {action}")
            success, message = execute_action(action, data)
            print(f">> Result: {message}")
            report_result(action, data, success, message, qid)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()