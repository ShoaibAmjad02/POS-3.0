import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(settings.BASE_DIR) / "deployment" / "backups"
BACKUP_FILE = BACKUP_DIR / "pos_backup.sql"
METADATA_FILE = BACKUP_DIR / "backup_metadata.json"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_backup_metadata():
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "last_backup_time": None,
        "last_backup_status": None,
        "last_backup_error": None,
        "auto_backup_enabled": True,
        "backup_file_size": None,
    }


def save_backup_metadata(metadata):
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def get_backup_file_size():
    if BACKUP_FILE.exists():
        return BACKUP_FILE.stat().st_size
    return 0


def run_backup():
    db = settings.DATABASES["default"]
    engine = db.get("ENGINE", "")
    result = {"success": False, "error": None, "size": 0}

    try:
        if "mysql" in engine:
            result = _mysql_backup(db)
        elif "sqlite" in engine:
            result = _sqlite_backup(db)
        else:
            result["error"] = f"Unsupported database engine: {engine}"

        if result["success"]:
            result["size"] = get_backup_file_size()
            metadata = get_backup_metadata()
            metadata["last_backup_time"] = timezone.now().isoformat()
            metadata["last_backup_status"] = "success"
            metadata["last_backup_error"] = None
            metadata["backup_file_size"] = result["size"]
            save_backup_metadata(metadata)
            logger.info(f"Backup completed successfully. Size: {result['size']} bytes")
        else:
            metadata = get_backup_metadata()
            metadata["last_backup_time"] = timezone.now().isoformat()
            metadata["last_backup_status"] = "failed"
            metadata["last_backup_error"] = result["error"]
            save_backup_metadata(metadata)
            logger.error(f"Backup failed: {result['error']}")

    except Exception as e:
        error_msg = str(e)
        metadata = get_backup_metadata()
        metadata["last_backup_time"] = timezone.now().isoformat()
        metadata["last_backup_status"] = "failed"
        metadata["last_backup_error"] = error_msg
        save_backup_metadata(metadata)
        logger.error(f"Backup failed with exception: {error_msg}")
        result["error"] = error_msg

    return result


def _mysql_backup(db):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = BACKUP_DIR / "pos_backup_tmp.sql"

    possible_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 9.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 9.1\bin\mysqldump.exe",
        "mysqldump",
    ]

    mysqldump_path = None
    for p in possible_paths:
        if p == "mysqldump":
            try:
                subprocess.run([p, "--version"], capture_output=True, check=False)
                mysqldump_path = p
                break
            except FileNotFoundError:
                continue
        elif os.path.exists(p):
            mysqldump_path = p
            break

    if not mysqldump_path:
        return {"success": False, "error": "mysqldump not found. Install MySQL or add mysqldump to PATH."}

    cmd = [
        mysqldump_path,
        f"--user={db['USER']}",
        f"--password={db['PASSWORD']}",
        f"--host={db.get('HOST', 'localhost')}",
        f"--port={str(db.get('PORT', '3306'))}",
        "--routines",
        "--triggers",
        "--single-transaction",
        "--quick",
        db["NAME"],
    ]

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

        if result.returncode != 0:
            if temp_file.exists():
                temp_file.unlink()
            return {"success": False, "error": result.stderr.strip()}

        if temp_file.exists():
            if BACKUP_FILE.exists():
                BACKUP_FILE.unlink()
            temp_file.rename(BACKUP_FILE)

        return {"success": True, "error": None}

    except subprocess.TimeoutExpired:
        if temp_file.exists():
            temp_file.unlink()
        return {"success": False, "error": "mysqldump timed out after 300 seconds"}
    except FileNotFoundError:
        if temp_file.exists():
            temp_file.unlink()
        return {"success": False, "error": f"mysqldump not found at: {mysqldump_path}"}
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        return {"success": False, "error": str(e)}


def _sqlite_backup(db):
    db_path = db.get("NAME")
    if not db_path:
        return {"success": False, "error": "SQLite database path not configured"}

    db_path = Path(db_path)
    if not db_path.exists():
        return {"success": False, "error": f"Database file not found: {db_path}"}

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = BACKUP_DIR / "pos_backup_tmp.sql"
        with open(temp_file, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write("%s\n" % line)
        conn.close()

        if BACKUP_FILE.exists():
            BACKUP_FILE.unlink()
        temp_file.rename(BACKUP_FILE)

        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def should_run_auto_backup():
    metadata = get_backup_metadata()
    if not metadata.get("auto_backup_enabled", True):
        return False

    last_backup = metadata.get("last_backup_time")
    if not last_backup:
        return True

    try:
        last_time = datetime.fromisoformat(last_backup)
        if timezone.is_naive(last_time):
            last_time = timezone.make_aware(last_time)
        now = timezone.now()
        delta = now - last_time
        return delta.total_seconds() >= 86400
    except (ValueError, TypeError):
        return True
