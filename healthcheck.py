"""Minimal deployment health check."""
import os
import urllib.request

url = os.getenv("HEALTHCHECK_URL")
if not url:
    raise SystemExit("Set HEALTHCHECK_URL to run the remote health check")

with urllib.request.urlopen(url, timeout=10) as response:
    if response.status != 200:
        raise SystemExit(f"Health check failed: HTTP {response.status}")
    print(response.read().decode())
