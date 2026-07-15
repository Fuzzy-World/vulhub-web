from fastapi import APIRouter
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import SystemConfig
from app.services import auth_service
from datetime import datetime

router = APIRouter()


class SettingsUpdate(BaseModel):
    vulhub_root_path: str = None
    server_port: int = None
    admin_password: str = None
    default_remove_image: bool = None
    idle_timeout_hours: int = None
    scan_cron: str = None
    cleanup_cron: str = None


@router.get("")
def get_settings():
    db = SessionLocal()
    try:
        configs = db.query(SystemConfig).all()
        result = {}
        for c in configs:
            result[c.config_key] = c.config_value

        return {
            "vulhub_root_path": result.get("vulhub_root_path", ""),
            "server_port": int(result.get("server_port", "8088")),
            "has_password": bool(result.get("admin_password_hash", "")),
            "default_remove_image": result.get("default_remove_image", "true").lower() == "true",
            "idle_timeout_hours": int(result.get("idle_timeout_hours", "0")),
            "scan_cron": result.get("scan_cron", "0 */6 * * *"),
            "cleanup_cron": result.get("cleanup_cron", "0 2 * * *"),
        }
    finally:
        db.close()


@router.post("")
def update_settings(req: SettingsUpdate):
    db = SessionLocal()
    try:
        updates = {}

        if req.vulhub_root_path is not None:
            updates["vulhub_root_path"] = req.vulhub_root_path

        if req.server_port is not None:
            updates["server_port"] = str(req.server_port)

        if req.admin_password is not None and len(req.admin_password) >= 4:
            auth_service.init_admin_password(req.admin_password)

        if req.default_remove_image is not None:
            updates["default_remove_image"] = str(req.default_remove_image).lower()

        if req.idle_timeout_hours is not None:
            updates["idle_timeout_hours"] = str(req.idle_timeout_hours)

        if req.scan_cron is not None:
            updates["scan_cron"] = req.scan_cron

        if req.cleanup_cron is not None:
            updates["cleanup_cron"] = req.cleanup_cron

        for key, value in updates.items():
            config_row = db.query(SystemConfig).filter_by(config_key=key).first()
            if config_row:
                config_row.config_value = value
                config_row.updated_at = datetime.now()
            else:
                db.add(SystemConfig(config_key=key, config_value=value))

        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}
    finally:
        db.close()
