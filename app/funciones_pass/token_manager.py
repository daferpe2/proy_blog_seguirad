from datetime import datetime, timedelta, timezone
from fastapi import HTTPException,status
from jose import ExpiredSignatureError, jwt, JWTError
import uuid


class TokenManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 45):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
        self.revoked_tokens = set()  # Almacena los jti revocados

    def create_token(self, payload: dict) -> str:
        jti = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.expire_minutes)
        token_data = {
            **payload,
            "jti": jti,
            "iat": now,
            "exp": expire
        }
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

    def invalidate_token(self, token: str):
        decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        jti = decoded.get("jti")
        self.revoked_tokens.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        return jti in self.revoked_tokens