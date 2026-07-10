from fastapi import HTTPException
from ..repositories.user_repository import UserRepository
from ..core.security import verify_password, create_access_token

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def login(self, username, password):
        user = self.user_repo.get_user_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
        
        token = create_access_token(data={"sub": user.username, "role": str(user.role_id)})
        return {"access_token": token, "token_type": "bearer"}