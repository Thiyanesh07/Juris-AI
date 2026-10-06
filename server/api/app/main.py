"""Application entry point. Routers live under app.api.routes."""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.graph import router as graph_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.qa import router as qa_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.saved_research import router as saved_research_router
from app.api.routes.settings import router as settings_router
from app.api.routes.validation import router as validation_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Juris AI LegalGraph API",
    description="Indian legal research platform powered by GraphRAG and hybrid search.",
    version="0.6.1",
)

extra_origins_str = getattr(settings, "extra_cors_origins", "") or ""
frontend_url_str = getattr(settings, "frontend_url", "http://localhost:5173") or ""

raw_origins = [
    frontend_url_str,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:5173",
    "https://juris-ai-landing-ten.vercel.app",
    "https://juris-ai-user.vercel.app",
    "https://juris-ai-admin.vercel.app",
    *(o for o in extra_origins_str.split(",") if o.strip()),
]

allowed_origins = list({
    origin.strip().strip("'\"").rstrip("/")
    for origin in raw_origins
    if origin and origin.strip()
})


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="legalgraph_session",
    max_age=settings.session_max_age_seconds,
    same_site="none" if settings.session_cookie_secure else "lax",
    https_only=settings.session_cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Standard root routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(qa_router)
app.include_router(evaluation_router)
app.include_router(validation_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(graph_router)
app.include_router(history_router)
app.include_router(saved_research_router)

# Compatibility /api/v1 router prefix
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(admin_users_router)
v1_router.include_router(documents_router)
v1_router.include_router(retrieval_router)
v1_router.include_router(qa_router)
v1_router.include_router(evaluation_router)
v1_router.include_router(validation_router)
v1_router.include_router(audit_router)
v1_router.include_router(settings_router)
v1_router.include_router(graph_router)
v1_router.include_router(history_router)
v1_router.include_router(saved_research_router)
app.include_router(v1_router)
