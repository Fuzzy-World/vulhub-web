import logging
import os
import re
import json
import asyncio
import subprocess
import shutil
import socket
import threading
from datetime import datetime
from app.database import SessionLocal
from app.models import Vuln, Task, SystemConfig, ContainerInfo
from typing import List, Dict
from app.services.docker_service import DockerService

logger = logging.getLogger(__name__)

# Active tasks to prevent duplicate operations
_active_tasks: Dict[int, str] = {}


def _get_compose_cmd() -> List[str]:
    """Detect available docker compose command. Prefer v2, fallback v1."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            return ["docker", "compose"]
    except Exception:
        pass
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return ["docker", "compose"]


def _get_vulhub_root() -> str:
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="vulhub_root_path").first()
        return config_row.config_value if config_row else ""
    finally:
        db.close()


def _get_config(key: str, default: str = "") -> str:
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key=key).first()
        return config_row.config_value if config_row else default
    finally:
        db.close()


def _create_task(vuln_id: int, task_type: str) -> Task:
    db = SessionLocal()
    try:
        task = Task(vuln_id=vuln_id, task_type=task_type, status="running", log_content="")
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


def _update_task(task_id: int, status: str, log: str = "", duration: int = 0):
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = status
            task.log_content = log
            task.duration_seconds = duration
            task.finished_at = datetime.now()
            db.commit()
    finally:
        db.close()


def _update_vuln_status(vuln_id: int, status: str):
    db = SessionLocal()
    try:
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if vuln:
            vuln.status = status
            vuln.updated_at = datetime.now()
            db.commit()
    finally:
        db.close()


def _get_compose_path(vuln: Vuln) -> str:
    root = _get_vulhub_root()
    return os.path.join(root, vuln.vulhub_path)


def _check_port_conflict(ports: List[int]) -> List[int]:
    conflicts = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                conflicts.append(port)
    return conflicts


def _parse_compose_ports(compose_dir: str) -> List[Dict]:
    """Parse port mappings from docker-compose.yml."""
    compose_file = os.path.join(compose_dir, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(compose_dir, "docker-compose.yaml")
    if not os.path.exists(compose_file):
        return []

    try:
        import yaml
        with open(compose_file, "r", encoding="utf-8") as f:
            compose = yaml.safe_load(f)
        ports = []
        for service_name, service in compose.get("services", {}).items():
            for port_mapping in service.get("ports", []):
                if isinstance(port_mapping, str):
                    parts = port_mapping.split(":")
                    if len(parts) >= 2:
                        host_port = int(parts[0])
                        container_port = int(parts[-1])
                        protocol = "tcp"
                        if "/" in parts[-1]:
                            container_port, protocol = parts[-1].split("/")
                        ports.append({
                            "host_port": host_port,
                            "container_port": int(container_port),
                            "protocol": protocol,
                        })
                elif isinstance(port_mapping, dict):
                    target = port_mapping.get("target", 0)
                    published = port_mapping.get("published", 0)
                    protocol = port_mapping.get("protocol", "tcp")
                    if published and target:
                        ports.append({
                            "host_port": int(published),
                            "container_port": int(target),
                            "protocol": protocol,
                        })
        return ports
    except Exception:
        return []


def _get_host_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def build_range(vuln_id: int) -> dict:
    """Submit a build task. Returns task_id immediately, builds in background."""
    db = SessionLocal()
    try:
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if not vuln:
            return {"success": False, "message": "Vulnerability not found"}
        if vuln.status == "running":
            return {"success": False, "message": "Lab is running. Please destroy first."}
        if vuln.status == "building":
            return {"success": False, "message": "Already building. Please wait."}
        if vuln.status == "starting":
            return {"success": False, "message": "Starting. Please wait."}
        if vuln.status == "destroying":
            return {"success": False, "message": "Destroying. Please wait."}
        if vuln.status == "built":
            return {"success": False, "message": "Already built. Destroy first to rebuild."}
        compose_dir = _get_compose_path(vuln)
        if not os.path.isdir(compose_dir):
            return {"success": False, "message": f"Directory not found: {compose_dir}"}
        logger.info(f"[BUILD] vuln_id={vuln_id}, cve={vuln.cve_id}, compose_dir={compose_dir}")
    finally:
        db.close()

    task = _create_task(vuln_id, "build")
    _update_vuln_status(vuln_id, "building")

    def _do_build():
        try:
            start_time = datetime.now()
            compose_cmd = _get_compose_cmd()
            all_log = ""

            logger.info(f"[BUILD] Pulling: {' '.join(compose_cmd + ['pull'])}, cwd={compose_dir}")
            pull_proc = subprocess.run(
                compose_cmd + ["pull"],
                cwd=compose_dir,
                capture_output=True, text=True, timeout=1800,
            )
            all_log += (pull_proc.stdout or "") + (pull_proc.stderr or "")

            logger.info(f"[BUILD] Building: {' '.join(compose_cmd + ['build'])}, cwd={compose_dir}")
            build_proc = subprocess.run(
                compose_cmd + ["build"],
                cwd=compose_dir,
                capture_output=True, text=True, timeout=1800,
            )
            all_log += (build_proc.stdout or "") + (build_proc.stderr or "")

            duration = (datetime.now() - start_time).seconds
            logger.info(f"[BUILD] Done: pull_rc={pull_proc.returncode}, build_rc={build_proc.returncode}, duration={duration}s")

            if pull_proc.returncode == 0 and build_proc.returncode == 0:
                _update_task(task.id, "success", all_log, duration)
                _update_vuln_status(vuln_id, "built")
            else:
                _update_task(task.id, "failed", all_log, duration)
                _update_vuln_status(vuln_id, "unbuilt")
        except subprocess.TimeoutExpired:
            logger.error(f"[BUILD] Timeout: vuln_id={vuln_id}")
            _update_task(task.id, "failed", "Build timeout (30 minutes)")
            _update_vuln_status(vuln_id, "unbuilt")
        except Exception as e:
            logger.error(f"[BUILD] Error: vuln_id={vuln_id}, error={e}")
            _update_task(task.id, "failed", str(e))
            _update_vuln_status(vuln_id, "unbuilt")
        finally:
            _active_tasks.pop(vuln_id, None)

    t = threading.Thread(target=_do_build, daemon=True)
    t.start()
    return {"success": True, "task_id": task.id, "message": "Build task submitted"}


async def start_range(vuln_id: int) -> dict:
    """Submit a start task. Returns task_id immediately, starts in background."""
    db = SessionLocal()
    try:
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if not vuln:
            return {"success": False, "message": "Vulnerability not found"}
        if vuln.status == "running":
            return {"success": False, "message": "Lab is already running"}
        if vuln.status in ("building", "starting", "destroying"):
            return {"success": False, "message": f"Status {vuln.status}, please wait"}

        compose_dir = _get_compose_path(vuln)
        ports = _parse_compose_ports(compose_dir)

        host_ports = [p["host_port"] for p in ports]
        conflicts = _check_port_conflict(host_ports)
        if conflicts:
            return {"success": False, "message": f"Port conflict: {conflicts}", "conflicts": conflicts}
    finally:
        db.close()

    task = _create_task(vuln_id, "start")
    _update_vuln_status(vuln_id, "starting")
    _active_tasks[vuln_id] = "start"

    def _do_start():
        original_status = "built"
        try:
            start_time = datetime.now()
            process = subprocess.run(
                _get_compose_cmd() + ["up", "-d"],
                cwd=compose_dir,
                capture_output=True, text=True, timeout=300,
            )
            duration = (datetime.now() - start_time).seconds
            log_text = (process.stdout or "") + (process.stderr or "")

            if process.returncode == 0:
                _update_task(task.id, "success", log_text, duration)
                _update_vuln_status(vuln_id, "running")

                docker_svc = DockerService()
                containers_info = docker_svc.get_compose_containers_info(compose_dir)
                host_ip = _get_host_ip()

                access_urls = []
                for port_info in ports:
                    access_urls.append(f"http://{host_ip}:{port_info['host_port']}")
                access_url = access_urls[0] if access_urls else ""

                db2 = SessionLocal()
                try:
                    if containers_info:
                        for c in containers_info:
                            container_info = db2.query(ContainerInfo).filter_by(vuln_id=vuln_id).first()
                            info_data = {
                                "vuln_id": vuln_id,
                                "container_id": c.get("id", "")[:12],
                                "access_url": access_url,
                                "ports_json": json.dumps(ports),
                                "started_at": datetime.now(),
                            }
                            if container_info:
                                for k, v in info_data.items():
                                    setattr(container_info, k, v)
                            else:
                                db2.add(ContainerInfo(**info_data))
                        db2.commit()
                    else:
                        container_info = db2.query(ContainerInfo).filter_by(vuln_id=vuln_id).first()
                        info_data = {
                            "vuln_id": vuln_id,
                            "container_id": "",
                            "access_url": access_url,
                            "ports_json": json.dumps(ports),
                            "started_at": datetime.now(),
                        }
                        if container_info:
                            for k, v in info_data.items():
                                setattr(container_info, k, v)
                        else:
                            db2.add(ContainerInfo(**info_data))
                        db2.commit()
                finally:
                    db2.close()
            else:
                _update_task(task.id, "failed", log_text, duration)
                _update_vuln_status(vuln_id, original_status)
        except Exception as e:
            _update_task(task.id, "failed", str(e))
            _update_vuln_status(vuln_id, original_status)
        finally:
            _active_tasks.pop(vuln_id, None)

    t = threading.Thread(target=_do_start, daemon=True)
    t.start()
    return {"success": True, "task_id": task.id, "message": "Start task submitted"}


async def destroy_range(vuln_id: int, remove_image: bool = False) -> dict:
    """Submit a destroy task. Returns task_id immediately, destroys in background."""
    db = SessionLocal()
    try:
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if not vuln:
            return {"success": False, "message": "Vulnerability not found"}
        if vuln.status in ("building", "destroying"):
            return {"success": False, "message": f"Status {vuln.status}, please wait"}
        original_status = vuln.status
        compose_dir = _get_compose_path(vuln)
    finally:
        db.close()

    task = _create_task(vuln_id, "destroy")
    _update_vuln_status(vuln_id, "destroying")
    _active_tasks[vuln_id] = "destroy"

    def _do_destroy():
        try:
            start_time = datetime.now()
            cmd = _get_compose_cmd() + ["down"]
            if remove_image:
                cmd += ["--rmi", "all"]

            process = subprocess.run(
                cmd,
                cwd=compose_dir,
                capture_output=True, text=True, timeout=300,
            )
            duration = (datetime.now() - start_time).seconds
            log_text = (process.stdout or "") + (process.stderr or "")

            if process.returncode == 0:
                _update_task(task.id, "success", log_text, duration)

                db2 = SessionLocal()
                try:
                    db2.query(ContainerInfo).filter_by(vuln_id=vuln_id).delete()
                    db2.commit()
                finally:
                    db2.close()

                new_status = "unbuilt" if remove_image else "built"
                _update_vuln_status(vuln_id, new_status)
            else:
                _update_task(task.id, "failed", log_text, duration)
                _update_vuln_status(vuln_id, original_status)
        except Exception as e:
            _update_task(task.id, "failed", str(e))
            _update_vuln_status(vuln_id, original_status)
        finally:
            _active_tasks.pop(vuln_id, None)

    t = threading.Thread(target=_do_destroy, daemon=True)
    t.start()
    return {"success": True, "task_id": task.id, "message": "Destroy task submitted"}


async def batch_destroy(vuln_ids: List[int], remove_image: bool = False) -> dict:
    results = []
    for vid in vuln_ids:
        result = await destroy_range(vid, remove_image)
        results.append({"vuln_id": vid, **result})
    success_count = sum(1 for r in results if r.get("success"))
    return {"total": len(vuln_ids), "success": success_count, "results": results}


def get_running_ranges() -> list:
    db = SessionLocal()
    try:
        containers = db.query(ContainerInfo).all()
        result = []
        for c in containers:
            vuln = db.query(Vuln).filter_by(id=c.vuln_id).first()
            if not vuln:
                continue

            uptime = int((datetime.now() - c.started_at).total_seconds()) if c.started_at else 0

            access_url = c.access_url
            if not access_url:
                compose_dir = _get_compose_path(vuln)
                ports = _parse_compose_ports(compose_dir)
                host_ip = _get_host_ip()
                if ports:
                    access_url = f"http://{host_ip}:{ports[0]['host_port']}"

            result.append({
                "id": vuln.id,
                "cve_id": vuln.cve_id,
                "name": vuln.name,
                "status": "running",
                "access_url": access_url,
                "ports": json.loads(c.ports_json) if c.ports_json else [],
                "uptime_seconds": uptime,
                "container_id": c.container_id,
            })
        return result
    finally:
        db.close()


def get_container_resource(container_id: str) -> dict:
    """Get resource usage for a single container."""
    if not container_id:
        return {"cpu_percent": 0, "memory_usage_mb": 0}
    try:
        docker_svc = DockerService()
        stats = docker_svc.get_container_stats(container_id)
        return {
            "cpu_percent": round(stats.get("cpu_percent", 0), 1),
            "memory_usage_mb": round(stats.get("memory_mb", 0), 1),
        }
    except Exception:
        return {"cpu_percent": 0, "memory_usage_mb": 0}


async def stream_container_logs(vuln_id: str, tail: int = 100):
    db = SessionLocal()
    try:
        container_info = db.query(ContainerInfo).filter_by(vuln_id=int(vuln_id)).first()
        if not container_info or not container_info.container_id:
            yield f"data: {json.dumps({'error': 'Container not running'})}\n\n"
            return

        container_id = container_info.container_id
    finally:
        db.close()

    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", str(tail), "-f", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        while True:
            chunk = await process.stdout.read(4096)
            if not chunk:
                break
            for line in chunk.decode("utf-8", errors="replace").splitlines():
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
