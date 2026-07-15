from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Vuln(Base):
    __tablename__ = "vulns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cve_id = Column(String(128), nullable=False, index=True)
    name = Column(String(256), nullable=False, default="")
    category = Column(String(64), nullable=False, default="other", index=True)
    description = Column(Text, nullable=False, default="")
    vulhub_path = Column(String(512), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="unbuilt", index=True)
    readme_content = Column(Text, default="")
    year = Column(String(8), default="")
    scan_batch_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vuln_id = Column(Integer, ForeignKey("vulns.id"), nullable=False, index=True)
    task_type = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="pending", index=True)
    log_content = Column(Text, default="")
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(128), nullable=False, unique=True)
    config_value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ContainerInfo(Base):
    __tablename__ = "container_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vuln_id = Column(Integer, ForeignKey("vulns.id"), nullable=False, unique=True)
    container_id = Column(String(128), nullable=False)
    access_url = Column(String(512), default="")
    ports_json = Column(Text, default="[]")
    uptime_seconds = Column(Integer, default=0)
    cpu_percent = Column(Float, default=0.0)
    memory_mb = Column(Float, default=0.0)
    started_at = Column(DateTime, server_default=func.now())
