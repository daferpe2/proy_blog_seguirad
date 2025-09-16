from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import uuid


class TokenManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 15):
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
            decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if self.is_token_revoked(decoded.get("jti")):
                raise JWTError("Token has been revoked")
            return decoded
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def invalidate_token(self, token: str):
        decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        jti = decoded.get("jti")
        self.revoked_tokens.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        return jti in self.revoked_tokens