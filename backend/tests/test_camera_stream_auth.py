from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth_middleware import get_current_user
from app.core.security import create_access_token
from app.database.session import Base, get_db
from app.models.models import Role, User


app = FastAPI()


@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)):
    return {
        "ok": True,
        "user_id": user.get("user_id"),
        "user_id_type": type(user.get("user_id")).__name__,
        "role": user.get("role"),
    }


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(role_name="Officer")
        user = User(
            full_name="Test User",
            username="test_user",
            email="test@example.com",
            password_hash="not-used",
            role=role,
            status="Active",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        user_id = str(user.user_id)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, user_id
    app.dependency_overrides.clear()
    engine.dispose()


def test_get_current_user_accepts_token_query_param(auth_client):
    client, user_id = auth_client
    token = create_access_token(
        {"user_id": user_id, "role": "Administrator"}
    )

    response = client.get(f"/protected?token={token}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["role"] == "Officer"


def test_current_user_converts_string_user_id_to_uuid(auth_client):
    client, user_id = auth_client
    token = create_access_token({"user_id": user_id, "role": "Administrator"})

    response = client.get(f"/protected?token={token}")
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["user_id_type"] == "UUID"
