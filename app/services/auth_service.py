import os
import json
import hmac
import hashlib
import base64
import time
import bcrypt as _bcrypt
from app.database import SessionLocal
from app.models import SystemConfig
from app import config


def get_password_hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(data: dict, expires_delta=None) -> str:
    to_encode = data.copy()
    expire = time.time() + (expires_delta.total_seconds() if expires_delta else config.JWT_EXPIRE_HOURS * 3600)
    to_encode.update({"exp": expire})

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(to_encode).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(config.get_secret_key().encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(config.get_secret_key().encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))

        if "exp" in payload and payload["exp"] < time.time():
            return None

        return payload
    except Exception:
        return None


def is_initialized() -> bool:
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="admin_password_hash").first()
        return bool(config_row and config_row.config_value)
    finally:
        db.close()


def init_admin_password(password: str):
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="admin_password_hash").first()
        if config_row:
            config_row.config_value = get_password_hash(password)
        else:
            db.add(SystemConfig(config_key="admin_password_hash", config_value=get_password_hash(password)))
        db.commit()
    finally:
        db.close()


def authenticate(password: str):
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="admin_password_hash").first()
        if not config_row or not config_row.config_value:
            return None
        if verify_password(password, config_row.config_value):
            return create_access_token({"sub": "admin"})
        return None
    finally:
        db.close()


def validate_token(token: str) -> bool:
    payload = decode_access_token(token)
    return payload is not None
