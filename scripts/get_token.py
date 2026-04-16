#!/usr/bin/env python3
"""Quick helper to get an admin JWT token."""
import urllib.request
import json

data = json.dumps({"email": "admin@educorp.dev", "password": "AdminPass123!"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:80/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = urllib.request.urlopen(req, timeout=30)
d = json.loads(resp.read())
print(d["data"]["access_token"])
