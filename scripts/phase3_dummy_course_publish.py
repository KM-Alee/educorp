#!/usr/bin/env python3
"""End-to-end publish runner for dummy-course PDFs.

Usage:
    python scripts/phase3_dummy_course_publish.py [--base-url http://localhost] [--token <jwt>]

The script:
1. Creates a course titled "JavaScript Foundations From Slides"
2. Creates modules from sorted PDFs in dummy-course/
3. Uploads each PDF to its module
4. Validates the draft
5. Starts publish
6. Polls status until REVIEW_REQUIRED or READY
7. Approves if review is required (after showing the summary)
8. Polls until READY
9. Activates the version
10. Runs keyword and semantic search
11. Prints a final structured report
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DUMMY_COURSE_DIR = Path(__file__).parent.parent / "dummy-course"

# Service base URLs (Traefik routes on localhost by default)
DEFAULT_BASE_URL = "http://localhost"

COURSE_API = "/api/v1/courses"
AUTH_API = "/api/v1/auth"
PUBLISHING_API = "/api/v1/publishing"
SEARCH_API = "/api/v1/search"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _check(resp: httpx.Response, label: str) -> dict[str, Any]:
    if resp.is_error:
        print(f"ERROR [{label}] HTTP {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)
    body = resp.json()
    if "error" in body:
        print(f"ERROR [{label}]: {body['error']}")
        sys.exit(1)
    return body


def _poll_version(
    client: httpx.Client,
    base_url: str,
    token: str,
    version_id: str,
    *,
    terminal_statuses: set[str],
    max_wait: int = 600,
    interval: int = 5,
) -> dict[str, Any]:
    """Poll GET /publishing/versions/{version_id} until a terminal status or timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = client.get(
            f"{base_url}{PUBLISHING_API}/versions/{version_id}",
            headers=_headers(token),
        )
        body = _check(resp, "get_version")
        version = body["data"]
        status = version["status"]
        approved = version.get("approval_state")
        display = _derive_display_status(status, approved, version.get("activated_at"))
        print(f"  ... status={status} approval={approved} display={display}")
        if display in terminal_statuses or status in terminal_statuses:
            return version
        time.sleep(interval)
    print(f"ERROR: Timed out waiting for version {version_id}")
    sys.exit(1)


def _derive_display_status(status: str, approval_state: str | None, activated_at: str | None) -> str:
    if status == "SUPERSEDED":
        return "SUPERSEDED"
    if status in {"FAILED", "CANCELLED"}:
        return status
    if status == "REVIEW_REQUIRED":
        return "APPROVED" if approval_state == "APPROVED" else "REVIEW_REQUIRED"
    if status == "PUBLISHING":
        return "PUBLISHING"
    if status == "READY":
        return "ACTIVATED" if activated_at else "READY"
    return status


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Dummy-course end-to-end publish runner")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Traefik base URL")
    parser.add_argument("--token", default=os.environ.get("EDUCORP_TOKEN", ""), help="JWT access token")
    parser.add_argument("--no-approve", action="store_true", help="Skip approval even if REVIEW_REQUIRED")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = args.token
    if not token:
        print("ERROR: --token <jwt> is required (or set EDUCORP_TOKEN env var)")
        sys.exit(1)

    # Sort PDFs by filename
    pdfs = sorted(DUMMY_COURSE_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"ERROR: No PDFs found in {DUMMY_COURSE_DIR}")
        sys.exit(1)

    print(f"Found {len(pdfs)} PDFs in {DUMMY_COURSE_DIR}:")
    for p in pdfs:
        print(f"  {p.name}")

    report: dict[str, Any] = {
        "course_title": "JavaScript Foundations From Slides",
        "pdfs": [p.name for p in pdfs],
    }

    with httpx.Client(timeout=60) as client:
        # ---- Step 1: Create course ----------------------------------------
        print("\n[1/10] Creating course...")
        resp = client.post(
            f"{base_url}{COURSE_API}/",
            json={
                "title": "JavaScript Foundations From Slides",
                "description": "A complete JavaScript course built from lecture slides.",
                "short_description": "JavaScript fundamentals from lecture slides",
                "category": "programming",
                "difficulty": "beginner",
                "tags": ["javascript", "programming", "web"],
            },
            headers={**_headers(token), "Content-Type": "application/json"},
        )
        course = _check(resp, "create_course")["data"]
        course_id = course["id"]
        report["course_id"] = course_id
        print(f"  Created course: {course_id}")

        # ---- Step 2+3: Create modules and upload PDFs ----------------------
        print("\n[2/10] Creating modules and uploading PDFs...")
        module_assets: list[dict[str, Any]] = []
        for idx, pdf_path in enumerate(pdfs, start=1):
            # Module title: strip extension, clean up
            module_title = pdf_path.stem.replace("-", " ").replace("_", " ").strip()

            mod_resp = client.post(
                f"{base_url}{COURSE_API}/{course_id}/modules",
                json={
                    "title": module_title,
                    "description": f"Module from {pdf_path.name}",
                    "sort_order": idx,
                    "is_required": True,
                },
                headers={**_headers(token), "Content-Type": "application/json"},
            )
            module = _check(mod_resp, f"create_module_{idx}")["data"]
            module_id = module["id"]
            print(f"  Module {idx}: {module_title} ({module_id})")

            # Upload PDF via multipart directly to course service
            with pdf_path.open("rb") as fh:
                upload_resp = client.post(
                    f"{base_url}{COURSE_API}/{course_id}/modules/{module_id}/assets/upload",
                    files={"file": (pdf_path.name, fh, "application/pdf")},
                    data={"title": pdf_path.stem, "sort_order": "1"},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
            asset_body = _check(upload_resp, f"upload_asset_{idx}")["data"]
            asset_id = asset_body["id"]

            module_assets.append({"module_id": module_id, "asset_id": asset_id, "file": pdf_path.name})
            print(f"  Uploaded: {pdf_path.name} -> asset {asset_id}")

        report["total_assets"] = len(module_assets)

        # ---- Step 4: Validate draft ----------------------------------------
        print("\n[4/10] Validating draft...")
        val_resp = client.post(
            f"{base_url}{COURSE_API}/{course_id}/validate",
            headers=_headers(token),
        )
        val_body = _check(val_resp, "validate")["data"]
        if not val_body.get("is_valid", False):
            issues = val_body.get("issues", [])
            print("ERROR: Draft validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        print("  Draft is valid")

        # ---- Step 5: Start publish ----------------------------------------
        print("\n[5/10] Starting publish...")
        pub_resp = client.post(
            f"{base_url}{COURSE_API}/{course_id}/publish",
            headers=_headers(token),
        )
        pub_body = _check(pub_resp, "publish")["data"]
        version_id = str(pub_body["version_id"])
        report["version_id"] = version_id
        print(f"  Publish started: version_id={version_id}")

        # ---- Step 6: Poll until REVIEW_REQUIRED or READY ------------------
        print("\n[6/10] Polling publish status...")
        version = _poll_version(
            client, base_url, token, version_id,
            terminal_statuses={"REVIEW_REQUIRED", "READY", "FAILED", "CANCELLED"},
        )
        display = _derive_display_status(
            version["status"], version.get("approval_state"), version.get("activated_at")
        )
        print(f"  Reached: {display}")

        if display in {"FAILED", "CANCELLED"}:
            print(f"ERROR: Publish {display}: {version.get('error_details')}")
            sys.exit(1)

        # ---- Step 7: Approve if REVIEW_REQUIRED ---------------------------
        if display == "REVIEW_REQUIRED":
            print("\n[7/10] Version requires review.")
            preflight = version.get("preflight_summary_json") or {}
            print(f"  Preflight summary: {json.dumps(preflight, indent=2)}")
            if args.no_approve:
                print("  --no-approve flag set; skipping approval and exiting.")
                sys.exit(0)
            print("  Approving version...")
            approve_resp = client.post(
                f"{base_url}{PUBLISHING_API}/versions/{version_id}/approve",
                headers=_headers(token),
            )
            _check(approve_resp, "approve")
            print("  Approval sent. Polling for READY...")
            version = _poll_version(
                client, base_url, token, version_id,
                terminal_statuses={"READY", "FAILED", "CANCELLED"},
            )
            display = _derive_display_status(
                version["status"], version.get("approval_state"), version.get("activated_at")
            )
            if display not in {"READY"}:
                print(f"ERROR: Unexpected status after approval: {display}")
                sys.exit(1)
        else:
            print("\n[7/10] No review required, skipping approval step.")

        print(f"  Version is READY: {version_id}")
        report["total_chunks"] = version.get("total_chunks", 0)

        # ---- Step 8: Activate version ------------------------------------
        print("\n[8/10] Activating version...")
        act_resp = client.post(
            f"{base_url}{PUBLISHING_API}/versions/{version_id}/activate",
            headers=_headers(token),
        )
        act_body = _check(act_resp, "activate")["data"]
        print(f"  Activated: {act_body.get('message')}")

        # Re-fetch to get activated_at etc.
        final_resp = client.get(
            f"{base_url}{PUBLISHING_API}/versions/{version_id}",
            headers=_headers(token),
        )
        final_version = _check(final_resp, "final_version")["data"]
        report["activated_at"] = final_version.get("activated_at")

        # Gather quality report stats from artifacts
        for artifact in final_version.get("artifacts", []):
            if artifact.get("artifact_type") == "QUALITY_REPORT":
                meta = artifact.get("metadata", {})
                report["ocr_pages"] = meta.get("ocr_rescue_pages", 0)
                report["nanogpt_pages"] = meta.get("visual_enrichment_pages", 0)
                report["embeddings_reused"] = meta.get("embeddings_reused", 0)
                report["embeddings_created"] = meta.get("embeddings_created", 0)
                report["qdrant_points"] = meta.get("qdrant_points_indexed", 0)

        # ---- Step 9: Keyword search ---------------------------------------
        print("\n[9/10] Keyword search for 'javascript'...")
        kw_resp = client.get(
            f"{base_url}{SEARCH_API}/courses",
            params={"q": "javascript"},
            headers=_headers(token),
        )
        kw_body = _check(kw_resp, "keyword_search")
        kw_items = kw_body.get("data", [])
        print(f"  Found {len(kw_items)} course(s)")
        report["keyword_search_results"] = len(kw_items)
        for item in kw_items[:3]:
            print(f"    - {item['title']} (score={item['relevance_score']:.3f})")

        # ---- Step 10: Semantic search ------------------------------------
        print("\n[10/10] Semantic search: 'What is a closure in JavaScript?'...")
        sem_resp = client.post(
            f"{base_url}{SEARCH_API}/semantic",
            json={"course_id": course_id, "query": "What is a closure in JavaScript?", "top_k": 5},
            headers={**_headers(token), "Content-Type": "application/json"},
        )
        sem_body = _check(sem_resp, "semantic_search")["data"]
        sem_chunks = sem_body.get("chunks", [])
        print(f"  Found {len(sem_chunks)} chunk(s)")
        report["semantic_search_results"] = len(sem_chunks)
        warnings: list[str] = []
        for c in sem_chunks[:3]:
            page = c.get("page_or_slide_number")
            qual = c.get("quality_score")
            mod_title = c.get("module_title", "?")
            asset_title = c.get("asset_title", "?")
            print(f"    - [{mod_title} / {asset_title}] page={page} quality={qual:.2f} score={c['score']:.3f}")
            if page is None:
                warnings.append(f"chunk {c['chunk_id']} missing page_or_slide_number")
        report["warnings"] = warnings

        # ---- Final report ------------------------------------------------
        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        for k, v in report.items():
            print(f"  {k}: {v}")
        print("=" * 60)
        print("\nPhase 3 end-to-end run COMPLETE.")


if __name__ == "__main__":
    main()
