from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import session as database_session


def test_application_starts_with_an_isolated_database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    isolated_sessions = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(database_session, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", isolated_sessions)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    try:
        with TestClient(main.create_app()) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            assert response.json()["info"]["title"] == "AeroGuard AI API"
    finally:
        engine.dispose()
