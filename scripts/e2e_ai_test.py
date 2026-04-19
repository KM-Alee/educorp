#!/usr/bin/env python3
"""End-to-end AI pipeline test using khawaja-m-ali.pdf.

Usage:
    python scripts/e2e_ai_test.py [--base-url http://localhost]

Steps:
  1.  Login as admin and obtain JWT
  2.  Create course "Khawaja M Ali - AI E2E Test"
  3.  Create one module
  4.  Upload khawaja-m-ali.pdf to the module
  5.  Validate the draft
  6.  Publish the course (starts Temporal workflow)
  7.  Poll until REVIEW_REQUIRED or READY (up to 10 minutes)
  8.  Approve if REVIEW_REQUIRED, then poll until READY
  9.  Activate the version
  10. Verify Qdrant has indexed points for the version
  11. Ask the AI assistant a question about the CV
  12. Enqueue all 4 instructor enhancement jobs (summary, objectives, quiz, glossary)
  13. Poll each job until COMPLETED or FAILED
  14. Print structured PASS/FAIL report
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PDF_PATH = Path(__file__).parent.parent / "khawaja-m-ali.pdf"
DEFAULT_BASE_URL = "http://localhost"
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "course_chunks"

AUTH_API = "/api/v1/auth"
COURSE_API = "/api/v1/courses"
PUBLISHING_API = "/api/v1/publishing"
AI_API = "/api/v1/ai"

ADMIN_EMAIL = "admin@educorp.dev"
ADMIN_PASSWORD = "AdminPass123!"

RESULTS: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _ok(resp: httpx.Response, label: str, *, fatal: bool = True) -> dict[str, Any] | None:
    if resp.is_error:
        msg = f"FAIL [{label}] HTTP {resp.status_code}: {resp.text[:500]}"
        RESULTS[label] = f"FAIL (HTTP {resp.status_code})"
        if fatal:
            print(msg)
            sys.exit(1)
        print(f"  WARN: {msg}")
        return None
    body = resp.json()
    if "error" in body:
        msg = f"FAIL [{label}] API error: {body['error']}"
        RESULTS[label] = f"FAIL ({body['error'].get('code', '?')})"
        if fatal:
            print(msg)
            sys.exit(1)
        print(f"  WARN: {msg}")
        return None
    RESULTS[label] = "PASS"
    return body


def _derive_display(status: str, approval_state: str | None, activated_at: str | None) -> str:
    if status in {"FAILED", "CANCELLED", "SUPERSEDED"}:
        return status
    if status == "REVIEW_REQUIRED":
        return "APPROVED" if approval_state == "APPROVED" else "REVIEW_REQUIRED"
    if status == "PUBLISHING":
        return "PUBLISHING"
    if status == "READY":
        return "ACTIVATED" if activated_at else "READY"
    return status


def _poll_version(
    client: httpx.Client,
    base_url: str,
    token: str,
    version_id: str,
    *,
    terminal_statuses: set[str],
    max_wait: int = 600,
    interval: int = 6,
) -> dict[str, Any]:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = client.get(f"{base_url}{PUBLISHING_API}/versions/{version_id}", headers=_h(token))
        body = _ok(resp, "poll_version")
        if body is None:
            sys.exit(1)
        version = body["data"]
        display = _derive_display(
            version["status"], version.get("approval_state"), version.get("activated_at")
        )
        print(
            f"  ... status={version['status']} approval={version.get('approval_state')} display={display}"
        )
        if display in terminal_statuses or version["status"] in terminal_statuses:
            return version
        time.sleep(interval)
    print(f"ERROR: Timed out waiting for version {version_id}")
    sys.exit(1)


def _poll_job(
    client: httpx.Client,
    base_url: str,
    token: str,
    job_id: str,
    label: str,
    *,
    max_wait: int = 120,
    interval: int = 4,
) -> dict[str, Any] | None:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = client.get(f"{base_url}{AI_API}/instructor/jobs/{job_id}", headers=_h(token))
        body = _ok(resp, label, fatal=False)
        if body is None:
            return None
        job = body["data"]
        status = job["status"]
        print(f"  ... job {label} status={status}")
        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return job
        time.sleep(interval)
    print(f"  WARN: Timed out waiting for job {job_id}")
    RESULTS[label] = "FAIL (timeout)"
    return None


def _qdrant_count(version_id: str) -> int:
    """Return number of Qdrant points for the given version_id."""
    try:
        r = httpx.post(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/count",
            json={"filter": {"must": [{"key": "version_id", "match": {"value": version_id}}]}},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()["result"]["count"]
    except Exception as exc:
        print(f"  WARN: Qdrant count failed: {exc}")
        return -1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="EduCorp AI end-to-end test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        sys.exit(1)
    print(f"PDF found: {PDF_PATH} ({PDF_PATH.stat().st_size // 1024}KB)")

    report: dict[str, Any] = {}

    with httpx.Client(timeout=60) as client:
        # ------------------------------------------------------------------ #
        # Step 1: Login
        # ------------------------------------------------------------------ #
        print("\n[1/13] Logging in as admin...")
        resp = client.post(
            f"{base_url}{AUTH_API}/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
        )
        auth = _ok(resp, "login")
        token = auth["data"]["access_token"]
        print(f"  Token obtained (user={auth['data'].get('user', {}).get('email', '?')})")

        # ------------------------------------------------------------------ #
        # Step 2: Create course
        # ------------------------------------------------------------------ #
        print("\n[2/13] Creating course...")
        resp = client.post(
            f"{base_url}{COURSE_API}/",
            json={
                "title": "Khawaja M Ali - AI E2E Test",
                "description": "Automated end-to-end AI pipeline test using a CV PDF.",
                "short_description": "AI E2E test course",
                "category": "other",
                "difficulty": "beginner",
                "tags": ["test", "cv", "ai"],
            },
            headers={**_h(token), "Content-Type": "application/json"},
        )
        course_data = _ok(resp, "create_course")["data"]
        course_id = course_data["id"]
        report["course_id"] = course_id
        print(f"  Course created: {course_id}")

        # ------------------------------------------------------------------ #
        # Step 3: Create module
        # ------------------------------------------------------------------ #
        print("\n[3/13] Creating module...")
        resp = client.post(
            f"{base_url}{COURSE_API}/{course_id}/modules",
            json={
                "title": "Khawaja M Ali CV",
                "description": "CV document",
                "sort_order": 1,
                "is_required": True,
            },
            headers={**_h(token), "Content-Type": "application/json"},
        )
        module_data = _ok(resp, "create_module")["data"]
        module_id = module_data["id"]
        report["module_id"] = module_id
        print(f"  Module created: {module_id}")

        # ------------------------------------------------------------------ #
        # Step 4: Upload PDF
        # ------------------------------------------------------------------ #
        print("\n[4/13] Uploading PDF...")
        with PDF_PATH.open("rb") as fh:
            resp = client.post(
                f"{base_url}{COURSE_API}/{course_id}/modules/{module_id}/assets/upload",
                files={"file": (PDF_PATH.name, fh, "application/pdf")},
                data={"title": PDF_PATH.stem, "sort_order": "1"},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
        asset_data = _ok(resp, "upload_asset")["data"]
        asset_id = asset_data["id"]
        report["asset_id"] = asset_id
        print(f"  Asset uploaded: {asset_id}")

        # ------------------------------------------------------------------ #
        # Step 5: Validate draft
        # ------------------------------------------------------------------ #
        print("\n[5/13] Validating draft...")
        resp = client.post(f"{base_url}{COURSE_API}/{course_id}/validate", headers=_h(token))
        val_data = _ok(resp, "validate_draft")["data"]
        if not val_data.get("is_valid", False):
            issues = val_data.get("issues", [])
            print(f"ERROR: Draft invalid: {issues}")
            RESULTS["validate_draft"] = f"FAIL (invalid: {issues})"
            sys.exit(1)
        print("  Draft is valid")

        # ------------------------------------------------------------------ #
        # Step 6: Publish
        # ------------------------------------------------------------------ #
        print("\n[6/13] Starting publish...")
        resp = client.post(f"{base_url}{COURSE_API}/{course_id}/publish", headers=_h(token))
        pub_data = _ok(resp, "start_publish")["data"]
        version_id = str(pub_data["version_id"])
        report["version_id"] = version_id
        print(f"  Publish started: version_id={version_id}")

        # ------------------------------------------------------------------ #
        # Step 7: Poll until REVIEW_REQUIRED or READY
        # ------------------------------------------------------------------ #
        print("\n[7/13] Polling publish status (up to 10 min)...")
        version = _poll_version(
            client,
            base_url,
            token,
            version_id,
            terminal_statuses={"REVIEW_REQUIRED", "READY", "FAILED", "CANCELLED"},
            max_wait=600,
        )
        display = _derive_display(
            version["status"], version.get("approval_state"), version.get("activated_at")
        )
        print(f"  Reached display status: {display}")

        if display in {"FAILED", "CANCELLED"}:
            RESULTS["publish_pipeline"] = f"FAIL ({display})"
            print(f"ERROR: Publish failed: {version.get('error_details')}")
            sys.exit(1)
        RESULTS["publish_pipeline"] = "PASS"

        # ------------------------------------------------------------------ #
        # Step 8: Approve if REVIEW_REQUIRED
        # ------------------------------------------------------------------ #
        if display == "REVIEW_REQUIRED":
            print("\n[8/13] Approving version...")
            resp = client.post(
                f"{base_url}{PUBLISHING_API}/versions/{version_id}/approve",
                headers=_h(token),
            )
            _ok(resp, "approve_version")
            print("  Approval sent. Polling for READY...")
            version = _poll_version(
                client,
                base_url,
                token,
                version_id,
                terminal_statuses={"READY", "FAILED", "CANCELLED"},
                max_wait=300,
            )
            display = _derive_display(
                version["status"], version.get("approval_state"), version.get("activated_at")
            )
            if display not in {"READY", "ACTIVATED"}:
                RESULTS["approve_version"] = f"FAIL (unexpected: {display})"
                print(f"ERROR: Unexpected status after approval: {display}")
                sys.exit(1)
        else:
            print("\n[8/13] No review required — skipping approval.")
            RESULTS["approve_version"] = "SKIP"

        report["total_chunks"] = version.get("total_chunks", 0)
        print(f"  Version READY — total_chunks={report['total_chunks']}")

        # ------------------------------------------------------------------ #
        # Step 9: Activate
        # ------------------------------------------------------------------ #
        print("\n[9/13] Activating version...")
        if display == "ACTIVATED":
            # Already activated (e.g. auto-activated after approval)
            RESULTS["activate_version"] = "PASS (auto-activated)"
            print("  Version already activated — skipping activate call.")
            resp = client.get(
                f"{base_url}{PUBLISHING_API}/versions/{version_id}", headers=_h(token)
            )
            final_v = _ok(resp, "fetch_final_version")["data"]
        else:
            resp = client.post(
                f"{base_url}{PUBLISHING_API}/versions/{version_id}/activate",
                headers=_h(token),
            )
            act_data = _ok(resp, "activate_version")
            print(f"  Activated: {act_data['data'].get('message')}")
            # Re-fetch to grab quality report
            resp = client.get(
                f"{base_url}{PUBLISHING_API}/versions/{version_id}", headers=_h(token)
            )
            final_v = _ok(resp, "fetch_final_version")["data"]
        report["activated_at"] = final_v.get("activated_at")
        for artifact in final_v.get("artifacts", []):
            if artifact.get("artifact_type") == "QUALITY_REPORT":
                meta = artifact.get("metadata", {})
                report["qdrant_points_indexed"] = meta.get("qdrant_points_indexed", 0)
                report["embeddings_created"] = meta.get("embeddings_created", 0)

        # ------------------------------------------------------------------ #
        # Step 10: Verify Qdrant
        # ------------------------------------------------------------------ #
        print("\n[10/13] Verifying Qdrant index...")
        qdrant_count = _qdrant_count(version_id)
        report["qdrant_points_actual"] = qdrant_count
        if qdrant_count > 0:
            RESULTS["qdrant_index"] = f"PASS ({qdrant_count} points)"
            print(f"  Qdrant has {qdrant_count} points for version {version_id}")
        elif qdrant_count == 0:
            RESULTS["qdrant_index"] = "FAIL (0 points)"
            print("  ERROR: Qdrant has 0 points for this version — embeddings were not stored!")
        else:
            RESULTS["qdrant_index"] = "WARN (count unavailable)"
            print("  WARN: Could not verify Qdrant point count")

        # ------------------------------------------------------------------ #
        # Step 11: AI ask
        # ------------------------------------------------------------------ #
        print("\n[11/13] Calling AI ask endpoint...")
        ask_payload = {
            "course_id": course_id,
            "question": "What is Khawaja M Ali's educational background and key skills?",
        }
        resp = client.post(
            f"{base_url}{AI_API}/ask",
            json=ask_payload,
            headers={**_h(token), "Content-Type": "application/json"},
            timeout=90,
        )
        ask_body = _ok(resp, "ai_ask", fatal=False)
        if ask_body:
            ask_data = ask_body["data"]
            answer_preview = ask_data.get("answer", "")[:200].replace("\n", " ")
            confidence = ask_data.get("confidence", "?")
            citations = ask_data.get("citations", [])
            print(f"  Answer ({confidence}): {answer_preview}...")
            print(f"  Citations: {len(citations)}")
            RESULTS["ai_ask"] = f"PASS (confidence={confidence}, citations={len(citations)})"
            report["ai_answer_confidence"] = confidence
            report["ai_citations"] = len(citations)
        else:
            print("  AI ask returned an error (see above)")

        # ------------------------------------------------------------------ #
        # Step 12: Instructor enhancements
        # ------------------------------------------------------------------ #
        print("\n[12/13] Queueing instructor enhancement jobs...")
        job_ids: dict[str, str] = {}

        for job_type in ("summary", "objectives", "quiz", "glossary"):
            enhance_payload: dict[str, Any] = {
                "course_id": course_id,
                "job_type": job_type,
                "scope": "course",
                "parameters": {},
            }
            resp = client.post(
                f"{base_url}{AI_API}/instructor/enhance",
                json=enhance_payload,
                headers={**_h(token), "Content-Type": "application/json"},
                timeout=30,
            )
            body = _ok(resp, f"enqueue_{job_type}", fatal=False)
            if body:
                jid = str(body["data"]["job_id"])
                job_ids[job_type] = jid
                print(f"  Queued {job_type}: job_id={jid}")
            else:
                print(f"  Failed to queue {job_type}")

        # ------------------------------------------------------------------ #
        # Step 13: Poll all jobs
        # ------------------------------------------------------------------ #
        print("\n[13/13] Polling instructor jobs (up to 2 min each)...")
        for job_type, job_id in job_ids.items():
            print(f"  Polling {job_type} job {job_id}...")
            job = _poll_job(client, base_url, token, job_id, f"job_{job_type}", max_wait=180)
            if job is None:
                RESULTS[f"job_{job_type}"] = "FAIL (poll error)"
            elif job["status"] == "COMPLETED":
                result = job.get("result") or {}
                preview = str(result)[:120].replace("\n", " ")
                RESULTS[f"job_{job_type}"] = f"PASS (result preview: {preview})"
                print(f"  {job_type} COMPLETED: {preview}")
            else:
                error = job.get("error") or {}
                code = error.get("code", "UNKNOWN")
                retryable = error.get("retryable", False)
                level = "WARN" if retryable or code == "AI_TIMEOUT" else "FAIL"
                RESULTS[f"job_{job_type}"] = f"{level} (status={job['status']}, code={code})"
                print(f"  {job_type} {level}: {error}")

    # ---------------------------------------------------------------------- #
    # Final report
    # ---------------------------------------------------------------------- #
    print("\n" + "=" * 70)
    print("FINAL E2E AI PIPELINE REPORT")
    print("=" * 70)
    print("\nInfrastructure / Publishing:")
    for k in (
        "login",
        "create_course",
        "create_module",
        "upload_asset",
        "validate_draft",
        "start_publish",
        "publish_pipeline",
        "approve_version",
        "activate_version",
        "fetch_final_version",
        "qdrant_index",
    ):
        status = RESULTS.get(k, "NOT RUN")
        icon = "✓" if status.startswith("PASS") else ("—" if status == "SKIP" else "✗")
        print(f"  {icon} {k:<30} {status}")

    print("\nAI:")
    for k in (
        "ai_ask",
        "enqueue_summary",
        "enqueue_objectives",
        "enqueue_quiz",
        "enqueue_glossary",
        "job_summary",
        "job_objectives",
        "job_quiz",
        "job_glossary",
    ):
        status = RESULTS.get(k, "NOT RUN")
        icon = "✓" if status.startswith("PASS") else ("—" if status == "NOT RUN" else "✗")
        print(f"  {icon} {k:<30} {status}")

    print("\nMetrics:")
    for k, v in report.items():
        print(f"  {k}: {v}")

    fails = [k for k, v in RESULTS.items() if v.startswith("FAIL")]
    print("\n" + "=" * 70)
    if fails:
        print(f"RESULT: FAILED — {len(fails)} step(s) failed: {', '.join(fails)}")
    else:
        print("RESULT: ALL STEPS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
