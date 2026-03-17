# Code Review Rule: No Hardcoded Credentials or Secrets

**What:** All credentials, API keys, and secrets must never be hardcoded in source code; they must be read from environment variables or secure configuration management.

**Why:** Hardcoded secrets can be exposed in version control history, logs, or accidental public repositories, creating critical security vulnerabilities.

**Good:**
```python
# Python
from app.config import settings
api_key = settings.openai_api_key

# Ruby
api_key = Setting.plugin_redmine_assistant['openai_api_key']
```

**Bad:**
```python
# Python
api_key = "sk-1234567890abcdef"

# Ruby
api_key = "sk-1234567890abcdef"
```

---

# Code Review Rule: Consistent Error Handling with Logging

**What:** All exceptions must be caught with specific exception types (never bare `except:`) and logged using the logger, with safe default return values.

**Why:** Bare exception handlers mask bugs, prevent proper error tracking, and can leave the application in an inconsistent state. Proper logging enables debugging and monitoring.

**Good:**
```python
try:
    result = openai_service.generate(prompt)
except OpenAIError as e:
    logger.error(f"OpenAI call failed: {str(e)}")
    return None
```

**Bad:**
```python
try:
    result = openai_service.generate(prompt)
except:
    print("Error occurred")
    raise
```

---

# Code Review Rule: No Debug Code in Production

**What:** Debug statements (`print()`, `console.log()`, `binding.pry`, `breakpoint()`, `debugger`) must not exist in committed code.

**Why:** Debug code clutters logs, impacts performance, and can expose sensitive information in production environments.

**Good:**
```python
logger.debug(f"Processing issue {issue_id}")
logger.info(f"Embedding completed in {elapsed_time}s")
```

**Bad:**
```python
print(f"DEBUG: issue={issue_id}, api_key={api_key}")
breakpoint()
```

---

# Code Review Rule: Proper HTTP Status Codes

**What:** API endpoints must return semantically correct HTTP status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error.

**Why:** Correct status codes enable proper client-side error handling, caching, and help with API monitoring and debugging.

**Good:**
```python
@app.post("/issues", status_code=201)
def create_issue(data: IssueSchema):
    return created_issue

@app.get("/issues/{id}")
def get_issue(id: int):
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue
```

**Bad:**
```python
@app.post("/issues")
def create_issue(data: IssueSchema):
    return created_issue  # Returns 200 instead of 201

@app.get("/issues/{id}")
def get_issue(id: int):
    return None  # Returns 200 with null instead of 404
```

---

# Code Review Rule: Environment Variables via Settings Object

**What:** All environment variables must be read through a centralized `settings` object (Python) or `Setting` helper (Ruby), never directly via `os.environ.get()` or `ENV[]` scattered throughout code.

**Why:** Centralized configuration management makes it easier to change, validate, and audit environment variable usage across the codebase.

**Good:**
```python
# Python: in app/config.py
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    openai_api_key: str
    redis_url: str = "redis://localhost"

# Usage anywhere
from app.config import settings
api_key = settings.openai_api_key
```

**Bad:**
```python
import os
api_key = os.environ.get("OPENAI_API_KEY")
redis_url = os.environ.get("REDIS_URL", "redis://localhost")
```

---

# Code Review Rule: Avoid N+1 Queries with Eager Loading

**What:** When querying related data, use `joinedload()` or `selectinload()` to fetch relationships in a single query, never loop through results and query again.

**Why:** N+1 queries cause severe performance degradation; eager loading reduces database round trips exponentially.

**Good:**
```python
from sqlalchemy.orm import joinedload
issues = db.query(Issue).options(joinedload(Issue.comments)).all()
```

**Bad:**
```python
issues = db.query(Issue).all()
for issue in issues:
    comments = db.query(Comment).filter(Comment.issue_id == issue.id).all()
```

---

# Code Review Rule: LLM Calls Must Be Logged and Cached Correctly

**What:** Every LLM API call must be logged to `OpenAIUsageLog` with token counts, and error responses must never be cached in Redis.

**Why:** Token usage tracking enables cost monitoring and budget alerts; caching errors causes stale bad data to be served repeatedly.

**Good:**
```python
try:
    response = await openai_client.chat.completions.create(...)
    log_usage(model=response.model, tokens=response.usage.total_tokens)
    cache.set(cache_key, response.content, ttl=86400)
except OpenAIError as e:
    logger.error(f"LLM call failed: {e}")
    return None  # Do not cache error
```

**Bad:**
```python
response = await openai_client.chat.completions.create(...)
cache.set(cache_key, response)  # No logging

# Caching error response
try:
    response = await openai_client.chat.completions.create(...)
except OpenAIError as e:
    cache.set(cache_key, str(e), ttl=3600)  # Wrong: caches error
```

---

# Code Review Rule: Embedding Dimension Consistency

**What:** Embedding dimension (1024) must match exactly across embedding model, database schema, and vector operations; empty/short text must return zero vector or be skipped, never raise exceptions.

**Why:** Mismatched dimensions cause vector DB errors; exceptions during embedding break the entire ingestion pipeline instead of gracefully handling edge cases.

**Good:**
```python
if not text or len(text.strip()) < 10:
    return np.zeros(1024)  # Zero vector for empty/short text

embedding = embed_model.embed(text)  # Returns shape (1024,)
assert embedding.shape == (1024,), "Dimension mismatch"
```

**Bad:**
```python
embedding = embed_model.embed("")  # Raises exception

# Schema mismatch
db.execute("CREATE TABLE vectors (embedding VECTOR(512))")  # But model outputs 1024
```

---

# Code Review Rule: Parameterized Queries Only

**What:** Never use string concatenation or f-strings to build SQL queries; always use parameterized queries via ORM or parameterized SQL.

**Why:** String-based SQL is vulnerable to SQL injection attacks that can leak or corrupt data.

**Good:**
```python
# SQLAlchemy ORM
issues = db.query(Issue).filter(Issue.project_id == project_id).all()

# Raw SQL with parameters
db.execute("SELECT * FROM issues WHERE project_id = %s", (project_id,))
```

**Bad:**
```python
# String concatenation (SQL injection vulnerability)
query = f"SELECT * FROM issues WHERE project_id = {project_id}"
db.execute(query)
```

---

# Code Review Rule: Authorization Checks Before Data Access

**What:** Every controller/router action must verify the user has permission to access the resource before processing (e.g., `issue.visible?`, `require_login`).

**Why:** Missing authorization checks allow users to access or modify data they shouldn't, creating security breaches.

**Good:**
```python
# Python FastAPI
@app.get("/issues/{issue_id}")
def get_issue(issue_id: int, current_user: User = Depends(