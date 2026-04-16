#!/usr/bin/env python3
"""Test semantic search endpoint."""
import urllib.request
import json

# Get token
data = json.dumps({"email": "admin@educorp.dev", "password": "AdminPass123!"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:80/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = urllib.request.urlopen(req, timeout=30)
d = json.loads(resp.read())
token = d["data"]["access_token"]
print(f"Got token: {token[:30]}...")

# First get a course_id from keyword search
ks_data = json.dumps({"query": "javascript", "limit": 1}).encode()
req_ks = urllib.request.Request(
    "http://127.0.0.1:80/api/v1/search/courses",
    data=ks_data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST",
)
ks_resp = urllib.request.urlopen(req_ks, timeout=30)
ks_result = json.loads(ks_resp.read())
course_id = ks_result["data"]["results"][0]["course_id"]
print(f"Using course_id: {course_id}")

# Semantic search
search_data = json.dumps({"query": "What is a closure in JavaScript?", "top_k": 3, "course_id": course_id}).encode()
req2 = urllib.request.Request(
    "http://127.0.0.1:80/api/v1/search/semantic",
    data=search_data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST",
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=30)
    result = json.loads(resp2.read())
    chunks = result["data"]["chunks"]
    print(f"Semantic search: {len(chunks)} chunks returned")
    for i, chunk in enumerate(chunks[:2]):
        print(f"  Chunk {i+1}: score={chunk.get('score', '?'):.4f}, text={str(chunk.get('text', ''))[:80]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body}")
