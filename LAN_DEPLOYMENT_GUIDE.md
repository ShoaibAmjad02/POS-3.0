# POS - LAN Deployment Guide

## Architecture

```
[ SERVER MACHINE ]
-------------------------------
POS.exe (Django + Waitress)
Port 0.0.0.0:8000
-------------------------------
      |         |         |
   [Client]  [Client]  [Client]
   Browser   Browser   Browser
   http://SERVER_IP:8000
```

- **Server** runs the pre-built `POS.exe` — no Python installation required.
- **Clients** access via web browser. No installation needed.

---

## Option A: Quick Start (EXE)

1. **Build or download** `POS.exe` (see Inno Setup installer)

2. **Configure Database**
   - On first run, the server creates `.env` from the bundled template
   - Edit `.env` with your `DATABASE_URL` and `DJANGO_SECRET_KEY`

3. **Run the EXE**
   ```bash
   POS.exe
   ```
   Starts Waitress on `0.0.0.0:8000`, opens POS window automatically.

4. **Client Access**
   Clients open `http://SERVER_IP:8000` in any browser.

---

## Option B: Build from Source

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller POS.spec
```

Output: `dist\POS\POS.exe`

---

## Option C: Inno Setup Installer (Full Deployment)

1. Build the EXE (see Option B)
2. Open `electric_lan.iss` in Inno Setup Compiler
3. Compile (Ctrl+F9)
4. Output: `Installer\POS-Setup.exe`

The installer:
- Installs `POS.exe` and supporting files to `%LOCALAPPDATA%\POS`
- Creates desktop shortcut
- Opens firewall port 8000 (optional)
- Starts server and opens browser after install
- Shows server IP on completion

### Client Installer (Optional)

1. Open `client_setup.iss` in Inno Setup
2. Compile
3. Output: `Installer\POSClient-Setup.exe`

The client installer:
- Asks for Server IP and Port
- Saves config to `server.conf`
- Creates desktop shortcut with the URL
- No Python/Django installed on client

---

## Security Configuration

### Production Settings (LAN mode)

Settings file: `config/settings/lan.py`

| Setting | Value | Notes |
|---------|-------|-------|
| `DEBUG` | `False` | Never enable in production |
| `ALLOWED_HOSTS` | `["*"]` | Safe on isolated LAN |
| `SECURE_SSL_REDIRECT` | `False` | HTTP only on LAN |
| `SESSION_COOKIE_SECURE` | `False` | HTTPS not required |
| `CSRF_COOKIE_SECURE` | `False` | HTTPS not required |
| `CSRF_TRUSTED_ORIGINS` | configurable | Add LAN IPs if needed |

### Firewall

Port 8000 TCP inbound is opened automatically by the installer.
To manually configure:
```bash
netsh advfirewall firewall add rule name="POS 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## Database

- **Only the server** has the database
- MySQL 8.0+ recommended
- Default credentials in `base.py`: `root` / `123456` on `localhost:3306`
- Change these in production and update `.env`

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| `main.py` | Django entry point (Waitress server launcher) |
| `POS.spec` | PyInstaller build spec |
| `config/settings/lan.py` | LAN-specific Django settings (DEBUG=False, HTTP mode) |
| `deployment/config/lan.env` | Environment template for LAN |
| `electric_lan.iss` | Server Inno Setup installer |
| `client_setup.iss` | Client shortcut installer |

---

## Quick Command Reference

```bash
# Build EXE
pip install pyinstaller
pyinstaller POS.spec

# Run server
POS.exe

# Firewall (Admin)
netsh advfirewall firewall add rule name="POS 8000" dir=in action=allow protocol=TCP localport=8000

# Migrate (when building from source)
python manage.py migrate --settings=config.settings.lan

# Collect static (when building from source)
python manage.py collectstatic --noinput --settings=config.settings.lan
```
