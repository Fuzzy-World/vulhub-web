import json
import os
import asyncio
import subprocess
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from app.services import range_service
from app.services.docker_service import DockerService
from app.database import SessionLocal
from app.models import ContainerInfo, Vuln

router = APIRouter()


class DestroyRequest(BaseModel):
    remove_image: bool = False


class BatchDestroyRequest(BaseModel):
    vuln_ids: List[int]
    remove_image: bool = False


@router.post("/{vuln_id}/build")
async def build(vuln_id: int):
    return await range_service.build_range(vuln_id)


@router.post("/{vuln_id}/start")
async def start(vuln_id: int):
    return await range_service.start_range(vuln_id)


@router.post("/{vuln_id}/stop")
async def stop(vuln_id: int):
    return await range_service.destroy_range(vuln_id, remove_image=False)


@router.post("/{vuln_id}/destroy")
async def destroy(vuln_id: int, req: DestroyRequest = None):
    remove_image = req.remove_image if req else False
    return await range_service.destroy_range(vuln_id, remove_image=remove_image)


@router.get("/{vuln_id}/status")
def status(vuln_id: int):
    db = SessionLocal()
    try:
        container_info = db.query(ContainerInfo).filter_by(vuln_id=vuln_id).first()
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if not vuln:
            return {"error": "Vulnerability not found"}
        result = {"status": vuln.status}
        if container_info:
            result["access_url"] = container_info.access_url
            result["ports"] = json.loads(container_info.ports_json) if container_info.ports_json else []
        return result
    finally:
        db.close()


@router.get("/{vuln_id}/logs")
async def stream_logs(vuln_id: str, tail: int = Query(100)):
    return StreamingResponse(
        range_service.stream_container_logs(vuln_id, tail),
        media_type="text/event-stream",
    )


@router.websocket("/{vuln_id}/terminal")
async def terminal(websocket: WebSocket, vuln_id: str):
    """Web terminal using PTY + docker exec -it for interactive shell."""
    await websocket.accept()

    db = SessionLocal()
    container_info = db.query(ContainerInfo).filter_by(vuln_id=int(vuln_id)).first()
    db.close()

    if not container_info or not container_info.container_id:
        await websocket.send_text("\r\nError: Container not running or container ID is empty\r\n")
        await websocket.close()
        return

    container_id = container_info.container_id

    try:
        import pty
        import fcntl
        master_fd, slave_fd = pty.openpty()

        process = subprocess.Popen(
            ["docker", "exec", "-it", container_id, "/bin/sh"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)

        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    except Exception as e:
        await websocket.send_text(f"\r\nError: Failed to start terminal: {e}\r\n")
        await websocket.close()
        return

    loop = asyncio.get_event_loop()
    running = True

    def on_readable():
        nonlocal running
        try:
            data = os.read(master_fd, 4096)
            if data:
                asyncio.ensure_future(
                    websocket.send_text(data.decode("utf-8", errors="replace"))
                )
            else:
                running = False
                loop.remove_reader(master_fd)
        except OSError:
            running = False
            loop.remove_reader(master_fd)
        except Exception:
            pass

    loop.add_reader(master_fd, on_readable)

    try:
        while running:
            data = await websocket.receive_text()
            if not running:
                break
            try:
                os.write(master_fd, data.encode("utf-8"))
            except OSError:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        running = False
        try:
            loop.remove_reader(master_fd)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


@router.get("/running")
def running():
    return range_service.get_running_ranges()


@router.get("/resource/{container_id}")
def container_resource(container_id: str):
    return range_service.get_container_resource(container_id)


@router.post("/batch-destroy")
async def batch_destroy(req: BatchDestroyRequest):
    return await range_service.batch_destroy(req.vuln_ids, req.remove_image)
