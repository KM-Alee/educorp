from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("PHASE1_BASE_URL", "http://localhost/api/v1/auth")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@educorp.dev")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AdminPass123!")


def fail(label: str, message: str, body: object | None = None) -> None:
    print(f"FAIL {label}: {message}")
    if body is not None:
        print(body)
    raise SystemExit(1)


def request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
    expected: int,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read().decode("utf-8")
    except Exception as error:  # noqa: BLE001
        fail(path, f"request error: {error}")

    parsed = json.loads(body)
    if status != expected:
        fail(path, f"expected {expected}, got {status}", parsed)

    print(f"PASS {path} ({status})")
    return parsed


def query_sql(sql: str) -> str:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "educorp",
            "-d",
            "educorp",
            "-Atc",
            sql,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    stamp = int(time.time())
    test_email = f"phase1-{stamp}@example.com"
    test_password = "TestPass123!"
    new_password = "ResetPass456!"

    request("GET", "/health/ready", expected=200)

    admin_login = request(
        "POST",
        "/login",
        payload={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        expected=200,
    )
    admin_access = admin_login["data"]["access_token"]

    request("GET", "/me", token=admin_access, expected=200)

    register = request(
        "POST",
        "/register",
        payload={
            "email": test_email,
            "password": test_password,
            "first_name": "Phase",
            "last_name": "Tester",
        },
        expected=201,
    )
    user_id = register["data"]["id"]

    request(
        "POST",
        "/login",
        payload={"email": test_email, "password": test_password},
        expected=403,
    )

    verify_token = query_sql(
        f"SELECT payload->'data'->>'token' FROM auth.outbox WHERE event_type = 'user.created' AND payload->'data'->>'email' = '{test_email}' ORDER BY created_at DESC LIMIT 1;"
    )
    if not verify_token:
        fail("verify_token", "token missing from outbox")
    print("PASS verify_token_extracted")

    request("POST", "/verify-email", payload={"token": verify_token}, expected=200)

    user_login = request(
        "POST",
        "/login",
        payload={"email": test_email, "password": test_password},
        expected=200,
    )
    user_access = user_login["data"]["access_token"]
    user_refresh = user_login["data"]["refresh_token"]

    refresh = request(
        "POST",
        "/refresh",
        payload={"refresh_token": user_refresh},
        expected=200,
    )
    user_access = refresh["data"]["access_token"]

    request("GET", "/me", token=user_access, expected=200)

    request("POST", "/forgot-password", payload={"email": test_email}, expected=200)
    reset_token = query_sql(
        f"SELECT payload->'data'->>'token' FROM auth.outbox WHERE event_type = 'user.password_reset_requested' AND payload->'data'->>'email' = '{test_email}' ORDER BY created_at DESC LIMIT 1;"
    )
    if not reset_token:
        fail("reset_token", "token missing from outbox")
    print("PASS reset_token_extracted")

    request(
        "POST",
        "/reset-password",
        payload={"token": reset_token, "new_password": new_password},
        expected=200,
    )

    user_login = request(
        "POST",
        "/login",
        payload={"email": test_email, "password": new_password},
        expected=200,
    )
    user_access = user_login["data"]["access_token"]

    application = request(
        "POST",
        "/instructor-application",
        payload={"reason": "I want to teach secure backend delivery."},
        token=user_access,
        expected=201,
    )
    application_id = application["data"]["id"]

    request("GET", "/admin/users", token=admin_access, expected=200)
    request(
        "PATCH",
        f"/admin/users/{user_id}/roles",
        payload={"add_roles": ["admin"], "remove_roles": []},
        token=admin_access,
        expected=200,
    )
    request(
        "PATCH",
        f"/admin/users/{user_id}/roles",
        payload={"add_roles": [], "remove_roles": ["admin"]},
        token=admin_access,
        expected=200,
    )
    request(
        "PATCH",
        f"/admin/users/{user_id}/status",
        payload={"is_active": False},
        token=admin_access,
        expected=200,
    )
    request(
        "POST",
        "/login",
        payload={"email": test_email, "password": new_password},
        expected=403,
    )
    request(
        "PATCH",
        f"/admin/users/{user_id}/status",
        payload={"is_active": True},
        token=admin_access,
        expected=200,
    )
    request("GET", "/admin/instructor-applications", token=admin_access, expected=200)
    request(
        "PATCH",
        f"/admin/instructor-applications/{application_id}",
        payload={"status": "APPROVED"},
        token=admin_access,
        expected=200,
    )

    audit_count = int(query_sql("SELECT COUNT(*) FROM auth.audit_log;"))
    outbox_count = int(query_sql("SELECT COUNT(*) FROM auth.outbox;"))
    instructor_rows = int(
        query_sql(
            f"SELECT COUNT(*) FROM auth.user_roles ur JOIN auth.roles r ON ur.role_id = r.id WHERE ur.user_id = '{user_id}' AND r.name = 'instructor';"
        )
    )

    if audit_count <= 0:
        fail("audit_log", "no audit rows recorded")
    if outbox_count <= 0:
        fail("outbox", "no outbox rows recorded")
    if instructor_rows <= 0:
        fail("instructor_role", "approved application did not grant instructor role")

    print(f"PASS audit_log_present count={audit_count}")
    print(f"PASS outbox_present count={outbox_count}")
    print(f"PASS instructor_role_after_review count={instructor_rows}")
    print(
        f"SUMMARY user_id={user_id} application_id={application_id} email={test_email}"
    )


if __name__ == "__main__":
    main()