#!/usr/bin/env python3
"""
Seed development data for EduCorp via the HTTP API.

Usage:
    python scripts/seed_data.py [--gateway http://localhost]

This script calls the live API to create users and courses, so all
services must be running first (run-app.sh or docker compose up).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

USERS_TO_SEED = [
    {
        "email": "instructor@educorp.dev",
        "password": "InstructorPass123!",
        "first_name": "Jane",
        "last_name": "Instructor",
        "promote_to_instructor": True,
    },
    {
        "email": "student@educorp.dev",
        "password": "StudentPass123!",
        "first_name": "John",
        "last_name": "Student",
        "promote_to_instructor": False,
    },
]

COURSES = [
    {
        "title": "Introduction to Python",
        "description": (
            "A comprehensive introduction to Python programming. "
            "Covers basic syntax, data structures, functions, and OOP."
        ),
        "short_description": "Learn Python from scratch with hands-on exercises.",
        "category": "Programming",
        "difficulty": "beginner",
        "estimated_duration": "PT8H",
        "tags": ["python", "programming", "beginner"],
        "modules": [
            "Getting Started with Python",
            "Variables and Data Types",
            "Control Flow",
            "Functions and Modules",
        ],
    },
    {
        "title": "Advanced FastAPI",
        "description": (
            "Master FastAPI for building high-performance APIs. "
            "Topics: dependency injection, async patterns, auth, deployment."
        ),
        "short_description": "Build production-ready APIs with FastAPI.",
        "category": "Web Development",
        "difficulty": "advanced",
        "estimated_duration": "PT12H",
        "tags": ["python", "fastapi", "api", "advanced"],
        "modules": [
            "FastAPI Fundamentals",
            "Dependency Injection Deep Dive",
            "Authentication & Security",
            "Testing FastAPI Applications",
            "Deployment Strategies",
        ],
    },
    {
        "title": "React for Beginners",
        "description": (
            "Learn to build modern web applications with React 19. "
            "Covers components, hooks, state management, and routing."
        ),
        "short_description": "Build interactive UIs with React.",
        "category": "Web Development",
        "difficulty": "beginner",
        "estimated_duration": "PT10H",
        "tags": ["react", "javascript", "frontend", "beginner"],
        "modules": [
            "Introduction to React",
            "Components and Props",
            "State and Hooks",
            "React Router and Navigation",
        ],
    },
    {
        "title": "Database Design with PostgreSQL",
        "description": (
            "Learn relational database design and PostgreSQL. "
            "Schema design, indexing, query optimisation, migrations."
        ),
        "short_description": "Master PostgreSQL for production systems.",
        "category": "Databases",
        "difficulty": "intermediate",
        "estimated_duration": "PT6H",
        "tags": ["postgresql", "sql", "databases", "intermediate"],
        "modules": [
            "Relational Design Principles",
            "Advanced SQL Techniques",
            "Indexing and Performance",
        ],
    },
]


def _request(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_bytes = exc.read()
        try:
            payload = json.loads(body_bytes)
        except Exception:
            payload = {"raw": body_bytes.decode(errors="replace")}
        return exc.code, payload


def login(gateway: str, email: str, password: str) -> str | None:
    status, payload = _request("POST", f"{gateway}/api/v1/auth/login", {"email": email, "password": password})
    if status == 200 and "data" in payload:
        return payload["data"]["access_token"]
    return None


def main(gateway: str) -> None:
    print("=== EduCorp Seed Data ===\n")
    print(f"Gateway: {gateway}\n")

    # ── 1. Seed admin via existing script inside container ──────────────
    print("Step 1 — Ensure admin user exists")
    print("  Run:  docker compose exec auth-service python scripts/seed.py")
    print("  (skipping here; admin seed is handled by the service container)\n")

    # ── 2. Login as admin ───────────────────────────────────────────────
    print("Step 2 — Login as admin")
    admin_token = login(gateway, "admin@educorp.dev", "AdminPass123!")
    if not admin_token:
        print("  ERROR: Could not login as admin@educorp.dev / AdminPass123!")
        print("  Run the auth seed first:  docker compose exec auth-service python scripts/seed.py")
        sys.exit(1)
    print("  OK\n")

    # ── 3. Create additional users ──────────────────────────────────────
    print("Step 3 — Create instructor and student accounts")
    created_users: dict[str, str] = {}
    for u in USERS_TO_SEED:
        status, payload = _request(
            "POST",
            f"{gateway}/api/v1/auth/register",
            {
                "email": u["email"],
                "password": u["password"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
            },
        )
        if status == 201:
            user_id = payload["data"]["id"]
            created_users[u["email"]] = user_id
            print(f"  Created: {u['email']}")
        elif status == 409 or (status == 400 and "already" in str(payload)):
            # Get user id by logging in
            tok = login(gateway, u["email"], u["password"])
            if tok:
                s2, p2 = _request("GET", f"{gateway}/api/v1/auth/me", token=tok)
                if s2 == 200:
                    created_users[u["email"]] = p2["data"]["id"]
            print(f"  Exists:  {u['email']}")
        else:
            print(f"  WARN: could not create {u['email']}: {status} {payload}")

        # Grant instructor role if needed
        if u.get("promote_to_instructor") and u["email"] in created_users:
            uid = created_users[u["email"]]
            s3, p3 = _request(
                "PATCH",
                f"{gateway}/api/v1/auth/admin/users/{uid}/roles",
                {"add_roles": ["instructor"], "remove_roles": []},
                token=admin_token,
            )
            if s3 == 200:
                print(f"    Granted instructor role to {u['email']}")
            else:
                print(f"    WARN: could not grant instructor role: {s3} {p3}")

    print()

    # ── 4. Login as instructor to create courses ────────────────────────
    print("Step 4 — Create sample courses (as instructor)")
    inst_token = login(gateway, "instructor@educorp.dev", "InstructorPass123!")
    if not inst_token:
        inst_token = admin_token
        print("  Using admin token as fallback")

    for course_data in COURSES:
        status, payload = _request(
            "POST",
            f"{gateway}/api/v1/courses/",
            {
                "title": course_data["title"],
                "description": course_data["description"],
                "short_description": course_data["short_description"],
                "category": course_data["category"],
                "difficulty": course_data["difficulty"],
                "estimated_duration": course_data["estimated_duration"],
                "tags": course_data["tags"],
            },
            token=inst_token,
        )
        if status == 201:
            course_id = payload["data"]["id"]
            print(f"  Created course: {course_data['title']}")
            for i, title in enumerate(course_data["modules"], start=1):
                ms, mp = _request(
                    "POST",
                    f"{gateway}/api/v1/courses/{course_id}/modules",
                    {"title": title, "sort_order": i},
                    token=inst_token,
                )
                if ms == 201:
                    print(f"    + Module: {title}")
                else:
                    print(f"    WARN module {title}: {ms} {mp}")
        else:
            print(f"  Exists/skip: {course_data['title']} ({status})")

    print("\n=== Seed complete ===")
    print("\nTest accounts:")
    print("  admin@educorp.dev       / AdminPass123!      [student, instructor, admin]")
    print("  instructor@educorp.dev  / InstructorPass123! [student, instructor]")
    print("  student@educorp.dev     / StudentPass123!    [student]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://localhost", help="API gateway base URL")
    args = parser.parse_args()
    main(args.gateway)
