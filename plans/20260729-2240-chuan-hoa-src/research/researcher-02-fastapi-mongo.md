# Researcher 02 — FastAPI + pymongo (nested comments) 

Installed: fastapi 0.124.2, pydantic 2.12.5, pymongo 4.15.5, python-dotenv 1.2.1, certifi 2025.11.12. **pydantic-settings NOT installed** (`pip install pydantic-settings`).

Blocker found: `src/models/product.py` `Comment` TypedDict has **no `id` field** (has `date` instead). The crawler must generate `id` (e.g. `uuid4().hex`) per comment or `(product_id, comment_id)` addressing is impossible for existing docs. Existing repo code (`find_comment_by_id`, `update_comment`, `delete_comment` in `src/repositories/comment_repository.py`) treats comment_id as the product `_id` — all three are wrong for the real schema.

## 1. Nested-array CRUD

`$` (first positional) — updates the FIRST array element matched **by the query filter**. Requires the array field in the filter.

```python
col.update_one(
    {"_id": ObjectId(pid), "comments.id": cid},
    {"$set": {"comments.$.content": "x", "comments.$.rating": 5}},
)
```
Pitfalls of `$`: (a) fails with `The positional operator did not find the match` if the filter doesn't reference `comments`; (b) only ever touches one element; (c) **cannot be used inside `upsert=True`**; (d) `$` can't be combined with a nested `$[]` path in some cases.

`arrayFilters` / `$[elem]` — identifier bound by a separate condition; updates **every** matching element and does not need the array in the query.

```python
col.update_one(
    {"_id": ObjectId(pid)},
    {"$set": {"comments.$[c].content": "x"}},
    array_filters=[{"c.id": cid}],
)
```
Pitfalls: every declared identifier must be used in the update doc (else `MongoServerError`); identifiers are `[a-z][a-zA-Z0-9]*`; requires MongoDB >= 3.6 (Atlas fine).

**Recommendation for this API:** use `$` for single-comment PATCH — the `"comments.id": cid` filter also gives you existence checking for free (`matched_count == 0` ⇒ 404, distinguishing "product missing" vs "comment missing" needs a second cheap lookup or a projection probe). Use `arrayFilters` only for bulk/conditional edits.

Partial update (only non-None fields), building dotted paths:
```python
payload = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
if not payload: raise HTTPException(400, "Không có dữ liệu để cập nhật")
res = col.update_one(
    {"_id": ObjectId(pid), "comments.id": cid},
    {"$set": {f"comments.$.{k}": v for k, v in payload.items()}},
)
if res.matched_count == 0: raise HTTPException(404, "...")
# NOTE: modified_count == 0 when the value is unchanged — use matched_count for 404.
```

Delete + keep `total_comments` in sync (single atomic update, no transaction needed):
```python
res = col.update_one(
    {"_id": ObjectId(pid), "comments.id": cid},
    {"$pull": {"comments": {"id": cid}}, "$inc": {"total_comments": -1}},
)
```
`$pull` on a non-existent id is a silent no-op, so the `comments.id` guard in the filter is what prevents `total_comments` drifting negative. Note `$pull` removes **all** elements matching — fine if ids are unique, dangerous if not.

Append (idempotent-ish, refuses duplicate id):
```python
res = col.update_one(
    {"_id": ObjectId(pid), "comments.id": {"$ne": new["id"]}},
    {"$push": {"comments": new}, "$inc": {"total_comments": 1}},
)
```
`$push` + `$inc` in one update doc is atomic at the document level — this is the correct way to maintain the denormalized counter. Never do read-modify-write in Python. You cannot `$set` a field and `$inc` the same field in one doc (conflict), but different fields are fine.

Index required: `col.create_index([("comments.id", 1)])` (multikey). Also `create_index([("link", 1)], unique=True)` matches the crawler's upsert-by-link semantics.

## 2. Pagination + projection

`skip`/`limit`: server walks and discards `skip` docs — O(skip). Fine to ~10k. `count_documents({})` on an empty filter does a full collection scan on Atlas (it's `$group`-based, not metadata); `estimated_document_count()` reads collection metadata and is O(1) but ignores filters and can be stale.

**Recommendation (admin API):** `skip`/`limit` + `count_documents(filter)` when a filter exists, `estimated_document_count()` when the filter is empty. Simplicity wins; the collection is products (thousands), not comments (millions).

```python
skip = (page - 1) * limit          # page>=1, limit clamped 1..100
cursor = (col.find({}, {"comments": 0})
             .sort("_id", -1).skip(skip).limit(limit))
total = col.estimated_document_count()
```
Cursor/range pagination (use only if the product count explodes) — stateless, O(1) per page, but no random page access:
```python
q = {"_id": {"$lt": ObjectId(after)}} if after else {}
docs = list(col.find(q, {"comments": 0}).sort("_id", -1).limit(limit))
next_cursor = str(docs[-1]["_id"]) if len(docs) == limit else None
```

Excluding the huge array. `{"comments": 0}` is exclusion-only — you may not mix it with inclusions (except `_id`). To exclude the array **and** return its size, use `$size` in an aggregation, or `$project` in a find projection (MongoDB 4.4+ supports aggregation expressions in find projections):

```python
# aggregation (portable, recommended)
pipeline = [
    {"$sort": {"_id": -1}}, {"$skip": skip}, {"$limit": limit},
    {"$project": {
        "name": 1, "link": 1, "crawled_at": 1, "version": 1,
        "total_comments": 1,
        "comment_count": {"$size": {"$ifNull": ["$comments", []]}},
    }},
]
docs = list(col.aggregate(pipeline))
```
`$ifNull` guards docs where `comments` is missing — a bare `$size` errors the whole pipeline on one bad doc. If `total_comments` is trustworthy, skip `$size` entirely and just project it (cheaper: no array materialization).

Detail endpoint may paginate comments server-side with `$slice`:
`col.find_one({"_id": oid}, {"comments": {"$slice": [skip, limit]}})`.

## 3. Error handling: envelope + HTTPException

Current code returns `success: False` with HTTP 200 for not-found — wrong. Correct pattern: routes return the envelope on success and `raise HTTPException` on failure; a global handler re-renders HTTPException into the *same* envelope so clients parse one shape.

```python
# src/app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "success": False, "message": str(exc.detail)},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(RequestValidationError)      # 422 body errors
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(422, content={"data": None, "success": False,
                                      "message": "Dữ liệu không hợp lệ",
                                      "errors": exc.errors()})

@app.exception_handler(Exception)                   # 500 catch-all
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("unhandled")
    return JSONResponse(500, content={"data": None, "success": False,
                                      "message": "Lỗi hệ thống"})
```
Notes: register the `HTTPException` handler (Starlette's `StarletteHTTPException` is what FastAPI's subclasses — importing from `fastapi` works because FastAPI's HTTPException subclasses it, but registering `starlette.exceptions.HTTPException` catches both, including 404-route-not-found). The bare `Exception` handler does not run under `TestClient(raise_server_exceptions=True)`. Delete the per-route `try/except` blocks in `src/api/comments.py` — they swallow real 500s into 200s. Map: 400 invalid/empty payload or malformed ObjectId, 404 product/comment missing, 409 duplicate comment id, 500 unexpected.

## 4. Config

Use **pydantic-settings** (`BaseSettings`) — one typed object, validation, `.env` + env-var precedence, no scattered `os.getenv` with stringly-typed defaults. python-dotenv alone gives you loading but no typing/validation; it's only preferable if you refuse a new dependency. Recommendation: pydantic-settings v2 (pydantic 2.12 is already installed, so no conflict).

```python
# src/config/settings.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore", case_sensitive=False)
    mongo_uri: str
    mongo_db: str = "selenium_scraper"
    mongo_collection: str = "comments"
    api_debug: bool = False

@lru_cache
def get_settings() -> Settings: return Settings()
```
`.env.example` with placeholder URI, committed; `.env` in `.gitignore`. **The live credentials are currently hardcoded in `src/config/database.py:12` and committed — rotate that Atlas password.** Field names map case-insensitively to `MONGO_URI`, `MONGO_DB`.

## 5. MongoClient lifecycle

`MongoClient` is thread-safe and holds its own connection pool; create **exactly one** per process and share it. Creating one per request destroys pooling. The current `_is_connection_alive()` ping on **every** `get_mongo_client()` call adds a full network round-trip per API call and is pure waste — pymongo's topology monitor already tracks server health in the background and operations auto-reconnect; a dead client raises on the actual operation, which your error handler turns into a 500. Drop the ping (keep at most one at startup for fail-fast).

```python
from contextlib import asynccontextmanager
import certifi
from pymongo import MongoClient
from pymongo.server_api import ServerApi

@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.mongo = MongoClient(s.mongo_uri, server_api=ServerApi("1"),
                                  tlsCAFile=certifi.where(), maxPoolSize=50,
                                  serverSelectionTimeoutMS=5000)
    app.state.db = app.state.mongo[s.mongo_db]
    app.state.mongo.admin.command("ping")     # fail fast, once
    yield
    app.state.mongo.close()

app = FastAPI(lifespan=lifespan)
```
`tlsCAFile=certifi.where()` is required on macOS/Windows for `mongodb+srv://` Atlas — without it pymongo 4.x uses the OS trust store and commonly fails `CERTIFICATE_VERIFY_FAILED`. Keep it. Also: `mongodb+srv` needs `dnspython` (pulled in by `pymongo[srv]`) — add `pymongo[srv]` to requirements.txt. Since pymongo is **synchronous and blocking**, define routes as `def` (not `async def`) so FastAPI runs them in the threadpool; `async def` + pymongo blocks the event loop. Alternative: switch to `AsyncMongoClient` (pymongo 4.9+) with `async def`.

Access via `Depends`, not a module-level singleton: `def get_db(request: Request): return request.app.state.db`.

## 6. ObjectId in Pydantic v2

```python
from typing import Annotated
from pydantic import BeforeValidator, BaseModel, ConfigDict
PyObjectId = Annotated[str, BeforeValidator(str)]

class ProductOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = Field(alias="_id")
    name: str
    link: str
    total_comments: int = 0
```
`BeforeValidator(str)` coerces `ObjectId -> str` on the way in; `alias="_id"` + `populate_by_name` lets the raw Mongo dict validate directly (`ProductOut.model_validate(doc)`). Avoid `bson.json_util.dumps` for API output — it emits `{"$oid": ...}`, not what clients want.

## Unresolved questions

- Do existing crawled documents actually contain `comments[].id`? The `Comment` TypedDict says no. If absent, a backfill migration (`$set` a uuid per element via aggregation-pipeline update) is a prerequisite, and the plan must include it.
- Is `total_comments` currently accurate on stored docs, or should the list endpoint compute `$size` and a one-off repair job reconcile it?
- Should comment ids be globally unique or only unique within a product? Affects whether `/comments/{id}` lookup without a product id is ever supported.
- Collection name: code uses `"comments"` for a products-shaped collection. Rename to `products` (requires data migration) or keep and just fix the API naming?
- Is write access to this API authenticated at all? Currently nothing gates POST/PATCH/DELETE.
