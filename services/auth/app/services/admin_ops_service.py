from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from app.repositories.audit_log_repository import AuditLogRepository
from app.services.internal_ops_client import InternalOpsClient
from educorp_common.errors import NotFoundError


class AdminOpsService:
    def __init__(self, session) -> None:
        self._audit_logs = AuditLogRepository(session)
        self._internal = InternalOpsClient()

    async def list_audit_log(
        self,
        *,
        page: int,
        page_size: int,
        actor_id: UUID | None,
        action: str | None,
        resource_type: str | None,
        resource_id: UUID | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[list[dict], int]:
        auth_rows, auth_total = await self._audit_logs.list_entries(
            page=1,
            page_size=max(page * page_size, 100),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            from_date=from_date,
            to_date=to_date,
        )
        enrollment_payload = await self._internal.list_enrollment_audit(
            params=self._audit_params(
                page=1,
                page_size=max(page * page_size, 100),
                actor_id=actor_id,
                action=action,
                from_date=from_date,
                to_date=to_date,
            )
        )
        enrollment_rows = enrollment_payload.get("data", [])

        combined = [
            {
                "id": str(row.id),
                "source": "auth",
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "actor_type": row.actor_type,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": str(row.resource_id) if row.resource_id else None,
                "details": row.new_value or row.old_value or {},
                "correlation_id": str(row.correlation_id) if row.correlation_id else None,
                "created_at": row.created_at,
            }
            for row in auth_rows
        ]
        combined.extend(
            {
                "id": item["id"],
                "source": "enrollment",
                "actor_id": item.get("actor_id"),
                "actor_type": "user",
                "action": item["action"],
                "resource_type": "enrollment",
                "resource_id": item["enrollment_id"],
                "details": item.get("details", {}),
                "correlation_id": item.get("correlation_id"),
                "created_at": datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
            }
            for item in enrollment_rows
        )
        if resource_type and resource_type != "enrollment":
            combined = [row for row in combined if row["source"] == "auth"]
        if resource_id is not None:
            combined = [row for row in combined if row.get("resource_id") == str(resource_id)]
        combined.sort(key=lambda row: row["created_at"], reverse=True)
        total = len(combined)
        start = (page - 1) * page_size
        end = start + page_size
        return combined[start:end], total

    async def list_workflows(self, *, params: dict[str, str]) -> dict:
        return await self._internal.list_workflows(params=params)

    async def get_workflow(self, workflow_id: str) -> dict:
        return await self._internal.get_workflow(workflow_id)

    async def retry_workflow(self, workflow_id: str) -> dict:
        return await self._internal.retry_workflow(workflow_id)

    async def list_dead_letters(
        self, *, topic: str | None, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        params = {"page": "1", "page_size": str(max(page * page_size, 100))}
        if topic:
            params["topic"] = topic

        notification = await self._internal.list_notification_dlq(params=params)
        analytics = await self._internal.list_analytics_dlq(params=params)
        rows = [{**item, "source": "notification"} for item in notification.get("data", [])]
        rows.extend({**item, "source": "analytics"} for item in analytics.get("data", []))
        rows.sort(
            key=lambda row: datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            reverse=True,
        )
        total = int(notification.get("pagination", {}).get("total_items", 0)) + int(
            analytics.get("pagination", {}).get("total_items", 0)
        )
        start = (page - 1) * page_size
        end = start + page_size
        return rows[start:end], total

    async def replay_dead_letter(self, *, source: str, message_id: str) -> dict:
        if source == "notification":
            return await self._internal.replay_notification_dlq(message_id)
        if source == "analytics":
            return await self._internal.replay_analytics_dlq(message_id)
        raise NotFoundError("Dead-letter source not found")

    @staticmethod
    def _audit_params(
        *,
        page: int,
        page_size: int,
        actor_id: UUID | None,
        action: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> dict[str, str]:
        params = {"page": str(page), "page_size": str(page_size)}
        if actor_id is not None:
            params["actor_id"] = str(actor_id)
        if action:
            params["action"] = action
        if from_date is not None:
            params["from_date"] = from_date.astimezone(timezone.utc).isoformat()
        if to_date is not None:
            params["to_date"] = to_date.astimezone(timezone.utc).isoformat()
        return params


def parse_date_bounds(
    from_date: str | None, to_date: str | None
) -> tuple[datetime | None, datetime | None]:
    start = None
    end = None
    if from_date:
        start = datetime.combine(
            datetime.fromisoformat(from_date).date(), time.min, tzinfo=timezone.utc
        )
    if to_date:
        end = datetime.combine(
            datetime.fromisoformat(to_date).date(), time.max, tzinfo=timezone.utc
        )
    return start, end
