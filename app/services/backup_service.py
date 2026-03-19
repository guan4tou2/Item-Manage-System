"""排程備份服務模組"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from app import get_db_type


def get_config() -> Dict[str, Any]:
    """取得備份設定（若無則回傳預設值）"""
    db_type = get_db_type()
    if db_type == "postgres":
        from app import db
        from app.models.backup_config import BackupConfig

        cfg = db.session.query(BackupConfig).first()
        if cfg:
            return cfg.to_dict()
    else:
        from app import mongo

        doc = mongo.db.backup_config.find_one({})
        if doc:
            doc.pop("_id", None)
            return doc

    # 預設設定
    return {
        "id": None,
        "schedule": "disabled",
        "time": "03:00",
        "destination": "local",
        "s3_bucket": "",
        "s3_region": "",
        "local_path": "",
        "retention_days": 30,
        "last_backup_at": None,
        "last_backup_status": "",
        "enabled": False,
    }


def update_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """儲存備份設定"""
    db_type = get_db_type()
    enabled = data.get("schedule", "disabled") != "disabled"

    if db_type == "postgres":
        from app import db
        from app.models.backup_config import BackupConfig

        cfg = db.session.query(BackupConfig).first()
        if not cfg:
            cfg = BackupConfig()
            db.session.add(cfg)

        cfg.schedule = data.get("schedule", "daily")
        cfg.time = data.get("time", "03:00")
        cfg.destination = data.get("destination", "local")
        cfg.s3_bucket = data.get("s3_bucket") or None
        cfg.s3_region = data.get("s3_region") or None
        cfg.local_path = data.get("local_path") or None
        cfg.retention_days = int(data.get("retention_days", 30))
        cfg.enabled = enabled
        db.session.commit()
        return cfg.to_dict()
    else:
        from app import mongo

        doc = {
            "schedule": data.get("schedule", "daily"),
            "time": data.get("time", "03:00"),
            "destination": data.get("destination", "local"),
            "s3_bucket": data.get("s3_bucket", ""),
            "s3_region": data.get("s3_region", ""),
            "local_path": data.get("local_path", ""),
            "retention_days": int(data.get("retention_days", 30)),
            "enabled": enabled,
        }
        mongo.db.backup_config.replace_one({}, doc, upsert=True)
        return doc


def run_backup() -> Dict[str, Any]:
    """執行一次備份，儲存到 local_path，回傳 {success, filename, message}"""
    from app.repositories import item_repo, type_repo, location_repo

    cfg = get_config()
    local_path = cfg.get("local_path") or ""

    if not local_path:
        local_path = str(Path(__file__).resolve().parent.parent.parent / "backups")

    try:
        Path(local_path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {"success": False, "message": f"無法建立備份目錄：{e}"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.json"
    filepath = Path(local_path) / filename

    db_type = get_db_type()
    backup_data = {
        "version": "1.2",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_type": db_type,
        "items": item_repo.get_all_items_for_backup(),
        "types": type_repo.get_all_types_for_backup(),
        "locations": location_repo.get_all_locations_for_backup(),
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _update_last_status("failed")
        return {"success": False, "message": f"備份寫入失敗：{e}"}

    _update_last_status("success")

    retention_days = int(cfg.get("retention_days") or 30)
    cleanup_old_backups(retention_days, local_path)

    return {
        "success": True,
        "filename": filename,
        "path": str(filepath),
        "message": f"備份完成：{filename}",
    }


def cleanup_old_backups(retention_days: int, local_path: str) -> int:
    """刪除超過 retention_days 的備份檔案，回傳刪除數量"""
    if not local_path:
        return 0

    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    try:
        for f in Path(local_path).glob("backup_*.json"):
            if f.stat().st_mtime < cutoff.timestamp():
                f.unlink()
                deleted += 1
    except Exception:
        pass
    return deleted


def _update_last_status(status: str) -> None:
    """更新備份設定中的最後備份時間與狀態"""
    db_type = get_db_type()
    now = datetime.utcnow()

    if db_type == "postgres":
        from app import db
        from app.models.backup_config import BackupConfig

        cfg = db.session.query(BackupConfig).first()
        if cfg:
            cfg.last_backup_at = now
            cfg.last_backup_status = status
            db.session.commit()
    else:
        from app import mongo

        mongo.db.backup_config.update_one(
            {},
            {"$set": {"last_backup_at": now, "last_backup_status": status}},
        )
