#!/usr/bin/env python3
"""
Vulhub-Web — Web-based Vulnerability Lab Management Platform.

Zero-config Vulhub vulnerability library import, one-click lab lifecycle
management, real-time log streaming, and web terminal access.

Usage:
    python run.py
"""
import uvicorn
from app.main import app
from app import config


if __name__ == "__main__":
    # Load port from database config if available
    port = config.DEFAULT_SERVER_PORT
    try:
        from app.database import SessionLocal
        from app.models import SystemConfig
        db = SessionLocal()
        port_config = db.query(SystemConfig).filter_by(config_key="server_port").first()
        if port_config and port_config.config_value:
            port = int(port_config.config_value)
        db.close()
    except Exception:
        pass

    print(f"Vulhub-Web starting on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
