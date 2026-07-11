from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from .database.session import engine, Base, _ensure_schema_compatibility
from .api.v1 import auth, cameras, users, reports, settings, websocket_api, ai
from .ai.processor import ai_engine
import logging
import os

logging.basicConfig(level=logging.INFO)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_ROOT = BACKEND_ROOT / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    app = FastAPI(title="AeroGuard AI API")
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

    @app.on_event("startup")
    def startup_event() -> None:
        Base.metadata.create_all(bind=engine)
        _ensure_schema_compatibility()

    return app


app = create_app()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# الربط الصحيح لجميع المسارات بـ Prefix واحد (api/v1)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(websocket_api.router) # الـ WebSocket غالباً لا يحتاج بريفيكس
app.include_router(ai.router, prefix="/api/v1")


def _resolve_bind_host() -> str:
    configured_host = (os.getenv("HOST") or "127.0.0.1").strip()
    if configured_host in {"", "0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return configured_host


if __name__ == "__main__":
    import uvicorn

    host = _resolve_bind_host()
    port = int(os.getenv("PORT", "8000"))

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=False,
        )
    except OSError as exc:
        if host != "127.0.0.1" and ("10013" in str(exc) or "permission" in str(exc).lower()):
            print(f"⚠️ Bind failed for {host}:{port}: {exc}. Retrying on 127.0.0.1.")
            uvicorn.run(
                "app.main:app",
                host="127.0.0.1",
                port=port,
                reload=False,
            )
        else:
            raise
