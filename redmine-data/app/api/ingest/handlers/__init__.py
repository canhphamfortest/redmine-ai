"""Ingest API handlers.

Module này export tất cả handlers cho Ingestion API endpoints:
- Manual upload: ingest_manual
- Redmine ingestion: ingest_redmine, ingest_redmine_wiki, ingest_redmine_wiki_project
- Source management: list_sources, check_source, resync_source
- Statistics: get_ingestion_stats

Tất cả handlers được import từ các submodules và export qua __all__.
"""
from app.api.ingest.handlers.manual_upload import ingest_manual
from app.api.ingest.handlers.redmine_ingest import (
    ingest_redmine,
    ingest_redmine_wiki,
    ingest_redmine_wiki_project
)
from app.api.ingest.handlers.sources import list_sources, list_projects, check_source, resync_source
from app.api.ingest.handlers.stats import get_ingestion_stats

__all__ = [
    'ingest_manual',
    'ingest_redmine',
    'ingest_redmine_wiki',
    'ingest_redmine_wiki_project',
    'list_sources',
    'list_projects',
    'check_source',
    'resync_source',
    'get_ingestion_stats'
]

