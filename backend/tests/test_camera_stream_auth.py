from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth_middleware import get_current_user
from app.core.security import create_access_token


app = FastAPI()


@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)):
    return {"ok": True, "user_id": user.get("user_id")}


def test_get_current_user_accepts_token_query_param():
    client = TestClient(app)
    token = create_access_token({"user_id": "user-1", "role": "Administrator"})

    response = client.get(f"/protected?token={token}")

    assert response.status_code == 200
    assert response.json()["ok"] is True
