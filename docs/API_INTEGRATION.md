# Juris AI — API Integration Documentation
## Phase 11 — Backend Integration Foundation

> Last updated: Phase 11

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  client/shared/api/          ← Shared API contract layer             │
│  ├── config.ts               ← Base URL, headers, fetch defaults     │
│  ├── errors.ts               ← ApiError class, error normalization   │
│  ├── types.ts                ← Canonical TypeScript types            │
│  ├── client.ts               ← Core fetch wrapper (credentials:include) │
│  ├── auth.ts                 ← /auth/* typed functions               │
│  ├── health.ts               ← /health/* typed functions             │
│  ├── documents.ts            ← /documents/* typed functions          │
│  ├── research.ts             ← /qa/* and /retrieval/* typed functions│
│  ├── evaluation.ts           ← /evaluation/* typed functions         │
│  └── index.ts                ← Barrel export                         │
│                                                                      │
│  client/admin/lib/           ← Admin-specific wrappers               │
│  ├── authClient.ts           ← Delegates to @shared/api/auth         │
│  └── api.ts                  ← Portal-level API boundary             │
│                                                                      │
│  client/user/lib/            ← User-specific wrappers                │
│  └── authClient.ts           ← Delegates to @shared/api/auth         │
└──────────────────────────────────────────────────────────────────────┘
                    ↓  HTTP + credentials:include
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend — http://localhost:8000                             │
│  Session management: Starlette SessionMiddleware                     │
│  Cookie name: legalgraph_session (HttpOnly, Lax SameSite)           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend Base URL

| Environment Variable | Default | Location |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | All portals: `.env.local` |

**Never** scatter `localhost:8000` through application code. Always use `API_BASE_URL` from `@shared/api/config`.

No secrets are stored in frontend environment variables. API keys, database passwords, and OAuth secrets remain exclusively on the backend.

---

## 3. Authentication Model

Authentication uses **server-side sessions** via an **HttpOnly cookie**.

| Property | Value |
|---|---|
| Cookie name | `legalgraph_session` |
| Cookie type | HttpOnly — JavaScript **cannot** read it |
| SameSite | `Lax` |
| Secure | `false` in dev, `true` in production |
| Max age | 7 days (configurable via `SESSION_MAX_AGE_SECONDS`) |

The frontend **never** manages tokens. It determines auth state by calling `GET /auth/me`.

---

## 4. Session / Cookie Behavior

```
User logs in (password or Google OAuth)
  → Backend sets legalgraph_session cookie
  → Frontend receives AuthUser from /auth/me

Every subsequent API request:
  → fetch(..., { credentials: 'include' }) forwards the cookie automatically
  → Backend reads session from cookie → loads User from DB

User logs out:
  → Frontend calls POST /auth/logout
  → Backend clears the session
  → Frontend clears auth state and navigates to login
  → Next call to GET /auth/me returns 401
```

> [!IMPORTANT]
> All authenticated API calls use `credentials: 'include'`. This is enforced by `apiFetch()` in `client/shared/api/client.ts`.

---

## 5. API Client Architecture

### Core: `apiFetch<T>(path, init)`

Located at `client/shared/api/client.ts`. Features:
- Prepends `API_BASE_URL` to all paths
- Sets `credentials: 'include'` on every request
- Sets `Content-Type: application/json` and `Accept: application/json`
- Throws structured `ApiError` on any non-2xx response
- Throws `ApiError` with code `NETWORK_ERROR` on fetch failures
- Handles 204 No Content (returns `undefined`)

### Convenience Methods

```typescript
apiClient.get<T>(path)
apiClient.post<T>(path, body?)
apiClient.put<T>(path, body?)
apiClient.patch<T>(path, body?)
apiClient.delete<T>(path)
apiClient.upload<T>(path, formData)   // multipart, no Content-Type override
```

---

## 6. Endpoint Inventory

All endpoints verified in `server/api/app/api/routes/` during Phase 11 audit.

### Authentication — `router.prefix = '/auth'`

| Method | Path | Auth | Role | Request | Response | Status |
|---|---|---|---|---|---|---|
| GET | `/auth/me` | Session cookie | any | — | `CurrentUserResponse` | ✅ Real |
| POST | `/auth/login` | — | — | `{email, password}` | `CurrentUserResponse` | ✅ Real |
| POST | `/auth/register` | — | — | `{email, password, name?}` | `CurrentUserResponse` [201] | ✅ Real |
| POST | `/auth/logout` | Session cookie | any | — | 204 No Content | ✅ Real |
| GET | `/auth/google/login` | — | — | `?intent&redirect_uri` | Redirect or `{url}` | ✅ Real |
| GET | `/auth/google/callback` | — | — | `?code&state` | `CurrentUserResponse` | ✅ Real |

### Health — `router.prefix = ''`

| Method | Path | Auth | Role | Response | Status |
|---|---|---|---|---|---|
| GET | `/health` | — | — | `HealthResponse` | ✅ Real |
| GET | `/health/database` | — | — | `DatabaseHealthResponse` (200 or 503) | ✅ Real |

### Documents — `router.prefix = '/documents'`

| Method | Path | Auth | Role | Request | Response | Status |
|---|---|---|---|---|---|---|
| POST | `/documents/upload` | Session | ADMIN/SUPER_ADMIN | `multipart/form-data` + query params | `DocumentUploadResponse` [202] | ✅ Real |
| GET | `/documents` | Session | any | `?page&page_size&status` | `PaginatedDocuments` | ✅ Real |
| GET | `/documents/{id}` | Session | any | — | `DocumentDetail` | ✅ Real |
| GET | `/documents/{id}/chunks` | Session | any | `?page&page_size` | `PaginatedChunks` | ✅ Real |
| GET | `/documents/{id}/jobs` | Session | any | — | `ProcessingJob[]` | ✅ Real |
| POST | `/documents/{id}/reprocess` | Session | ADMIN/SUPER_ADMIN | — | `ReprocessResponse` [202] | ✅ Real |

### Retrieval — `router.prefix = '/retrieval'`

| Method | Path | Auth | Role | Request | Response | Status |
|---|---|---|---|---|---|---|
| POST | `/retrieval/search` | Session | any | `{query, top_k?}` | `RetrievalResponse` | ✅ Real |
| POST | `/retrieval/hybrid` | Session | any | `{query, top_k?}` | `HybridRetrievalResponse` | ✅ Real |
| POST | `/retrieval/rebuild` | Session | ADMIN/SUPER_ADMIN | — | `{...}` | ✅ Real |

### QA — `router.prefix = '/qa'`

| Method | Path | Auth | Role | Request | Response | Status |
|---|---|---|---|---|---|---|
| POST | `/qa/ask` | Session | any | `{query, top_k?}` | `QAAskResponse` | ✅ Real |

### Evaluation — `router.prefix = '/evaluation'`

| Method | Path | Auth | Role | Response | Status |
|---|---|---|---|---|---|
| GET | `/evaluation` | Session | ADMIN/SUPER_ADMIN | `PaginatedEvaluationRuns` | ✅ Real |
| GET | `/evaluation/{id}` | Session | ADMIN/SUPER_ADMIN | `EvaluationRunSchema` | ✅ Real |

---

## 7. Request / Response Contracts

### `GET /auth/me` — `CurrentUserResponse`

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "name": "User Name",
  "image_url": null,
  "role": "user",         // lowercase: "user" | "admin" | "super_admin"
  "is_active": true,
  "last_login_at": "2026-01-01T00:00:00Z"
}
```

> [!WARNING]
> Backend returns **lowercase** role strings. Admin portal types use uppercase. Use `normalizeRoleToUppercase()` from `@shared/api/types` when bridging.

### `POST /qa/ask` — `QAAskRequest`

```json
{
  "query": "What does Article 21 protect?",
  "top_k": 5
}
```

### `QAAskResponse` (abbreviated)

```json
{
  "query": "...",
  "status": "answered",
  "answer": "...",
  "insufficient_evidence": false,
  "citations": [...],
  "evidence": [...],
  "retrieval": { "mode": "hybrid", "evidence_count": 5 },
  "provider": "openai_compatible",
  "model": "gpt-4o-mini",
  "llm_called": true,
  "timings_ms": { "retrieval": 850, "llm": 2100 },
  "disclaimer": "Informational research aid. Not legal advice."
}
```

---

## 8. Error Handling

All API errors are normalized to `ApiError` instances:

```typescript
class ApiError extends Error {
  code: ApiErrorCode;     // 'UNAUTHORIZED' | 'FORBIDDEN' | 'NOT_FOUND' | ...
  status: number | null;  // HTTP status or null for network errors
  detail: string | string[];  // FastAPI error detail
  userMessage: string;    // User-facing display message
}
```

| HTTP Status | ApiErrorCode | Behavior |
|---|---|---|
| 401 | `UNAUTHORIZED` | Auth context resets, redirect to login |
| 403 | `FORBIDDEN` | Show "Insufficient permissions" |
| 404 | `NOT_FOUND` | Show "Resource not found" |
| 409 | `CONFLICT` | Show "Already exists" |
| 422 | `VALIDATION_ERROR` | Show field-level errors from FastAPI detail |
| 429 | `RATE_LIMITED` | Show "Too many requests" |
| 503 | `SERVICE_UNAVAILABLE` | Show "Service temporarily unavailable" |
| 500+ | `SERVER_ERROR` | Show "Unexpected server error" |
| Network | `NETWORK_ERROR` | Show "Could not reach server" |

> [!NOTE]
> `fetchCurrentUser()` treats 401 as "not authenticated" and returns `null` — it does NOT throw. All other errors propagate.

---

## 9. Role Requirements

Backend role values (from `app/models/enums.py::UserRole`):

| Backend Value | Frontend Display | Access Level |
|---|---|---|
| `"user"` | USER | Regular user endpoints only |
| `"admin"` | ADMIN | All user endpoints + admin-gated endpoints |
| `"super_admin"` | SUPER ADMIN | All endpoints including super-admin-only |

Admin-gated endpoints (`require_admin` dependency):
- `POST /documents/upload`
- `POST /documents/{id}/reprocess`
- `POST /retrieval/rebuild`
- `GET /evaluation`
- `GET /evaluation/{id}`

---

## 10. CORS Configuration

Backend allows cross-origin requests with credentials from:

```python
allowed_origins = [
    settings.frontend_url,   # configurable, default http://localhost:5173
    "http://localhost:3000",  # landing portal
    "http://localhost:3001",  # admin portal
    "http://localhost:3002",  # user portal
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

CORS settings:
- `allow_credentials: True` — required for HttpOnly cookie forwarding
- `allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]`
- `allow_headers: ["Content-Type", "Authorization", "Accept", "multipart/form-data"]`

> [!CAUTION]
> CORS is NOT set to `"*"`. Wildcard CORS would break credentials-based authentication.

---

## 11. Mock vs Real Integration Status

### Admin Portal

| Module | Integration | Backend Endpoint | Notes |
|---|---|---|---|
| Auth (`/auth/me`) | ✅ **REAL** | `GET /auth/me` | AuthContext calls real backend |
| Auth (logout) | ✅ **REAL** | `POST /auth/logout` | Real server-side session clear |
| Health dashboard | ✅ **REAL** | `GET /health` | Live API + DB status shown |
| Documents (list) | ✅ **REAL** | `GET /documents` | Real backend with pagination |
| Documents (upload) | ✅ **REAL** | `POST /documents/upload` | ADMIN only, 202 async |
| Documents (detail) | ✅ **REAL** | `GET /documents/{id}` | Real backend |
| Documents (jobs) | ✅ **REAL** | `GET /documents/{id}/jobs` | Real processing job history |
| Evaluation runs | ✅ **REAL** | `GET /evaluation` | ADMIN only |
| Users (list) | 🔲 **MOCK** | No endpoint | No `/users` endpoint in backend |
| Admins (list) | 🔲 **MOCK** | No endpoint | No `/admins` endpoint in backend |
| Graph nodes/edges | 🔲 **MOCK** | No endpoint | Neo4j is internal; no graph HTTP API |
| Validation queue | 🔲 **MOCK** | No endpoint | No `/validation` endpoint |
| Audit log | 🔲 **MOCK** | No endpoint | No `/audit` endpoint |
| Settings | 🔲 **MOCK** | No endpoint | No `/settings` endpoint |

### User Portal

| Module | Integration | Backend Endpoint | Notes |
|---|---|---|---|
| Auth (`/auth/me`) | ✅ **REAL** | `GET /auth/me` | AuthContext calls real backend |
| Auth (logout) | ✅ **REAL** | `POST /auth/logout` | Real server-side session clear |
| Research query | 🔲 **API CONTRACT** | `POST /qa/ask` | Typed function exists; UI still uses mock pipeline |
| Dense search | 🔲 **API CONTRACT** | `POST /retrieval/search` | Typed function exists; not wired to UI yet |
| Hybrid search | 🔲 **API CONTRACT** | `POST /retrieval/hybrid` | Typed function exists; not wired to UI yet |
| Research history | 🔲 **MOCK** | No endpoint | No `/research/history` endpoint |
| Saved research | 🔲 **MOCK** | No endpoint | No `/saved-research` endpoint |
| Profile | 🔲 **MOCK** | Partial — `/auth/me` | Profile fields from `/auth/me`; no `/profile` endpoint |

---

## 12. Pending Backend Endpoints

These endpoints are needed for full integration but do not exist yet:

| Priority | Endpoint | Purpose |
|---|---|---|
| High | `GET /users` | List all users (admin) |
| High | `GET /users/{id}` | Get user details (admin) |
| High | `PUT /users/{id}/role` | Change user role (super_admin) |
| High | `PUT /users/{id}/active` | Enable/disable user (admin) |
| High | `GET /audit` | Paginated audit event log (admin) |
| Medium | `GET /validation` | Validation queue items (admin) |
| Medium | `POST /validation/{id}/approve` | Approve validation item (admin) |
| Medium | `POST /validation/{id}/reject` | Reject validation item (admin) |
| Medium | `GET /settings` | Non-secret system configuration (admin) |
| Medium | `GET /research/history` | User research history (user) |
| Medium | `GET /saved-research` | User saved research list (user) |
| Low | `GET /health/neo4j` | Neo4j connectivity health |
| Low | `GET /health/vector-index` | FAISS index health |
| Low | `GET /health/llm` | LLM provider health |
| Low | `GET /graph/nodes` | Graph nodes for admin canvas |
| Low | `GET /graph/edges` | Graph edges for admin canvas |

---

## 13. Security Considerations

1. **No secrets in frontend**: `OPENAI_API_KEY`, `GOOGLE_CLIENT_SECRET`, database passwords, Neo4j credentials are backend-only.
2. **No token storage**: Authentication tokens are never stored in `localStorage` or `sessionStorage`. The session is maintained via HttpOnly cookie only.
3. **Credentials required**: `credentials: 'include'` is enforced at the `apiFetch` level — it cannot be accidentally omitted.
4. **Admin endpoint protection**: Upload, reprocess, rebuild, evaluation endpoints use `require_admin` dependency on the backend. Role checks are server-authoritative.
5. **Settings security**: The admin settings UI shows masked values for `isSecret: true` fields. The frontend never sends actual API keys to the backend — those are configured via server environment variables.
6. **CORS locked**: `allow_origins` is an explicit allowlist. `"*"` is never used.
7. **Session fixation**: Backend calls `request.session.clear()` before writing new session data on login.

---

## 14. Files Created / Modified

### Created

| File | Purpose |
|---|---|
| `client/shared/api/config.ts` | Base URL, headers, fetch defaults |
| `client/shared/api/errors.ts` | ApiError class, error codes |
| `client/shared/api/types.ts` | Canonical backend response types |
| `client/shared/api/client.ts` | Core fetch wrapper |
| `client/shared/api/auth.ts` | Auth endpoint functions |
| `client/shared/api/health.ts` | Health endpoint functions |
| `client/shared/api/documents.ts` | Document endpoint functions |
| `client/shared/api/research.ts` | QA + retrieval endpoint functions |
| `client/shared/api/evaluation.ts` | Evaluation endpoint functions |
| `client/shared/api/index.ts` | Barrel export |
| `docs/API_INTEGRATION.md` | This document |

### Modified

| File | Change |
|---|---|
| `client/admin/lib/authClient.ts` | Delegates to shared layer; fixes role type |
| `client/admin/lib/api.ts` | Real endpoints integrated; mock boundaries labeled |
| `client/admin/app/admin/(app)/page.tsx` | Real health connectivity via GET /health |
| `client/admin/tsconfig.json` | Added `@shared/*` path alias |
| `client/admin/next.config.mjs` | Added `turbopack: {}` to suppress Turbopack warning |
| `client/user/lib/authClient.ts` | Delegates to shared layer |
| `client/user/tsconfig.json` | Added `@shared/*` path alias |
| `client/user/next.config.mjs` | Added `turbopack: {}` to suppress Turbopack warning |

### Intentionally Untouched

| File/Directory | Reason |
|---|---|
| `client/landing/` | Frozen per Phase 11 instructions |
| `client/admin/ref/` | Admin reference folder — untouchable |
| `client/admin/ref 2/` | Admin reference folder — untouchable |
| `client/admin/context/AuthContext.tsx` | Already correct; uses real authClient |
| `client/admin/middleware.ts` | Already calls real GET /auth/me; no change needed |
| `client/user/context/AuthContext.tsx` | Already correct; uses real authClient |
| `client/user/middleware.ts` | Already works correctly |
| `server/api/app/` | Phase 11 is frontend integration only |
| All mock data files (`client/admin/data/`) | Retained; mock vs real distinction documented above |
| OAuth flow routes | Phase 10.7 verified and frozen |

---

## 15. Known Limitations

1. **No user management endpoints** — The admin Users/Admins UI continues to use mock data from `UserStoreContext`. Backend user management API must be built in a future phase.
2. **No graph HTTP endpoints** — The admin Graph Canvas displays static mock data. Neo4j is used internally by the backend but has no HTTP-accessible graph query API yet.
3. **No audit logging endpoint** — The admin Audit Log displays mock data. A server-side audit trail exists in the `SystemEvent` model but there's no API to expose it.
4. **No validation endpoint** — The admin Validation Queue operates on mock data only.
5. **No settings endpoint** — Admin settings are UI-only with no backend persistence.
6. **User research pipeline is mock** — The `ResearchStoreContext` uses simulated pipeline timers. `submitLegalQuery()` is typed and ready but not yet wired to the UI.
7. **Middleware deprecation warning** — Next.js 16 warns about the `middleware.ts` convention being deprecated in favor of `proxy`. This is a pre-existing warning and NOT introduced by Phase 11.

---

## 16. Next-Phase Dependencies

Phase 12+ must address:

1. **User management backend endpoints** — before Admin Users UI can be real
2. **Audit log backend endpoint** — before Admin Audit UI can be real
3. **Validation backend endpoints** — before Admin Validation Queue can be real
4. **Research pipeline wiring** — connect `submitLegalQuery()` to User Portal research flow
5. **Research history & saved research backend endpoints** — before History/Saved tabs are real
6. **Neo4j graph HTTP endpoints** — before Admin Graph Canvas can visualize real graph data
7. **Settings backend endpoint** (non-secret metadata only) — before Admin Settings can persist
8. **Extended health endpoints** (Neo4j, FAISS, LLM) — before dashboard shows complete system status
