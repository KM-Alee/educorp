from __future__ import annotations

import os
import uuid

from locust import HttpUser, between, task

BASE_URL = os.getenv("EDUCORP_BASE_URL", "http://localhost")
STUDENT_EMAIL = os.getenv("EDUCORP_LOAD_STUDENT_EMAIL", "student@educorp.dev")
STUDENT_PASSWORD = os.getenv("EDUCORP_LOAD_STUDENT_PASSWORD", "StudentPass123!")
AI_QUESTION = os.getenv("EDUCORP_LOAD_AI_QUESTION", "Summarize this course.")


class EduCorpUser(HttpUser):
    wait_time = between(1, 3)
    host = BASE_URL

    def on_start(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
            name="auth.login",
        )
        if response.status_code != 200:
            raise RuntimeError(f"Login failed: {response.status_code} {response.text}")

        payload = response.json()["data"]
        self.headers = {"Authorization": f"Bearer {payload['access_token']}"}
        self.course_id = self._discover_course_id()

    def _discover_course_id(self) -> str:
        response = self.client.get(
            "/api/v1/search/courses?q=python",
            headers=self.headers,
            name="search.keyword",
        )
        if response.status_code != 200:
            raise RuntimeError(f"Course search failed: {response.status_code} {response.text}")
        data = response.json().get("data", [])
        if not data:
            raise RuntimeError("No searchable course available for load testing")
        return data[0]["course_id"]

    @task(4)
    def browse_catalog(self) -> None:
        self.client.get(
            "/api/v1/search/courses?q=python", headers=self.headers, name="search.catalog"
        )

    @task(2)
    def view_course(self) -> None:
        self.client.get(
            f"/api/v1/courses/{self.course_id}",
            headers=self.headers,
            name="courses.detail",
        )

    @task(1)
    def enroll_course(self) -> None:
        self.client.post(
            "/api/v1/enrollments/",
            headers=self.headers,
            json={
                "course_id": self.course_id,
                "idempotency_key": f"locust-{uuid.uuid4()}",
            },
            name="enrollment.create",
        )

    @task(2)
    def ai_ask(self) -> None:
        self.client.post(
            "/api/v1/ai/ask",
            headers=self.headers,
            json={"course_id": self.course_id, "question": AI_QUESTION},
            name="ai.ask",
        )
