#!/usr/bin/env python3
"""Apply reviewed Blog source repairs through the existing D1/CMS API.

The script is intentionally idempotent and fail-closed.  It never writes an
HTML artifact, never calls a translation provider, and never replaces a D1
record unless its current value matches the exact reviewed defect.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ORIGIN = os.environ.get("SITE_ORIGIN", "https://xuyibottles.com").rstrip("/")


def write_output(name: str, value: object) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def call(path: str, *, payload: dict) -> dict:
    if not TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is required for the D1 source migration")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/json",
        "Cache-Control": "no-store",
        "User-Agent": "XUYI-D1-Source-Migration/3.0",
        "x-xuyi-publish-intent": "explicit-owner-approval",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(ORIGIN + path, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"POST {path} returned HTTP {error.code}: {detail}") from error
    if not isinstance(result, dict):
        raise RuntimeError(f"POST {path} returned an invalid JSON object")
    if result.get("error"):
        raise RuntimeError(f"POST {path} failed: {result['error']}")
    return result


def main() -> None:
    try:
        result = call("/api/admin/blog-batch", payload={"action": "repair-reviewed-source"})
    except RuntimeError as error:
        # A newly added Pages Function cannot exist until the first deploy of
        # this commit.  The workflow performs that one bootstrap deploy, then
        # calls this same guarded entrypoint again before the final rebuild.
        if "A reviewed Blog batch must contain posts, translations and index cards" in str(error):
            print("XUYI_BLOG_SOURCE_MIGRATION_PENDING")
            raise SystemExit(2) from error
        raise
    if result.get("success") is not True or result.get("sourceRepair") is not True:
        raise RuntimeError("D1 Blog source repair was not confirmed")
    write_output("changed", int(result.get("changed") or 0))
    print("XUYI_BLOG_SOURCE_MIGRATION", json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


