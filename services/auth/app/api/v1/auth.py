from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_redis,
    get_session,
    require_roles,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    InstructorApplicationOut,
    InstructorApplicationRequest,
    LoginRequest,
    MessageOut,
    RefreshRequest,
    RefreshTokenResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    TokenUserOut,
    UpdateProfileRequest,
    UserCreatedOut,
    UserProfileOut,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.instructor_application_service import InstructorApplicationService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter()


def build_meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def request_context(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


@router.post(
    "/register",
    response_model=SuccessResponse[UserCreatedOut],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[UserCreatedOut]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    user = await service.register(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    data = UserCreatedOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=["student"],
        created_at=user.created_at,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[TokenResponse]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    access_token, refresh_token, expires_in, user, roles = await service.login(
        email=payload.email,
        password=payload.password,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    token_user = TokenUserOut(id=user.id, email=user.email, roles=roles)
    data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=token_user,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.post("/refresh", response_model=SuccessResponse[RefreshTokenResponse])
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[RefreshTokenResponse]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    access_token, refresh_token, expires_in = await service.refresh(
        refresh_token=payload.refresh_token,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    data = RefreshTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.post("/verify-email", response_model=SuccessResponse[MessageOut])
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[MessageOut]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    await service.verify_email(
        token=payload.token,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return SuccessResponse(
        data=MessageOut(message="Email verified successfully"), meta=build_meta()
    )


@router.post("/forgot-password", response_model=SuccessResponse[MessageOut])
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[MessageOut]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    await service.forgot_password(
        email=payload.email,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return SuccessResponse(
        data=MessageOut(
            message="If the email exists, a password reset link has been sent"
        ),
        meta=build_meta(),
    )


@router.post("/reset-password", response_model=SuccessResponse[MessageOut])
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[MessageOut]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    await service.reset_password(
        token=payload.token,
        new_password=payload.new_password,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return SuccessResponse(
        data=MessageOut(message="Password reset successfully"), meta=build_meta()
    )


@router.get("/me", response_model=SuccessResponse[UserProfileOut])
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[UserProfileOut]:
    service = AuthService(session, redis)
    user = await service.get_profile(UUID(current_user["id"]))
    data = UserProfileOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=current_user["roles"],
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.patch("/me", response_model=SuccessResponse[UserProfileOut])
async def update_me(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> SuccessResponse[UserProfileOut]:
    service = AuthService(session, redis)
    ip_address, user_agent = request_context(request)
    user = await service.update_profile(
        user_id=UUID(current_user["id"]),
        first_name=payload.first_name,
        last_name=payload.last_name,
        avatar_url=payload.avatar_url,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    data = UserProfileOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=current_user["roles"],
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.post(
    "/instructor-application",
    response_model=SuccessResponse[InstructorApplicationOut],
    status_code=status.HTTP_201_CREATED,
)
async def instructor_application(
    payload: InstructorApplicationRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[InstructorApplicationOut]:
    service = InstructorApplicationService(session)
    ip_address, user_agent = request_context(request)
    application = await service.apply(
        user_id=UUID(current_user["id"]),
        reason=payload.reason,
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
        auto_approve=settings.instructor_auto_approve,
    )
    await session.commit()
    data = InstructorApplicationOut(
        id=application.id,
        status=application.status,
        created_at=application.created_at,
    )
    return SuccessResponse(data=data, meta=build_meta())
