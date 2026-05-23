from __future__ import annotations
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import User
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')
TOKEN_BLACKLIST: set[str] = set()

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt.

Args:
    password (str): The password to be hashed.

Returns:
    str: The hashed password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verifies if the provided password matches the given hash.

Args:
    password (str): The plaintext password to verify.
    password_hash (str): The hashed password to compare against.

Returns:
    bool: True if the passwords match, False otherwise."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def pseudonymize(user_id: uuid.UUID) -> str:
    """Generate a pseudonymized string from a user ID.

Args:
    user_id (uuid.UUID): The unique identifier of the user to be pseudonymized.

Returns:
    str: A pseudonymized string representing the user."""
    digest = hmac.new(settings.pseudonym_hmac_key.encode('utf-8'), str(user_id).encode('utf-8'), hashlib.sha256).hexdigest()
    return digest

def create_access_token(subject: str) -> str:
    """Generates a JWT access token for the given subject.

Args:
    subject (str): The subject of the token, typically a user identifier.

Returns:
    str: A JWT access token encoded with specified payload and secret."""
    now = datetime.now(timezone.utc)
    payload = {'sub': subject, 'jti': str(uuid.uuid4()), 'iat': int(now.timestamp()), 'exp': int((now + timedelta(minutes=settings.jwt_expires_minutes)).timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    """Decodes a JWT token and returns its payload.

Args:
    token (str): The JWT token to decode.

Returns:
    dict: The decoded payload of the token.

Raises:
    HTTPException: If the token is invalid or has been logged out."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get('jti') in TOKEN_BLACKLIST:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token has been logged out')
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

async def get_current_user(token: str=Depends(oauth2_scheme), db: AsyncSession=Depends(get_db)) -> User:
    """Fetches the current authenticated user based on the provided token.

Args:
    token (str): The authentication token.
    db (AsyncSession): The database session.

Returns:
    User: The authenticated user object if found.

Raises:
    HTTPException: If the user is not found."""
    payload = decode_token(token)
    user_id = payload.get('sub')
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user