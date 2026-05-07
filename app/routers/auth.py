from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EmotionalState, User
from app.schemas import LoginRequest, SignupRequest, TokenResponse
from app.services.auth import (
    TOKEN_BLACKLIST,
    create_access_token,
    decode_token,
    hash_password,
    pseudonymize,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    exists = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        pseudonym_id=pseudonymize(user_id),
    )
    db.add(user)
    db.add(EmotionalState(user_id=user_id, vector=[0.0, 0.0, 0.0, 0.0]))
    await db.commit()

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == form_data.username))).scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    """
    Invalidates an access token by adding its `jti` claim to the server-side blacklist.
    
    Parameters:
        token (str): The OAuth2 Bearer access token to invalidate.
    
    Returns:
        dict[str, str]: A confirmation dictionary containing `{'message': 'Logged out'}`.
    """
    payload = decode_token(token)
    TOKEN_BLACKLIST.add(payload["jti"])
    return {"message": "Logged out"}