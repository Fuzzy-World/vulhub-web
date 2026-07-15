from fastapi import APIRouter
from pydantic import BaseModel
from app.services.docker_service import DockerService

router = APIRouter()


class CleanupRequest(BaseModel):
    remove_stopped: bool = False
    remove_dangling: bool = False
    remove_cache: bool = False


@router.get("/info")
def info():
    svc = DockerService()
    return svc.get_info()


@router.post("/cleanup")
def cleanup(req: CleanupRequest):
    svc = DockerService()
    return svc.cleanup(req.remove_stopped, req.remove_dangling, req.remove_cache)


@router.post("/destroy-all")
def destroy_all():
    svc = DockerService()
    return svc.destroy_all_running()
