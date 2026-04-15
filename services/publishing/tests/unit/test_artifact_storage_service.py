from __future__ import annotations

import hashlib

from app.services.artifact_storage_service import canonical_json_bytes


def test_canonical_json_bytes_are_stable_for_key_order() -> None:
    first = canonical_json_bytes(
        {
            "course_id": "course-1",
            "modules": [{"id": "m1", "title": "Intro", "sort_order": 0}],
            "title": "Course",
        }
    )
    second = canonical_json_bytes(
        {
            "title": "Course",
            "modules": [{"sort_order": 0, "title": "Intro", "id": "m1"}],
            "course_id": "course-1",
        }
    )

    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
