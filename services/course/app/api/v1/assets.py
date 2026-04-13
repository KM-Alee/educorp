from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from miniopy_async import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_minio,
    get_session,
    require_roles,
)
from app.schemas.asset import AssetDownload, AssetOut
from app.services.asset_service import AssetService
from app.services.storage_service import StorageService
from educorp_common.errors import ValidationError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["assets"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _to_out(asset) -> AssetOut:
    return AssetOut(
        id=asset.id,
        module_id=asset.module_id,
        title=asset.title,
        asset_type=asset.asset_type,
        file_name=asset.file_name,
        file_size=asset.file_size,
        mime_type=asset.mime_type,
        storage_path=asset.storage_path,
        checksum=asset.checksum,
        sort_order=asset.sort_order,
        upload_status=asset.upload_status,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.post(
    "/{course_id}/modules/{module_id}/assets/upload",
    response_model=SuccessResponse[AssetOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    course_id: UUID,
    module_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    sort_order: int | None = Form(default=None),
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
    minio_client: Minio = Depends(get_minio),
) -> SuccessResponse[AssetOut]:
    data = await file.read()
    if len(data) > settings.max_asset_size_bytes:
        max_mb = settings.max_asset_size_bytes / (1024 * 1024)
        raise ValidationError(f"File exceeds maximum size of {max_mb:.0f} MB")

    storage = StorageService(minio_client)
    svc = AssetService(session, storage)
    asset = await svc.upload(
        course_id=course_id,
        module_id=module_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
        file_name=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        title=title,
        sort_order=sort_order,
    )
    await session.commit()
    return SuccessResponse(data=_to_out(asset), meta=_meta())


@router.get(
    "/{course_id}/modules/{module_id}/assets",
    response_model=SuccessResponse[list[AssetOut]],
)
async def list_assets(
    course_id: UUID,
    module_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio_client: Minio = Depends(get_minio),
) -> SuccessResponse[list[AssetOut]]:
    storage = StorageService(minio_client)
    svc = AssetService(session, storage)
    assets = await svc.list_for_module(course_id=course_id, module_id=module_id)
    return SuccessResponse(data=[_to_out(a) for a in assets], meta=_meta())


@router.get(
    "/{course_id}/modules/{module_id}/assets/{asset_id}/download",
    response_model=SuccessResponse[AssetDownload],
)
async def download_asset(
    course_id: UUID,
    module_id: UUID,
    asset_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio_client: Minio = Depends(get_minio),
) -> SuccessResponse[AssetDownload]:
    storage = StorageService(minio_client)
    svc = AssetService(session, storage)
    url = await svc.presigned_download(
        course_id=course_id,
        module_id=module_id,
        asset_id=asset_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    return SuccessResponse(
        data=AssetDownload(
            download_url=url,
            expires_in=settings.presigned_url_ttl_seconds,
        ),
        meta=_meta(),
    )


@router.delete(
    "/{course_id}/modules/{module_id}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_asset(
    course_id: UUID,
    module_id: UUID,
    asset_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
    minio_client: Minio = Depends(get_minio),
) -> None:
    storage = StorageService(minio_client)
    svc = AssetService(session, storage)
    await svc.delete(
        course_id=course_id,
        module_id=module_id,
        asset_id=asset_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    await session.commit()
