import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app import config

os.makedirs(config.DATA_DIR, exist_ok=True)

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _init_default_config()


def _init_default_config():
    from app.models import SystemConfig
    db = SessionLocal()
    try:
        defaults = {
            "vulhub_root_path": "",
            "server_port": str(config.DEFAULT_SERVER_PORT),
            "admin_password_hash": "",
            "default_remove_image": str(config.DEFAULT_REMOVE_IMAGE).lower(),
            "idle_timeout_hours": str(config.DEFAULT_IDLE_TIMEOUT_HOURS),
            "scan_cron": config.DEFAULT_SCAN_CRON,
            "cleanup_cron": config.DEFAULT_CLEANUP_CRON,
            "secret_key": "",
        }
        for key, value in defaults.items():
            exists = db.query(SystemConfig).filter_by(config_key=key).first()
            if not exists:
                db.add(SystemConfig(config_key=key, config_value=value))
        db.commit()
    finally:
        db.close()
