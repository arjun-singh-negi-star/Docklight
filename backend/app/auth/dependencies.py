"""FastAPI dependency that resolves the current user from a Bearer JWT."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.services.user_service import UserService

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    user = UserService().get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
