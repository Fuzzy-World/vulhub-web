import json
import asyncio
import subprocess
import shutil

try:
    import docker
    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False


def _get_compose_cmd():
    """Detect available docker compose command."""
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


class DockerService:
    def __init__(self):
        if not _DOCKER_AVAILABLE:
            self.client = None
            return
        try:
            self.client = docker.from_env()
        except Exception:
            self.client = None

    def get_info(self) -> dict:
        if not self.client:
            return {
                "disk_usage_gb": 0,
                "total_images": 0,
                "running_containers": 0,
                "stopped_containers": 0,
                "dangling_images": 0,
            }
        try:
            images = self.client.images.list()
            containers = self.client.containers.list(all=True)
            running = [c for c in containers if c.status == "running"]
            stopped = [c for c in containers if c.status != "running"]
            dangling = [i for i in images if not i.tags]

            disk_usage = 0
            try:
                disk_usage = sum(img.attrs.get("Size", 0) for img in images) / (1024**3)
            except Exception:
                pass

            return {
                "disk_usage_gb": round(disk_usage, 2),
                "total_images": len(images),
                "running_containers": len(running),
                "stopped_containers": len(stopped),
                "dangling_images": len(dangling),
            }
        except Exception as e:
            return {
                "disk_usage_gb": 0,
                "total_images": 0,
                "running_containers": 0,
                "stopped_containers": 0,
                "dangling_images": 0,
                "error": str(e),
            }

    def cleanup(self, remove_stopped: bool = False, remove_dangling: bool = False,
                remove_cache: bool = False) -> dict:
        result = {"removed_containers": 0, "removed_images": 0, "freed_gb": 0}
        if not self.client:
            return result

        try:
            if remove_stopped:
                containers = self.client.containers.list(all=True)
                for c in containers:
                    if c.status != "running":
                        try:
                            c.remove(force=True)
                            result["removed_containers"] += 1
                        except Exception:
                            pass

            if remove_dangling:
                images = self.client.images.list(filters={"dangling": True})
                for img in images:
                    try:
                        self.client.images.remove(img.id, force=True)
                        result["removed_images"] += 1
                    except Exception:
                        pass

            if remove_cache:
                try:
                    self.client.images.prune()
                except Exception:
                    pass

            return result
        except Exception as e:
            return {"error": str(e)}

    def destroy_all_running(self) -> dict:
        if not self.client:
            return {"destroyed": 0}
        try:
            count = 0
            containers = self.client.containers.list()
            for c in containers:
                try:
                    c.stop(timeout=5)
                    c.remove(force=True)
                    count += 1
                except Exception:
                    pass
            return {"destroyed": count}
        except Exception as e:
            return {"destroyed": 0, "error": str(e)}

    def get_compose_containers(self, compose_dir: str) -> list:
        if not self.client:
            return []
        try:
            container_ids = self._get_compose_container_ids(compose_dir)
            containers = []
            for cid in container_ids:
                try:
                    c = self.client.containers.get(cid)
                    containers.append(c)
                except Exception:
                    pass
            return containers
        except Exception:
            return []

    def _get_compose_container_ids(self, compose_dir: str) -> list:
        try:
            result = subprocess.run(
                _get_compose_cmd() + ["ps", "-q"],
                cwd=compose_dir,
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception:
            pass
        return []

    def get_compose_containers_info(self, compose_dir: str) -> list:
        try:
            result = subprocess.run(
                _get_compose_cmd() + ["ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                containers = []
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        containers.append({
                            "id": data.get("ID", data.get("id", ""))[:12],
                            "name": data.get("Name", data.get("name", "")),
                            "status": data.get("Status", data.get("status", "")),
                            "ports": data.get("Ports", data.get("ports", "")),
                            "running": "running" in (data.get("Status", "") or data.get("status", "")).lower(),
                        })
                    except json.JSONDecodeError:
                        continue
                return containers
        except Exception:
            pass
        # Fallback: ps -q + docker inspect
        try:
            container_ids = self._get_compose_container_ids(compose_dir)
            containers = []
            for cid in container_ids:
                insp = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{.Id}}|{{.Name}}|{{.State.Status}}|{{range .NetworkSettings.Ports}}{{.}}{{end}}",
                     cid],
                    capture_output=True, text=True, timeout=10,
                )
                if insp.returncode == 0:
                    parts = insp.stdout.strip().split("|")
                    containers.append({
                        "id": parts[0][:12] if len(parts) > 0 else cid[:12],
                        "name": parts[1].lstrip("/") if len(parts) > 1 else "",
                        "status": parts[2] if len(parts) > 2 else "",
                        "ports": parts[3] if len(parts) > 3 else "",
                        "running": parts[2] == "running" if len(parts) > 2 else False,
                    })
            return containers
        except Exception:
            return []

    def get_container_stats(self, container_id: str) -> dict:
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "{{.CPUPerc}}|{{.MemUsage}}", container_id],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|")
                cpu_percent = 0.0
                mem_mb = 0.0
                if len(parts) >= 2:
                    cpu_str = parts[0].strip().rstrip("%")
                    try:
                        cpu_percent = float(cpu_str)
                    except ValueError:
                        pass
                    mem_str = parts[1].strip().split("/")[0].strip()
                    mem_mb = self._parse_mem_str(mem_str)
                return {"cpu_percent": round(cpu_percent, 1), "memory_mb": round(mem_mb, 1)}
        except Exception:
            pass
        return {"cpu_percent": 0, "memory_mb": 0}

    @staticmethod
    def _parse_mem_str(s: str) -> float:
        s = s.strip().lower()
        try:
            if "gib" in s or "gb" in s:
                return float(s.replace("gib", "").replace("gb", "").strip()) * 1024
            elif "mib" in s or "mb" in s:
                return float(s.replace("mib", "").replace("mb", "").strip())
            elif "kib" in s or "kb" in s:
                return float(s.replace("kib", "").replace("kb", "").strip()) / 1024
            elif "b" in s:
                return float(s.replace("b", "").strip()) / (1024 * 1024)
        except ValueError:
            pass
        return 0.0

    async def stream_container_logs(self, container_id: str, tail: int = 100):
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
                        yield line
        except Exception as e:
            yield f"Error: {str(e)}"

    def get_container_exec(self, container_id: str):
        if not self.client:
            return None
        try:
            container = self.client.containers.get(container_id)
            return container
        except Exception:
            return None
