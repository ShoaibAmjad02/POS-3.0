# POS Installation Guide

## Prerequisites

- **Windows 10/11** (64-bit)
- **MySQL Server 8.0+** (or MariaDB) - if using MySQL

---

## Build from Source

### Step 1: Install Python + Dependencies

```
pip install -r requirements.txt
pip install pyinstaller
```

### Step 2: Build EXE

```
pyinstaller POS.spec
```

Output: `dist\POS\POS.exe`

### Step 3: Run

Double-click `POS.exe` to start the server.

---

## Install via Inno Setup (Recommended)

1. Build the EXE first (see above)
2. Open `electric_lan.iss` in Inno Setup Compiler
3. Compile (Ctrl+F9)
4. Output: `Installer\POS-Setup.exe`
5. Run the installer on the target machine

The installer:
- Installs the pre-built EXE (no Python required)
- Creates desktop shortcut
- Opens firewall port 8000 (optional)
- Starts server automatically

---

## Usage

- **Start server**: Double-click `POS.exe` or use the desktop shortcut
- **Access locally**: `http://127.0.0.1:8000`
- **LAN access**: `http://SERVER_IP:8000`
- **Stop server**: Press Ctrl+C in the console window

---

## Database Setup

1. Create a MySQL database named `electricstore`
2. On first run, the server creates `.env` from the bundled template
3. Edit `.env` with your database credentials
4. Run migrations:
   ```
   python manage.py migrate --settings=config.settings.lan
   ```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 already in use | Change port in `config/settings/lan.py` |
| Database connection failed | Check MySQL credentials in `.env` |
| Static files not loading | Run `python manage.py collectstatic --noinput --settings=config.settings.lan` |
