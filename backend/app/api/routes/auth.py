from fastapi import APIRouter, HTTPException

from app.auth.security import create_access_token
from app.models.schemas import TokenResponse, UserLogin, UserSignup
from app.services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: UserSignup):
    try:
        user = UserService().create_user(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = create_access_token(user["user_id"])
    return TokenResponse(access_token=token, user_id=user["user_id"], email=user["email"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    user = UserService().authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token(user["user_id"])
    return TokenResponse(access_token=token, user_id=user["user_id"], email=user["email"])
