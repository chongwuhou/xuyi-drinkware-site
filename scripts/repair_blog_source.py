#!/usr/bin/env python3
"""Apply reviewed Blog source repairs through the existing D1/CMS APIs.

The script is intentionally idempotent and fail-closed.  It never writes an
HTML artifact, never calls a translation provider, and never replaces a D1
record unless its current value matches the exact reviewed defect.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blog_source_migrations import (  # noqa: E402
    BICYCLE_SLUG,
    repair_english_table,
    repair_localized_table,
)


ORIGIN = os.environ.get("SITE_ORIGIN", "https://xuyibottles.com").rstrip("/")
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")


class BootstrapRequired(RuntimeError):
    """The live Pages Function is older than the migration client."""


def call(path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is required for the D1 source migration")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Cache-Control": "no-store",
        "User-Agent": "XUYI-D1-Source-Migration/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(ORIGIN + path, data=body, headers=headers, method=method)
    # Publish is deliberately explicit even though this script is run only in
    # the controlled XUYI production workflow.
    if method == "POST":
        request.add_header("x-xuyi-publish-intent", "explicit-owner-approval")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:1000]
        if error.code == 401 and path.startswith("/api/admin/"):
            raise BootstrapRequired(
                "The live XUYI CMS does not expose the guarded source-read route yet; deploy this revision once, then rerun the publisher."
            ) from error
        raise RuntimeError(f"{method} {path} returned HTTP {error.code}: {detail}") from error
    if not isinstance(result, dict):
        raise RuntimeError(f"{method} {path} returned an invalid JSON object")
    if result.get("error"):
        raise RuntimeError(f"{method} {path} failed: {result['error']}")
    return result


def repair_english() -> str:
    result = call(f"/api/admin/blog?slug={BICYCLE_SLUG}")
    post = result.get("post")
    if not isinstance(post, dict):
        raise RuntimeError("D1 Blog API returned no editable bicycle article")
    state = repair_english_table(post)
    if state == "changed":
        response = call("/api/admin/blog", method="POST", payload={"action": "publish", "post": post})
        if response.get("status") != "published":
            raise RuntimeError("English Blog source repair was not published")
    return state


def repair_locales() -> dict[str, str]:
    result = call("/api/admin/page-translations")
    items = result.get("items")
    if not isinstance(items, list):
        raise RuntimeError("D1 translation API returned no item list")
    target_route = "/blog/" + BICYCLE_SLUG + "/"
    matches = {
        str(item.get("locale", "")).lower(): item
        for item in items
        if isinstance(item, dict) and item.get("route") == target_route
    }
    states: dict[str, str] = {}
    for locale in ("es", "pt", "ru", "tr"):
        item = matches.get(locale)
        if not item:
            raise RuntimeError(f"D1 translation API has no {locale} bicycle article")
        content = item.get("content")
        if not isinstance(content, dict):
            raise RuntimeError(f"D1 {locale} bicycle translation payload is invalid")
        main_html = str(content.get("mainHtml", ""))
        updated_html, state = repair_localized_table(main_html, locale)
        states[locale] = state
        if state == "changed":
            response = call(
                "/api/admin/page-translations",
                method="POST",
                payload={
                    "route": target_route,
                    "locale": locale,
                    "title": str(content.get("title", "")),
                    "description": str(content.get("description", "")),
                    "mainHtml": updated_html,
                },
            )
            if response.get("saved") is not True or response.get("locale") != locale:
                raise RuntimeError(f"D1 {locale} Blog source repair was not saved")
    return states


def main() -> None:
    try:
        english = repair_english()
        locales = repair_locales()
    except BootstrapRequired as error:
        # The first deployment after adding a guarded migration necessarily
        # has to publish the new reader before it can run.  The workflow treats
        # this explicit exit code as a safe bootstrap, never as a data success.
        print("XUYI_BLOG_SOURCE_MIGRATION_BOOTSTRAP_PENDING", error)
        raise SystemExit(2)
    print("XUYI_BLOG_SOURCE_MIGRATION", json.dumps({"english": english, "locales": locales}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


