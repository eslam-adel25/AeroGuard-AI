from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.session import engine, Base
from .api.v1 import auth, cameras, users, reports, settings, websocket_api, ai
from .ai.processor import ai_engine
import logging

logging.basicConfig(level=logging.INFO)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AeroGuard AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الربط الصحيح لجميع المسارات بـ Prefix واحد (api/v1)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(websocket_api.router) # الـ WebSocket غالباً لا يحتاج بريفيكس
app.include_router(ai.router, prefix="/api/v1")