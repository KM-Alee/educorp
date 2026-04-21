#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://localhost"
SEARCH_QUERY = "javascript"
STUDENT_EMAIL = "student@educorp.dev"
STUDENT_PASSWORD = "StudentPass123!"


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


def login() -> str:
    status, payload = request(
        "POST",
        "/api/v1/auth/login",
        body={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )
    if status != 200:
        raise RuntimeError(f"login failed: {status} {payload}")
    return payload["data"]["access_token"]


def main() -> None:
    token = login()

    status, search = request(
        "GET",
        f"/api/v1/search/courses?q={SEARCH_QUERY}",
        token=token,
    )
    if status != 200 or not search.get("data"):
        raise RuntimeError(f"no searchable courses available: {status} {search}")
    course_id = search["data"][0]["course_id"]

    status, enroll = request(
        "POST",
        "/api/v1/enrollments/",
        body={"course_id": course_id, "idempotency_key": f"phase4-{course_id}"},
        token=token,
    )
    if status not in {200, 201}:
        raise RuntimeError(f"enrollment failed: {status} {enroll}")
    enrollment_id = enroll["data"]["id"]

    status, progress = request("GET", f"/api/v1/progress/enrollments/{enrollment_id}", token=token)
    if status != 200:
        raise RuntimeError(f"progress load failed: {status} {progress}")

    certificate_id: str | None = None
    for module in progress["data"]["modules"]:
        status, completion = request(
            "POST",
            f"/api/v1/progress/enrollments/{enrollment_id}/modules/{module['module_id']}/complete",
            token=token,
        )
        if status != 200:
            raise RuntimeError(f"module completion failed: {status} {completion}")
        certificate = completion["data"].get("certificate")
        if certificate:
            certificate_id = certificate["id"]

    status, dashboard = request("GET", "/api/v1/progress/dashboard", token=token)
    if status != 200 or dashboard["data"]["completed_courses"] < 1:
        raise RuntimeError(f"dashboard completion missing: {status} {dashboard}")

    status, certificates = request("GET", "/api/v1/progress/certificates", token=token)
    if status != 200 or not certificates["data"]:
        raise RuntimeError(f"certificate list missing: {status} {certificates}")

    certificate_id = certificate_id or certificates["data"][0]["id"]
    status, certificate = request(
        "GET", f"/api/v1/progress/certificates/{certificate_id}", token=token
    )
    if status != 200:
        raise RuntimeError(f"certificate detail missing: {status} {certificate}")

    print("Phase 4 smoke passed")
    print(
        json.dumps(
            {
                "course_id": course_id,
                "enrollment_id": enrollment_id,
                "certificate_id": certificate_id,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Phase 4 smoke failed: {exc}", file=sys.stderr)
        raise
