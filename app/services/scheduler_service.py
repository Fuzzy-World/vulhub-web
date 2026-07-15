from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.models import SystemConfig, ContainerInfo, Vuln
from app.services.vuln_service import scan_vulhub_directory
from app.services.range_service import destroy_range
from app.services.docker_service import DockerService
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _get_cron(self, key: str, default: str) -> str:
        db = SessionLocal()
        try:
            config_row = db.query(SystemConfig).filter_by(config_key=key).first()
            return config_row.config_value if config_row and config_row.config_value else default
        finally:
            db.close()

    def _setup_jobs(self):
        # Incremental vulnerability scan
        scan_cron = self._get_cron("scan_cron", "0 */6 * * *")
        parts = scan_cron.split()
        if len(parts) == 5:
            self.scheduler.add_job(
                _scan_job, CronTrigger(minute=parts[0], hour=parts[1], day=parts[2],
                                       month=parts[3], day_of_week=parts[4]),
                id="scan_job", replace_existing=True,
            )

        # Docker cache cleanup
        cleanup_cron = self._get_cron("cleanup_cron", "0 2 * * *")
        parts = cleanup_cron.split()
        if len(parts) == 5:
            self.scheduler.add_job(
                _cleanup_job, CronTrigger(minute=parts[0], hour=parts[1], day=parts[2],
                                          month=parts[3], day_of_week=parts[4]),
                id="cleanup_job", replace_existing=True,
            )

        # Idle range reclamation (every 10 minutes)
        self.scheduler.add_job(_idle_check_job, "interval", minutes=10, id="idle_check_job")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def restart(self):
        self.scheduler.remove_all_jobs()
        self._setup_jobs()
        logger.info("Scheduler restarted")


def _scan_job():
    logger.info("Starting scheduled vulhub scan")
    result = scan_vulhub_directory()
    logger.info(f"Scan result: {result}")


def _cleanup_job():
    logger.info("Starting scheduled docker cleanup")
    docker_svc = DockerService()
    result = docker_svc.cleanup(remove_dangling=True, remove_cache=True)
    logger.info(f"Cleanup result: {result}")


def _idle_check_job():
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="idle_timeout_hours").first()
        if not config_row or not config_row.config_value:
            return
        timeout_hours = int(config_row.config_value)
        if timeout_hours <= 0:
            return

        default_remove = True
        remove_config = db.query(SystemConfig).filter_by(config_key="default_remove_image").first()
        if remove_config:
            default_remove = remove_config.config_value.lower() == "true"

        containers = db.query(ContainerInfo).all()
        for c in containers:
            if c.started_at:
                idle_hours = (datetime.now() - c.started_at).total_seconds() / 3600
                if idle_hours >= timeout_hours:
                    logger.info(f"Auto-destroying idle range: vuln_id={c.vuln_id}")
                    asyncio.run(destroy_range(c.vuln_id, remove_image=default_remove))
    except Exception as e:
        logger.error(f"Idle check error: {e}")
    finally:
        db.close()
