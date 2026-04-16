from __future__ import annotations

from app.repositories.certificate_repository import CertificateRepository
from app.repositories.module_progress_repository import ModuleProgressRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.student_progress_repository import StudentProgressRepository

__all__ = [
	"CertificateRepository",
	"ModuleProgressRepository",
	"OutboxRepository",
	"StudentProgressRepository",
]
