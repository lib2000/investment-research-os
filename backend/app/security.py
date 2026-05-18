from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.settings import Settings, get_settings


def verify_user_token(
    authorization: Optional[str] = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증되지 않은 사용자입니다.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.dev_user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증되지 않은 사용자입니다.",
        )
