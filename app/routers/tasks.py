from fastapi import APIRouter, Query
from app.database import SessionLocal
from app.models import Task

router = APIRouter()


@router.get("")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vuln_id: int = Query(None),
    task_type: str = Query(None),
    status: str = Query(None),
):
    db = SessionLocal()
    try:
        query = db.query(Task)
        if vuln_id:
            query = query.filter(Task.vuln_id == vuln_id)
        if task_type:
            query = query.filter(Task.task_type == task_type)
        if status:
            query = query.filter(Task.status == status)

        total = query.count()
        items = query.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "vuln_id": t.vuln_id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "duration_seconds": t.duration_seconds,
                    "created_at": str(t.created_at) if t.created_at else "",
                    "finished_at": str(t.finished_at) if t.finished_at else "",
                }
                for t in items
            ],
        }
    finally:
        db.close()


@router.get("/{task_id}")
def get_task(task_id: int):
    db = SessionLocal()
    try:
        t = db.query(Task).filter_by(id=task_id).first()
        if not t:
            return {"error": "Task not found"}
        return {
            "id": t.id,
            "vuln_id": t.vuln_id,
            "task_type": t.task_type,
            "status": t.status,
            "log_content": t.log_content,
            "duration_seconds": t.duration_seconds,
            "created_at": str(t.created_at) if t.created_at else "",
            "finished_at": str(t.finished_at) if t.finished_at else "",
        }
    finally:
        db.close()
