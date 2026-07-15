import os
import re
import yaml
from datetime import datetime
from app.database import SessionLocal
from app.models import Vuln, SystemConfig

CATEGORY_MAP = {
    "log4j": "log4j", "log4j2": "log4j",
    "shiro": "shiro",
    "fastjson": "fastjson",
    "struts2": "struts2", "struts": "struts2",
    "tomcat": "tomcat",
    "weblogic": "weblogic",
    "spring": "spring",
    "activemq": "activemq",
    "redis": "redis",
    "mysql": "mysql",
    "nginx": "nginx",
    "apache": "apache",
    "jboss": "jboss",
    "webmin": "webmin",
    "jenkins": "jenkins",
    "gitlab": "gitlab",
    "cve": "other",
    "thinkphp": "thinkphp",
    "laravel": "laravel",
    "django": "django",
    "flask": "flask",
    "node": "nodejs",
    "php": "php",
    "solr": "solr",
    "elasticsearch": "elasticsearch",
    "rabbitmq": "rabbitmq",
    "zabbix": "zabbix",
    "grafana": "grafana",
    "confluence": "confluence",
    "jira": "jira",
    "nexus": "nexus",
    "harbor": "harbor",
    "coredns": "coredns",
    "kibana": "kibana",
    "supervisor": "supervisor",
    "magento": "magento",
    "websockify": "other",
    "ghostscript": "other",
    "imagemagick": "other",
    "openssl": "other",
    "samba": "samba",
    "ftp": "ftp",
    "ssh": "ssh",
    "vnc": "vnc",
    "rmi": "rmi",
}


def _extract_cve_id(path: str) -> str:
    match = re.search(r"(CVE-\d{4}-\d+)", path, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    dirname = os.path.basename(path)
    return dirname.replace("-", " ").replace("_", " ").title()


def _extract_category(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        lower = part.lower()
        if lower in CATEGORY_MAP:
            return CATEGORY_MAP[lower]
    return "other"


def _extract_year(cve_id: str) -> str:
    match = re.search(r"CVE-(\d{4})", cve_id)
    return match.group(1) if match else ""


def _read_readme(vulhub_dir: str) -> str:
    for name in ["README.zh-cn.md", "README.md", "readme.md"]:
        readme_path = os.path.join(vulhub_dir, name)
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                pass
    return ""


def _extract_description(readme: str) -> str:
    """Extract the first # heading from README as description."""
    for line in readme.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 3:
            return stripped.lstrip("# ").strip()[:200]
    return ""


def scan_vulhub_directory() -> dict:
    db = SessionLocal()
    try:
        config_row = db.query(SystemConfig).filter_by(config_key="vulhub_root_path").first()
        if not config_row or not config_row.config_value:
            return {"success": False, "message": "Vulhub root path not configured"}

        root_path = config_row.config_value
        if not os.path.isdir(root_path):
            return {"success": False, "message": f"Directory not found: {root_path}"}

        batch_id = int(datetime.now().timestamp())
        found_paths = set()
        added = 0
        updated = 0

        for dirpath, dirnames, filenames in os.walk(root_path):
            if "docker-compose.yml" in filenames or "docker-compose.yaml" in filenames:
                rel_path = os.path.relpath(dirpath, root_path)
                found_paths.add(rel_path)

                cve_id = _extract_cve_id(rel_path)
                category = _extract_category(rel_path)
                year = _extract_year(cve_id)
                readme = _read_readme(dirpath)
                description = _extract_description(readme)
                name = cve_id if cve_id.startswith("CVE-") else os.path.basename(rel_path)

                existing = db.query(Vuln).filter_by(vulhub_path=rel_path).first()
                if existing:
                    existing.cve_id = cve_id
                    existing.name = name
                    existing.category = category
                    existing.year = year
                    existing.description = description
                    existing.readme_content = readme
                    existing.scan_batch_id = batch_id
                    existing.updated_at = datetime.now()
                    updated += 1
                else:
                    vuln = Vuln(
                        cve_id=cve_id,
                        name=name,
                        category=category,
                        description=description,
                        vulhub_path=rel_path,
                        status="unbuilt",
                        readme_content=readme,
                        year=year,
                        scan_batch_id=batch_id,
                    )
                    db.add(vuln)
                    added += 1

        # Remove entries for deleted directories
        removed = db.query(Vuln).filter(Vuln.scan_batch_id != batch_id).all()
        for v in removed:
            if v.vulhub_path not in found_paths:
                db.delete(v)

        db.commit()
        return {"success": True, "added": added, "updated": updated, "removed": len(removed)}

    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}
    finally:
        db.close()


def get_vulns(page: int = 1, page_size: int = 20, category: str = None,
              status: str = None, keyword: str = None, year: str = None) -> dict:
    db = SessionLocal()
    try:
        query = db.query(Vuln)
        if category and category != "all":
            query = query.filter(Vuln.category == category)
        if status and status != "all":
            query = query.filter(Vuln.status == status)
        if keyword:
            query = query.filter(
                (Vuln.cve_id.contains(keyword)) | (Vuln.name.contains(keyword))
            )
        if year and year != "all":
            query = query.filter(Vuln.year == year)

        total = query.count()
        items = query.order_by(Vuln.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "items": [_vuln_to_dict(v) for v in items],
        }
    finally:
        db.close()


def get_vuln(vuln_id: int):
    db = SessionLocal()
    try:
        v = db.query(Vuln).filter_by(id=vuln_id).first()
        if not v:
            return None
        return _vuln_to_dict(v, full=True)
    finally:
        db.close()


def get_categories() -> list:
    db = SessionLocal()
    try:
        rows = db.query(Vuln.category).distinct().all()
        result = []
        for (cat,) in rows:
            count = db.query(Vuln).filter_by(category=cat).count()
            result.append({"name": cat, "count": count})
        return sorted(result, key=lambda x: x["count"], reverse=True)
    finally:
        db.close()


def get_years() -> list:
    db = SessionLocal()
    try:
        rows = db.query(Vuln.year).filter(Vuln.year != "").distinct().all()
        return sorted([r[0] for r in rows], reverse=True)
    finally:
        db.close()


def _vuln_to_dict(v: Vuln, full: bool = False) -> dict:
    result = {
        "id": v.id,
        "cve_id": v.cve_id,
        "name": v.name,
        "category": v.category,
        "description": v.description,
        "vulhub_path": v.vulhub_path,
        "status": v.status,
        "year": v.year,
        "has_readme": bool(v.readme_content),
        "created_at": str(v.created_at) if v.created_at else "",
        "updated_at": str(v.updated_at) if v.updated_at else "",
    }
    if full:
        result["readme_content"] = v.readme_content
    return result
