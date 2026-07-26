#!/usr/bin/env python
"""POS - Native Desktop Point of Sale Application.

Starts Django via Waitress in the background.
Opens the frontend inside a polished pywebview desktop window.
No console window is created.
"""

import os
import sys
import socket
import time
import shutil
import threading
import traceback
import ctypes
import urllib.request
import urllib.error
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    WRITABLE_DIR = Path(sys.executable).parent
    # Redirect any stray stdout/stderr to log files
    try:
        _log_dir = WRITABLE_DIR / "deployment" / "logs"
        _log_dir.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(str(_log_dir / "stdout.log"), "a", encoding="utf-8")
        sys.stderr = open(str(_log_dir / "stderr.log"), "a", encoding="utf-8")
    except Exception:
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
else:
    BASE_DIR = Path(__file__).resolve().parent
    WRITABLE_DIR = BASE_DIR

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.lan")
if not getattr(sys, 'frozen', False):
    os.environ.setdefault("DJANGO_READ_DOT_ENV_FILE", "True")
sys.path.append(str(BASE_DIR / "megaone"))

_LOADING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Starting Electric Store...</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;
background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);
color:#fff;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
overflow:hidden;
-webkit-font-smoothing:antialiased
}
.container{text-align:center}
.logo{
width:100px;height:100px;
background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
border-radius:24px;
display:flex;align-items:center;justify-content:center;
margin:0 auto 28px;
font-size:40px;font-weight:700;
box-shadow:0 20px 60px rgba(102,126,234,0.4)
}
h1{font-size:28px;font-weight:600;margin-bottom:8px;letter-spacing:-0.5px}
p{color:rgba(255,255,255,0.55);font-size:14px;margin-bottom:36px}
.spinner{
width:36px;height:36px;
border:3px solid rgba(255,255,255,0.1);
border-top-color:#667eea;
border-radius:50%;
animation:spin .8s linear infinite;
margin:0 auto
}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
<div class="logo">ES</div>
<h1>Electric Store</h1>
<p>Starting server, please wait...</p>
<div class="spinner"></div>
</div>
</body>
</html>"""

_TIMEOUT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Startup Error</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;
background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);
color:#fff;
display:flex;
justify-content:center;
align-items:center;
height:100vh;overflow:hidden
}
.container{text-align:center}
.icon{
width:80px;height:80px;
background:linear-gradient(135deg,#f56565,#ed64a6);
border-radius:50%;
display:flex;align-items:center;justify-content:center;
margin:0 auto 24px;
font-size:40px;
box-shadow:0 20px 60px rgba(245,101,101,0.3)
}
h1{font-size:24px;font-weight:600;margin-bottom:8px}
p{color:rgba(255,255,255,0.55);font-size:14px;margin-bottom:4px}
</style>
</head>
<body>
<div class="container">
<div class="icon">!</div>
<h1>Startup Timeout</h1>
<p>The server did not start within 60 seconds.</p>
<p>Please restart the application.</p>
</div>
</body>
</html>"""


_startup_log_path = None


def startup_log(msg: str) -> None:
    global _startup_log_path
    try:
        if _startup_log_path is None:
            _startup_log_path = WRITABLE_DIR / "deployment" / "logs" / "startup.log"
            _startup_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(_startup_log_path), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass


def log(msg: str) -> None:
    try:
        log_dir = WRITABLE_DIR / "deployment" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        with open(str(log_file), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass


def message_box(title: str, message: str, icon: int = 0x10) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, icon)
    except Exception:
        pass


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


def ensure_env_file() -> None:
    env_path = WRITABLE_DIR / ".env"
    if not env_path.exists():
        template = BASE_DIR / "deployment" / "config" / "lan.env"
        if template.exists():
            shutil.copy2(str(template), str(env_path))
            log(f"Created .env from template: {env_path}")
        else:
            log(f"No .env template found at {template}")
    else:
        log(f".env already exists: {env_path}")


def load_env_file() -> None:
    env_path = WRITABLE_DIR / ".env"
    if env_path.exists():
        with open(str(env_path), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                os.environ.setdefault(key, value)
        log(f"Loaded env vars from: {env_path}")


def setup_logging() -> None:
    log_dir = WRITABLE_DIR / "deployment" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(log_dir / "django.log")
    os.environ.setdefault("DJANGO_LOG_FILE", log_file)


def ensure_required_directories() -> None:
    for d in [
        WRITABLE_DIR / "deployment",
        WRITABLE_DIR / "deployment" / "logs",
        WRITABLE_DIR / "deployment" / "backups",
        WRITABLE_DIR / "media",
        WRITABLE_DIR / "static",
        WRITABLE_DIR / "temp",
        WRITABLE_DIR / "cache",
    ]:
        d.mkdir(parents=True, exist_ok=True)


def ensure_media_exists() -> None:
    src_media = BASE_DIR / "megaone" / "media"
    dst_media = WRITABLE_DIR / "media"
    if not src_media.is_dir():
        log(f"Source media directory not found: {src_media}")
        return
    if src_media == dst_media:
        log(f"Media dir already in place: {dst_media}")
        return
    copied = 0
    skipped = 0
    for src_file in src_media.rglob("*"):
        if src_file.is_file():
            rel = src_file.relative_to(src_media)
            dst_file = dst_media / rel
            if not dst_file.exists():
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(src_file), str(dst_file))
                    copied += 1
                except Exception as e:
                    log(f"Failed to copy {src_file.name}: {e}")
            else:
                skipped += 1
    log(f"Media: {copied} copied, {skipped} already exist -> {dst_media}")


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def is_pos_running(port: int) -> bool:
    try:
        req = urllib.request.Request("http://127.0.0.1:" + str(port) + "/", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return True
    except Exception:
        return False


def check_resources() -> list:
    missing = []
    required_paths = [
        ("Templates directory", BASE_DIR / "megaone" / "templates"),
        ("Static directory", BASE_DIR / "staticfiles"),
        ("Config directory", BASE_DIR / "config"),
        ("Deployment config", BASE_DIR / "deployment" / "config"),
        ("Locale directory", BASE_DIR / "locale"),
        ("Menu app", BASE_DIR / "menu"),
        ("Orders app", BASE_DIR / "orders"),
        ("Users app", BASE_DIR / "megaone" / "users"),
        ("Icon file", BASE_DIR / "icon.ico"),
        ("CSS files", BASE_DIR / "staticfiles" / "vendor" / "css"),
        ("JavaScript files", BASE_DIR / "staticfiles" / "vendor" / "js"),
        ("Images", BASE_DIR / "staticfiles" / "vendor" / "img"),
        ("Fonts", BASE_DIR / "staticfiles" / "vendor" / "fonts"),
        ("Audio files", BASE_DIR / "staticfiles" / "audio"),
        ("Sounds", BASE_DIR / "staticfiles" / "sounds"),
        ("Favicon", BASE_DIR / "staticfiles" / "vendor" / "img" / "favicon.ico"),
        ("Deployment env template", BASE_DIR / "deployment" / "config" / "lan.env"),
        ("Settings config", BASE_DIR / "deployment" / "config" / "settings.ini"),
    ]
    for name, path in required_paths:
        if not path.exists():
            missing.append(name)
    return missing


def write_startup_error(error_msg: str) -> None:
    try:
        log_dir = WRITABLE_DIR / "deployment" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        error_path = log_dir / "startup_error.log"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(str(error_path), "w", encoding="utf-8") as f:
            f.write("POS Startup Error\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Executable: {sys.executable if getattr(sys, 'frozen', False) else __file__}\n")
            f.write(f"Working Directory: {Path.cwd()}\n")
            f.write(f"BASE_DIR: {BASE_DIR}\n")
            f.write(f"WRITABLE_DIR: {WRITABLE_DIR}\n")
            f.write(f"\nTraceback:\n{error_msg}\n")
    except Exception:
        pass


def wait_for_server(host: str, port: int, timeout: int = 60) -> bool:
    for i in range(timeout * 2):
        try:
            req = urllib.request.Request("http://127.0.0.1:" + str(port) + "/")
            with urllib.request.urlopen(req, timeout=2) as resp:
                resp.read(1024)
                return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.5)
    return False


def run_server_thread(server) -> None:
    try:
        startup_log("Waitress server thread started")
        server.run()
    except Exception as e:
        tb = traceback.format_exc()
        startup_log(f"Waitress server thread error: {e}\n{tb}")
        log(f"Fatal server thread error: {e}\n{tb}")


def main() -> None:
    try:
        startup_log("=== POS Application Start ===")
        startup_log(f"Application start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        startup_log(f"Python version: {sys.version}")
        startup_log(f"Frozen: {getattr(sys, 'frozen', False)}")
        startup_log(f"BASE_DIR: {BASE_DIR}")
        startup_log(f"WRITABLE_DIR: {WRITABLE_DIR}")
        startup_log(f"Executable: {sys.executable if getattr(sys, 'frozen', False) else __file__}")

        error_log_path = WRITABLE_DIR / "deployment" / "logs" / "startup_error.log"
        if error_log_path.exists():
            try:
                error_log_path.unlink()
            except Exception:
                pass

        os.chdir(str(WRITABLE_DIR))

        ensure_required_directories()
        ensure_media_exists()
        setup_logging()
        ensure_env_file()
        load_env_file()

        host = os.environ.get("ELECTRICSTORE_HOST", "0.0.0.0")
        port = int(os.environ.get("ELECTRICSTORE_PORT", "8000"))

        startup_log(f"Configured host: {host}, port: {port}")
        startup_log("Server start attempt beginning")

        if is_port_in_use(host, port):
            if is_pos_running(port):
                lan_ip = get_lan_ip()
                log(f"POS is already running on http://127.0.0.1:{port}")
            else:
                msg = (
                    f"Port {port} is already in use by another application.\n\n"
                    f"Please close the other application using port {port}\n"
                    f"and restart POS."
                )
                log(f"Port conflict: {msg}")
                message_box("POS - Port Conflict", msg)
                return
        else:
            missing = check_resources()
            if missing:
                log("WARNING: Missing Resources: " + ", ".join(missing))

        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()
        lan_ip = get_lan_ip()

        startup_log("Running database migrations...")
        try:
            from django.core.management import call_command
            call_command('migrate', interactive=False, verbosity=0)
            startup_log("Database migrations completed")
        except Exception as e:
            tb = traceback.format_exc()
            startup_log(f"Database migration warning (non-fatal): {e}\n{tb}")
            log(f"Migration warning: {e}")

        startup_log("Verifying database connection...")
        try:
            from django.db import connections
            cursor = connections['default'].cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            startup_log("Database connection verified OK")
        except Exception as e:
            tb = traceback.format_exc()
            startup_log(f"Database connection FAILED: {e}\n{tb}")
            log(f"Database connection FAILED: {e}")
            message_box(
                "POS - Database Error",
                f"Could not connect to the MySQL database.\n\n"
                f"Error: {e}\n\n"
                f"Check deployment/logs/startup.log for details.",
            )

        log(f"Starting server on {host}:{port}")
        log(f"Settings: {os.environ['DJANGO_SETTINGS_MODULE']}")
        log(f"Log file: {os.environ['DJANGO_LOG_FILE']}")
        log(f"Working Dir: {WRITABLE_DIR}")

        from waitress import create_server
        startup_log(f"Creating Waitress server on {host}:{port}")
        server = create_server(
            application,
            host=host,
            port=port,
            threads=6,
            channel_timeout=120,
        )
        startup_log("Waitress server created, starting thread")
        server_thread = threading.Thread(target=run_server_thread, args=(server,), name="waitress", daemon=True)
        server_thread.start()
        startup_log("Waitress server thread launched")

        ready = threading.Event()

        def waiter() -> None:
            startup_log("Server readiness check started")
            if wait_for_server(host, port, 60):
                ready.set()
                startup_log("Server is ready")
            else:
                startup_log("Server did not become ready within timeout")

        threading.Thread(target=waiter, daemon=True).start()

        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        window_w, window_h = 1400, 900
        win_x = max(0, (screen_w - window_w) // 2)
        win_y = max(0, (screen_h - window_h) // 2)

        import webview
        startup_log("Creating pywebview window")

        window = webview.create_window(
            title="POS",
            html=_LOADING_HTML,
            width=window_w,
            height=window_h,
            x=win_x,
            y=win_y,
            resizable=True,
            min_size=(1024, 600),
            background_color="#0f0c29",
            shadow=True,
            easy_drag=False,
        )

        def navigate_when_ready() -> None:
            if ready.wait(timeout=65):
                url = "http://127.0.0.1:" + str(port)
                startup_log(f"Server ready, navigating to {url}")
                log(f"Server ready, navigating to {url}")
                window.load_url(url)
                window.set_title(
                    "POS | Local: " + url
                    + " | LAN: http://" + lan_ip + ":" + str(port)
                )
            else:
                startup_log("Server failed to start within timeout")
                log("Server failed to start within timeout")
                window.load_html(_TIMEOUT_HTML)
                window.set_title("POS - Startup Error")

        threading.Thread(target=navigate_when_ready, daemon=True).start()

        startup_log("Starting pywebview GUI loop")
        webview.start(
            icon=str(BASE_DIR / "icon.ico"),
            private_mode=False,
        )
        startup_log("pywebview window closed")

        startup_log("Shutting down server...")
        log("Window closed, shutting down server...")
        server.close()
        server_thread.join(timeout=10)
        startup_log("Server stopped.")
        log("Server stopped.")

    except SystemExit:
        raise
    except Exception:
        tb = traceback.format_exc()
        write_startup_error(tb)
        log(f"Fatal error: {tb}")
        message_box(
            "POS - Startup Error",
            f"POS failed to start.\n\n"
            f"Details have been logged to:\n"
            f"deployment/logs/startup_error.log\n\n"
            f"Error:\n{tb[:500]}",
        )


if __name__ == "__main__":
    main()
    os._exit(0)
