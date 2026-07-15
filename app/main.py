import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import init_db
from app.routers import auth, vulns, ranges, docker, settings, tasks
from app import config

app = FastAPI(title="Vulhub-Web", version="1.0.0")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(vulns.router, prefix="/api/vulns", tags=["Vulnerabilities"])
app.include_router(ranges.router, prefix="/api/ranges", tags=["Lab Management"])
app.include_router(docker.router, prefix="/api/docker", tags=["Docker Monitor"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Task History"])

# Static files and templates (relative to project root)
static_dir = os.path.join(config.BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup():
    init_db()
    _cleanup_stale_statuses()


def _cleanup_stale_statuses():
    """Clean up stuck states on startup (e.g. after abnormal shutdown)."""
    try:
        from app.database import SessionLocal
        from app.models import Vuln
        db = SessionLocal()
        try:
            db.query(Vuln).filter(Vuln.status == "building").update({Vuln.status: "unbuilt"})
            db.query(Vuln).filter(Vuln.status == "starting").update({Vuln.status: "built"})
            db.query(Vuln).filter(Vuln.status == "destroying").update({Vuln.status: "built"})
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


@app.get("/")
async def index():
    return FileResponse(os.path.join(config.BASE_DIR, "static", "index.html"))


@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(config.BASE_DIR, "static", "index.html"))


if __name__ == "__main__":
    try:
        from app.services.scheduler_service import SchedulerService
        scheduler = SchedulerService()
        scheduler.start()
    except Exception:
        print("[WARN] Scheduler failed to start, scheduled tasks unavailable")

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

    uvicorn.run(app, host="0.0.0.0", port=port)
