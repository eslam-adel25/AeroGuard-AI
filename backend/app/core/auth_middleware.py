from fastapi import HTTPException, Depends, Header
from .security import verify_token # دالة افتراضية للتحقق من التوكن

async def get_current_user(authorization: str = Header(None)):
    """استخراج المستخدم من عنوان الـ Header (صفحة 135)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    return payload


def role_required(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        # التحقق من الرتبة القادمة من التوكن المفكوك بواسطة get_current_user
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للقيام بهذا الإجراء")
        return current_user
    return role_checker