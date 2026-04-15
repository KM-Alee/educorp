from __future__ import annotations

import asyncio
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from miniopy_async import Minio

from app.config import settings


@dataclass(frozen=True)
class StoredArtifact:
    object_path: str
    sha256: str
    size_bytes: int
    content_type: str = "application/json"


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        default=_json_default,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class ArtifactStorageService:
    def __init__(self, minio_client: Minio) -> None:
        self._minio = minio_client

    async def put_json(self, object_path: str, payload: Any) -> StoredArtifact:
        data = canonical_json_bytes(payload)
        await self._minio.put_object(
            settings.minio_bucket,
            object_path,
            io.BytesIO(data),
            length=len(data),
            content_type="application/json",
        )
        return StoredArtifact(
            object_path=object_path,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )

    async def get_json(self, object_path: str) -> Any:
        data = await read_object(self._minio, object_path)
        return json.loads(data.decode("utf-8"))


async def read_object(client: Minio, object_path: str) -> bytes:
    response = await client.get_object(settings.minio_bucket, object_path)
    data = response.read() if hasattr(response, "read") else response
    if asyncio.iscoroutine(data):
        data = await data
    if hasattr(response, "close"):
        maybe_close = response.close()
        if asyncio.iscoroutine(maybe_close):
            await maybe_close
    return data


def _json_default(value: Any) -> str:
    if isinstance(value, (UUID, datetime)):
        return str(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")
