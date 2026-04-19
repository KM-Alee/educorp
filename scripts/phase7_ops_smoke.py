#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost"
PROMETHEUS_URL = "http://localhost:9090"
ADMIN_EMAIL = "admin@educorp.dev"
ADMIN_PASSWORD = "AdminPass123!"


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
            payload = json.loads(response.read()) if response.length != 0 else {}
            return response.status, payload, dict(response.headers)
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read())
        return exc.code, payload, dict(exc.headers)


def request_absolute(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read())
            return response.status, payload, dict(response.headers)
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read())
        return exc.code, payload, dict(exc.headers)


def login() -> str:
    status, payload, _headers = request(
        "POST",
        "/api/v1/auth/login",
        body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if status != 200:
        raise RuntimeError(f"admin login failed: {status} {payload}")
    return payload["data"]["access_token"]


def main() -> None:
    token = login()

    checks: dict[str, object] = {}
    endpoints = {
        "auth_ready": "/api/v1/auth/health/ready",
        "course_ready": "/api/v1/courses/health/ready",
        "search_ready": "/api/v1/search/health/ready",
        "ai_ready": "/api/v1/ai/health/ready",
        "notification_ready": "/api/v1/notifications/health/ready",
        "analytics_ready": "/api/v1/analytics/health/ready",
    }
    for name, path in endpoints.items():
        status, payload, headers = request("GET", path, token=token)
        if status not in {200, 503}:
            raise RuntimeError(f"unexpected readiness response for {path}: {status} {payload}")
        if "X-Correlation-Id" not in headers:
            raise RuntimeError(f"missing correlation header for {path}")
        checks[name] = payload

    status, _payload, headers = request("GET", "/api/v1/search/courses?q=python", token=token)
    if status != 200:
        raise RuntimeError(f"catalog smoke failed: {status}")
    if headers.get("X-Frame-Options") != "DENY":
        raise RuntimeError("missing security headers on search response")

    admin_paths = {
        "audit_log": "/api/v1/admin/audit-log?page=1&page_size=5",
        "workflows": "/api/v1/admin/workflows?page=1&page_size=5",
        "dlq": "/api/v1/admin/dlq?page=1&page_size=5",
        "platform_analytics": "/api/v1/analytics/platform?from_date=2026-04-19&to_date=2026-04-19",
    }
    for name, path in admin_paths.items():
        status, payload, _headers = request("GET", path, token=token)
        if status != 200:
            raise RuntimeError(f"admin path failed for {path}: {status} {payload}")
        checks[name] = payload.get("data", payload)

    status, payload, _headers = request_absolute(f"{PROMETHEUS_URL}/api/v1/rules")
    if status != 200:
        raise RuntimeError(f"prometheus rules endpoint failed: {status} {payload}")
    group_names = [group["name"] for group in payload.get("data", {}).get("groups", [])]
    if "educorp-availability" not in group_names:
        raise RuntimeError("Prometheus alert groups were not loaded")
    checks["prometheus_rule_groups"] = group_names

    print("Phase 7 ops smoke passed")
    print(json.dumps(checks))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Phase 7 ops smoke failed: {exc}", file=sys.stderr)
        raise
