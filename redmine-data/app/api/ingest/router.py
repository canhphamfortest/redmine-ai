"""Router cho Ingestion API.

Module này định nghĩa các endpoints cho việc ingest dữ liệu vào hệ thống:
- Manual upload: Upload và ingest files thủ công
- Redmine ingestion: Ingest Redmine issues và wiki pages
- Source management: List, check, và resync sources
- Statistics: Lấy thống kê ingestion
"""
from fastapi import APIRouter

from app.api.ingest.handlers import (
    ingest_manual,
    ingest_redmine,
    ingest_redmine_wiki,
    ingest_redmine_wiki_project,
    list_sources,
    list_projects,
    check_source,
    resync_source,
    get_ingestion_stats
)

router = APIRouter()

# Đăng ký endpoints
router.add_api_route("/manual", ingest_manual, methods=["POST"])
router.add_api_route("/redmine", ingest_redmine, methods=["POST"])
router.add_api_route("/redmine/wiki", ingest_redmine_wiki, methods=["POST"])
router.add_api_route("/redmine/wiki/project", ingest_redmine_wiki_project, methods=["POST"])
router.add_api_route("/stats", get_ingestion_stats, methods=["GET"])
router.add_api_route("/sources", list_sources, methods=["GET"])
router.add_api_route("/sources/projects", list_projects, methods=["GET"])
router.add_api_route("/sources/{source_id}/check", check_source, methods=["POST"])
router.add_api_route("/sources/{source_id}/resync", resync_source, methods=["POST"])

