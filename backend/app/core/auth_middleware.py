from fastapi import HTTPException, Depends, Header
from .security import verify_token # دالة افتراضية للتحقق من التوكن
from uuid import UUID

async def get_current_user(authorization: str = Header(None), token: str | None = None):
    """استخراج المستخدم من عنوان الـ Header أو من بارامتر الاستعلام token."""
    bearer_token = None
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    if not bearer_token and token:
        bearer_token = token

    if not bearer_token:
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")

    payload = verify_token(bearer_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    if isinstance(user_id, str):
        try:
            payload["user_id"] = UUID(user_id)
        except ValueError:
            pass

    return payload


def role_required(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        # التحقق من الرتبة القادمة من التوكن المفكوك بواسطة get_current_user
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للقيام بهذا الإجراء")
        return current_user
    return role_checker