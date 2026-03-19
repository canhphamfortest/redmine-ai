# Refactor Job System

## Vấn đề trước đây

```
Thêm job mới phải sửa 4 nơi:
  redmine_handler.py    ← viết logic
  handlers/__init__.py  ← export
  executor.py           ← thêm elif
  4_Jobs.py (Streamlit) ← thêm UI form hardcode
```

---

## Kiến trúc mới

```
app/jobs/
├── base_job.py              ← Abstract: name, label, options(), execute(), run_cli()
├── registry.py              ← Auto-discover *_job.py, singleton JOB_REGISTRY
├── redmine_sync_job.py      ← Job type: Redmine Sync
├── git_sync_job.py          ← Job type: Git Sync (placeholder)
├── source_check_job.py      ← Job type: Source Check
└── chunk_embedding_job.py   ← Job type: Chunk Embedding

app/services/job_executor/
├── exceptions.py            ← JobCancelledException + check_cancelled()
└── executor.py              ← Dispatch qua JOB_REGISTRY (bỏ if/elif)

app/api/jobs/
├── handlers/types.py        ← GET /api/jobs/types
└── router.py                ← Thêm route /types
```

---

## Mỗi file job tự mô tả

```python
class RedmineSyncJob(BaseJob):
    name = "redmine_sync"
    label = "Redmine Sync"
    description = "Đồng bộ issues từ Redmine project"

    def options(self):
        return [
            JobOption("project_identifier", "text",     "Project Identifier", required=True),
            JobOption("incremental",         "checkbox", "Incremental Sync",   default=True),
            JobOption("filters.status",      "multiselect", "Filter by Status",
                      options=["New", "In Progress", "Resolved", "Closed"]),
        ]

    def execute(self, db, execution_id=None, **kwargs) -> dict:
        ...
        return {"processed": 42, "created": 10, "failed": 0}

if __name__ == "__main__":
    RedmineSyncJob.run_cli()   # ← CLI entry point
```

---

## Flow tổng thể

```
                        app/jobs/*.py
                       (Job templates)
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     RedmineSyncJob  EmbeddingJob   SourceCheckJob
            │
            │  1 class → nhiều instances (config khác nhau)
            │
     ┌──────┴──────┐
     │             │
  "Sync A"      "Sync B"          ← ScheduledJob (DB records)
  project=A     project=B
  cron=0 2**    cron=0 3**
```

---

## Executor: tự khám phá, không if/elif

```
Trước:                             Sau:
─────────────────────────────      ──────────────────────────────
if type == "redmine_sync":         handler = JOB_REGISTRY.get(job.job_type)
    execute_redmine_sync(...)      if not handler:
elif type == "git_sync":               raise ValueError(...)
    execute_git_sync(...)          result = handler.execute(db, **job.config)
elif type == "source_check":
    ...
elif type == "chunk_embedding":
    ...
```

---

## Registry: tự discover, chống duplicate

```python
# registry.py — scan tất cả *_job.py, load BaseJob subclasses
JOB_REGISTRY = discover_jobs("app.jobs")
# → {"redmine_sync": RedmineSyncJob(), "chunk_embedding": ChunkEmbeddingJob(), ...}

# Duplicate detection:
# - Cùng class (re-export): bỏ qua, log DEBUG
# - Khác class, cùng name: log ERROR rõ ràng, không overwrite
```

---

## API: GET /api/jobs/types

```
GET /api/jobs/types
→ Trả về danh sách job types + options của từng loại

[
  {
    "name": "redmine_sync",
    "label": "Redmine Sync",
    "description": "Đồng bộ issues từ Redmine project",
    "options": [
      {"key": "project_identifier", "type": "text",     "required": true},
      {"key": "incremental",         "type": "checkbox", "default": true},
      {"key": "filters.status",      "type": "multiselect", "options": [...]}
    ]
  },
  ...
]
```

---

## Streamlit: render form động

```
Trước:                             Sau:
─────────────────────────────      ──────────────────────────────
if job_type == "redmine_sync":     types = GET /api/jobs/types
    st.text_input("Project")
elif job_type == "embedding":      for field in selected_type["options"]:
    st.number_input("Limit")           render_field(field)  ← tự động
elif ...

# Cron preset dùng session_state để text_input phản ánh đúng ngay:
st.session_state["cron_expression"] = _CRON_PRESETS[cron_preset]
cron_expression = st.text_input(..., value=st.session_state["cron_expression"])
```

---

## CLI: chạy job trực tiếp từ terminal

```bash
# Xem help + danh sách params
python -m app.jobs.redmine_sync_job --help

# Chạy Redmine sync
python -m app.jobs.redmine_sync_job --project_identifier=myproject --incremental=true

# Chạy embedding
python -m app.jobs.chunk_embedding_job --limit=200 --batch_size=32

# Chạy source check
python -m app.jobs.source_check_job --limit=500 --project_id=myproject

# Output:
# ▶ Running Redmine Sync...
#   Config: {"project_identifier": "myproject", "incremental": true}
# ✅ Done: {"processed": 42, "created": 10, "failed": 0}
```

`run_cli()` trong `BaseJob` tự parse `options()` thành argparse args.
**Thêm job mới sẽ tự có CLI — không cần viết thêm gì.**

---

## Các fix bổ sung

| File | Fix |
|------|-----|
| `chunk_embedding_job.py` | DB-level pagination thay vì `query.all()` — tránh OOM khi dataset lớn |
| `chunk_embedding_job.py` | `db.rollback()` trong except block — tránh `PendingRollbackError` |
| `redmine_sync_job.py` | Collect `filters.*` keys từ kwargs → merge vào dict filters |
| `registry.py` | Detect duplicate job name — log ERROR, không overwrite |
| `4_Jobs.py` | Cron preset dùng `session_state` — text input phản ánh đúng ngay |

---

## Thêm job mới (sau refactor)

```
Chỉ cần tạo 1 file: app/jobs/wiki_sync_job.py
  ├── name = "wiki_sync"
  ├── label = "Wiki Sync"
  ├── options() → khai báo params
  ├── execute() → logic
  └── if __name__ == "__main__": WikiSyncJob.run_cli()

→ Tự động có trong:
   ✅ executor registry
   ✅ GET /api/jobs/types
   ✅ Streamlit form (không sửa UI)
   ✅ CLI: python -m app.jobs.wiki_sync_job --help
```

---

## Không thay đổi

- DB models, scheduler, API response format
- Services: RedmineSync, SourceChecker, embedder
- Budget checker (system job, vẫn hardcode trong APScheduler)
- Docker volumes (scheduler không cần mount app/jobs/)
