from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services import auth_service

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class InitPasswordRequest(BaseModel):
    password: str


@router.post("/login")
def login(req: LoginRequest):
    if not auth_service.is_initialized():
        return {"success": False, "need_init": True, "message": "Please set admin password first"}

    token = auth_service.authenticate(req.password)
    if token:
        return {"success": True, "token": token}
    return {"success": False, "message": "Incorrect password"}


@router.post("/init")
def init_password(req: InitPasswordRequest):
    if auth_service.is_initialized():
        return {"success": False, "message": "Password already set, cannot re-initialize"}
    if len(req.password) < 4:
        return {"success": False, "message": "Password must be at least 4 characters"}
    auth_service.init_admin_password(req.password)
    token = auth_service.authenticate(req.password)
    return {"success": True, "token": token}


@router.get("/verify")
def verify(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token and auth_service.validate_token(token):
        return {"valid": True}
    return {"valid": False}


@router.get("/status")
def status():
    return {"initialized": auth_service.is_initialized()}
