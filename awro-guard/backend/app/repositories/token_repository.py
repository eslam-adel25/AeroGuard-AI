from sqlalchemy.orm import Session
from ..models.models import RefreshToken, EmailVerificationToken
from datetime import datetime

class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_refresh_token(self, token_obj: RefreshToken):
        self.db.add(token_obj)
        self.db.commit()
        self.db.refresh(token_obj)
        return token_obj

    def get_refresh_token(self, token: str):
        return self.db.query(RefreshToken).filter(RefreshToken.token == token).first()

    def revoke_refresh_token(self, token: str):
        rt = self.get_refresh_token(token)
        if rt:
            rt.revoked = True
            self.db.commit()
            return True
        return False

    def create_email_verification(self, ev: EmailVerificationToken):
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def get_email_verification(self, token: str):
        return self.db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()

    def delete_email_verification(self, token_id):
        ev = self.db.query(EmailVerificationToken).filter(EmailVerificationToken.token_id == token_id).first()
        if ev:
            self.db.delete(ev)
            self.db.commit()
            return True
        return False
