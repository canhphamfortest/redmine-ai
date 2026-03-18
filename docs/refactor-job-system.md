# Refactor Job System

## Vấn đề hiện tại

```
Thêm job mới phải sửa 4 nơi:
  redmine_handler.py   ← viết logic
  handlers/__init__.py ← export
  executor.py          ← thêm elif
  4_Jobs.py (Streamlit) ← thêm UI form
```

---

## Kiến trúc mới

```
app/jobs/
├── base_job.py              ← Abstract: name, options(), execute()
├── redmine_sync_job.py      ← Job type: Redmine
├── git_sync_job.py          ← Job type: Git
├── source_check_job.py      ← Job type: Source Check
└── chunk_embedding_job.py   ← Job type: Embedding
```

### Mỗi file job tự mô tả

```python
class RedmineSyncJob(BaseJob):
    name = "redmine_sync"
    label = "Redmine Sync"

    def options(self):
        return [
            {"key": "project_identifier", "type": "text",     "required": True},
            {"key": "incremental",         "type": "checkbox", "default": True},
        ]

    def execute(self, db, **kwargs) -> dict:
        ...
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
Hiện tại:                          Sau refactor:
─────────────────────────────      ──────────────────────────────
if type == "redmine_sync":         JOB_REGISTRY = discover("app/jobs/")
    execute_redmine_sync(...)      
elif type == "git_sync":           handler = JOB_REGISTRY[job.job_type]
    execute_git_sync(...)          result  = handler.execute(db, **job.config)
elif type == "source_check":
    ...
elif type == "chunk_embedding":
    ...
```

---

## API mới: `/api/jobs/types`

```
GET /api/jobs/types
→ Trả về danh sách job types + options của từng loại

[
  {
    "name": "redmine_sync",
    "label": "Redmine Sync",
    "options": [
      {"key": "project_identifier", "type": "text",     "required": true},
      {"key": "incremental",         "type": "checkbox", "default": true}
    ]
  },
  { "name": "chunk_embedding", ... },
  ...
]
```

---

## Streamlit: render form động

```
Hiện tại:                          Sau refactor:
─────────────────────────────      ──────────────────────────────
if job_type == "redmine_sync":     types = GET /api/jobs/types
    st.text_input("Project")       
elif job_type == "embedding":      for field in selected_type["options"]:
    st.number_input("Limit")           render_field(field)  ← tự động
elif ...
```

---

## Thêm job mới (sau refactor)

```
Chỉ cần tạo 1 file:

app/jobs/wiki_sync_job.py
  ├── name = "wiki_sync"
  ├── options() → khai báo params
  └── execute() → logic

→ Tự động xuất hiện trong:
   ✅ executor registry
   ✅ GET /api/jobs/types
   ✅ Streamlit form (không sửa UI)
```

---

## Các file thay đổi

| File | Hành động |
|------|-----------|
| `app/jobs/base_job.py` | Tạo mới |
| `app/jobs/*_job.py` (4 files) | Tạo mới, migrate logic từ handlers |
| `app/services/job_executor/executor.py` | Sửa: if/elif → registry |
| `app/services/job_executor/handlers/` | Xóa (logic chuyển vào jobs/) |
| `app/api/jobs/router.py` | Thêm route `/types` |
| `app/api/jobs/schemas.py` | JobType Enum tự động từ registry |
| `streamlit_app/pages/4_Jobs.py` | Sửa: hardcode → render động |

**Không thay đổi:** DB models, scheduler, services (RedmineSync, embedder...), API response format.
