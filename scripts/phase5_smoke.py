#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://localhost"
STUDENT_EMAIL = "student@educorp.dev"
STUDENT_PASSWORD = "StudentPass123!"
INSTRUCTOR_EMAIL = "instructor@educorp.dev"
INSTRUCTOR_PASSWORD = "InstructorPass123!"


def request(method: str, path: str, *, body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read())
            return response.status, payload
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read())
        return exc.code, payload


def login(email: str, password: str) -> str:
    status, payload = request(
        "POST",
        "/api/v1/auth/login",
        body={"email": email, "password": password},
    )
    if status != 200:
        raise RuntimeError(f"login failed for {email}: {status} {payload}")
    return payload["data"]["access_token"]


def main() -> None:
    student_token = login(STUDENT_EMAIL, STUDENT_PASSWORD)
    instructor_token = login(INSTRUCTOR_EMAIL, INSTRUCTOR_PASSWORD)

    status, search = request("GET", "/api/v1/search/courses?q=python", token=student_token)
    if status != 200 or not search.get("data"):
        raise RuntimeError(f"no searchable courses available: {status} {search}")
    course_id = search["data"][0]["course_id"]

    request(
        "POST",
        "/api/v1/enrollments/",
        body={"course_id": course_id, "idempotency_key": f"phase5-{course_id}"},
        token=student_token,
    )

    status, answer = request(
        "POST",
        "/api/v1/ai/ask",
        body={"course_id": course_id, "question": "Summarize the first module."},
        token=student_token,
    )
    if status != 200 or answer["data"]["response_type"] not in {"answer", "clarification"}:
        raise RuntimeError(f"AI ask failed: {status} {answer}")

    status, job = request(
        "POST",
        "/api/v1/ai/instructor/enhance",
        body={"course_id": course_id, "job_type": "summary", "scope": "course", "parameters": {}},
        token=instructor_token,
    )
    if status != 202:
        raise RuntimeError(f"AI instructor job failed: {status} {job}")

    print("Phase 5 smoke passed")
    print(
        json.dumps(
            {
                "course_id": course_id,
                "query_id": answer["data"]["query_id"],
                "job_id": job["data"]["job_id"],
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Phase 5 smoke failed: {exc}", file=sys.stderr)
        raise
