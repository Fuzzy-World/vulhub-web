from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from app.services import vuln_service
from app.database import SessionLocal
from app.models import Vuln, SystemConfig
import markdown
import re
import os

router = APIRouter()


@router.get("")
def list_vulns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query(None),
    status: str = Query(None),
    keyword: str = Query(None),
    year: str = Query(None),
):
    return vuln_service.get_vulns(page, page_size, category, status, keyword, year)


@router.post("/scan")
def scan():
    result = vuln_service.scan_vulhub_directory()
    return result


@router.get("/categories")
def categories():
    return vuln_service.get_categories()


@router.get("/years")
def years():
    return vuln_service.get_years()


@router.get("/{vuln_id}")
def get_vuln(vuln_id: int):
    vuln = vuln_service.get_vuln(vuln_id)
    if not vuln:
        return {"error": "Vulnerability not found"}
    return vuln


@router.get("/{vuln_id}/readme")
def get_readme(vuln_id: int):
    vuln = vuln_service.get_vuln(vuln_id)
    if not vuln:
        return {"error": "Vulnerability not found"}
    readme_md = vuln.get("readme_content", "")

    # Rewrite relative image paths to API endpoints
    readme_md = re.sub(
        r'!\[([^\]]*)\]\((?!https?://)(?!data:)([^)]+)\)',
        lambda m: f'![{m.group(1)}](/api/vulns/{vuln_id}/readme-assets/{m.group(2).lstrip("./")})',
        readme_md,
    )

    html = markdown.markdown(
        readme_md,
        extensions=["fenced_code", "tables", "codehilite", "toc"],
        extension_configs={"codehilite": {"css_class": "highlight"}},
    )
    return {"html": html, "raw": readme_md}


@router.get("/{vuln_id}/readme-assets/{file_path:path}")
def get_readme_asset(vuln_id: int, file_path: str):
    """Serve static assets (images etc.) from vulnerability directories."""
    db = SessionLocal()
    try:
        vuln = db.query(Vuln).filter_by(id=vuln_id).first()
        if not vuln:
            return {"error": "Vulnerability not found"}
        config_row = db.query(SystemConfig).filter_by(config_key="vulhub_root_path").first()
        vulhub_root = config_row.config_value if config_row else ""
    finally:
        db.close()

    # Path traversal protection
    asset_path = os.path.normpath(os.path.join(vulhub_root, vuln.vulhub_path, file_path))
    vulhub_dir = os.path.normpath(os.path.join(vulhub_root, vuln.vulhub_path))
    if not asset_path.startswith(vulhub_dir):
        return {"error": "Invalid path"}

    if os.path.isfile(asset_path):
        return FileResponse(asset_path)
    return {"error": "File not found"}
