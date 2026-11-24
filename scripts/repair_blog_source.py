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
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blog_source_migrations import (  # noqa: E402
    BICYCLE_SLUG,
    repair_english_table,
    repair_localized_table,
)


TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "a4032d0251103d6ef680b2aaddce1afc")
DATABASE_NAME = "xuyi-drinkware-d1"
CF_API = "https://api.cloudflare.com/client/v4"


def cloudflare_call(path: str, *, method: str = "GET", payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is required for the D1 source migration")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/json",
        "User-Agent": "XUYI-D1-Source-Migration/2.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(CF_API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"{method} {path} returned HTTP {error.code}: {detail}") from error
    if not isinstance(result, dict):
        raise RuntimeError(f"{method} {path} returned an invalid JSON object")
    if result.get("success") is False:
        raise RuntimeError(f"{method} {path} failed: {result.get('errors') or result.get('messages') or 'Cloudflare API error'}")
    return result


def d1_database_id() -> str:
    query = urllib.parse.urlencode({"name": DATABASE_NAME})
    response = cloudflare_call(f"/accounts/{ACCOUNT_ID}/d1/database?{query}")
    matches = [item for item in response.get("result", []) if item.get("name") == DATABASE_NAME]
    if len(matches) != 1 or not matches[0].get("uuid"):
        raise RuntimeError(f"D1 database lookup did not return exactly one {DATABASE_NAME} database")
    return str(matches[0]["uuid"])


def d1_query(database_id: str, sql: str, params: list[object] | None = None) -> tuple[list[dict], dict]:
    response = cloudflare_call(
        f"/accounts/{ACCOUNT_ID}/d1/database/{database_id}/query",
        method="POST",
        payload={"sql": sql, "params": params or []},
    )
    results = response.get("result") or []
    if len(results) != 1:
        raise RuntimeError("D1 query returned an unexpected result count")
    item = results[0]
    if item.get("success") is False:
        raise RuntimeError(f"D1 query failed: {item.get('errors') or item.get('messages')}")
    return item.get("results") or [], item.get("meta") or {}


def d1_batch(database_id: str, statements: list[dict]) -> list[dict]:
    response = cloudflare_call(
        f"/accounts/{ACCOUNT_ID}/d1/database/{database_id}/query",
        method="POST",
        payload={"batch": statements},
    )
    results = response.get("result") or []
    if len(results) != len(statements):
        raise RuntimeError("D1 batch returned an unexpected result count")
    if any(item.get("success") is False for item in results):
        raise RuntimeError("D1 batch failed; the guarded transaction was not accepted")
    return results


def prepare_d1_repairs(database_id: str) -> tuple[list[dict], dict[str, str]]:
    english_rows, _ = d1_query(
        database_id,
        "SELECT slug,status,content_json FROM xuyi_blog_posts WHERE slug=? LIMIT 1",
        [BICYCLE_SLUG],
    )
    if len(english_rows) != 1 or english_rows[0].get("status") != "published":
        raise RuntimeError("D1 has no published bicycle Blog source")
    english_row = english_rows[0]
    try:
        english_post = json.loads(str(english_row.get("content_json") or ""))
    except json.JSONDecodeError as error:
        raise RuntimeError("D1 bicycle Blog source JSON is invalid") from error
    english_old_json = str(english_row["content_json"])
    english_state = repair_english_table(english_post)

    resource_id = "/blog/" + BICYCLE_SLUG + "/"
    locales = ["es", "pt", "ru", "tr"]
    placeholders = ",".join("?" for _ in locales)
    translation_rows, _ = d1_query(
        database_id,
        "SELECT locale,translated_json FROM xuyi_translation_overrides WHERE resource_id=? AND locale IN (" + placeholders + ")",
        ["page:" + resource_id, *locales],
    )
    by_locale = {str(row.get("locale", "")).lower(): row for row in translation_rows}
    changes: list[dict] = []
    if english_state == "changed":
        changes.append({
            "kind": "english",
            "old_json": english_old_json,
            "new_json": json.dumps(english_post, ensure_ascii=False, separators=(",", ":")),
            "slug": BICYCLE_SLUG,
        })

    states: dict[str, str] = {"en": english_state}
    for locale in locales:
        row = by_locale.get(locale)
        if not row:
            raise RuntimeError(f"D1 has no {locale} bicycle Blog translation")
        old_json = str(row.get("translated_json") or "")
        try:
            content = json.loads(old_json)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"D1 {locale} bicycle translation JSON is invalid") from error
        updated_html, state = repair_localized_table(str(content.get("mainHtml", "")), locale)
        states[locale] = state
        if state == "changed":
            content["mainHtml"] = updated_html
            changes.append({
                "kind": "locale",
                "locale": locale,
                "resource_id": "page:" + resource_id,
                "old_json": old_json,
                "new_json": json.dumps(content, ensure_ascii=False, separators=(",", ":")),
            })
    return changes, states


def apply_d1_repairs(database_id: str, changes: list[dict]) -> None:
    if not changes:
        return
    # Every statement shares the same old-value guard.  If any owner edit or
    # concurrent write changed the reviewed defect, all statements become
    # no-ops and the migration refuses to report success.
    guard_parts = []
    guard_params: list[object] = []
    for item in changes:
        if item["kind"] == "english":
            guard_parts.append("(SELECT COUNT(*) FROM xuyi_blog_posts WHERE slug=? AND status='published' AND content_json=?)")
            guard_params.extend([item["slug"], item["old_json"]])
        else:
            guard_parts.append("(SELECT COUNT(*) FROM xuyi_translation_overrides WHERE resource_id=? AND locale=? AND translated_json=?)")
            guard_params.extend([item["resource_id"], item["locale"], item["old_json"]])
    guard = " + ".join(guard_parts) + f" = {len(changes)}"
    statements = [{
        "sql": "UPDATE site_state SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT),updated_at=CURRENT_TIMESTAMP WHERE key='publish_revision' AND (" + guard + ")",
        "params": guard_params,
    }]
    for item in changes:
        if item["kind"] == "english":
            statements.append({
                "sql": "UPDATE xuyi_blog_posts SET content_json=?,updated_at=CURRENT_TIMESTAMP WHERE slug=? AND status='published' AND content_json=? AND (" + guard + ")",
                "params": [item["new_json"], item["slug"], item["old_json"], *guard_params],
            })
        else:
            statements.append({
                "sql": "UPDATE xuyi_translation_overrides SET translated_json=?,reviewed_at=CURRENT_TIMESTAMP WHERE resource_id=? AND locale=? AND translated_json=? AND (" + guard + ")",
                "params": [item["new_json"], item["resource_id"], item["locale"], item["old_json"], *guard_params],
            })
    results = d1_batch(database_id, statements)
    if any(int((result.get("meta") or {}).get("changes", 0)) != 1 for result in results):
        raise RuntimeError("D1 guarded migration changed an unexpected number of rows; no success reported")


def main() -> None:
    database_id = d1_database_id()
    changes, states = prepare_d1_repairs(database_id)
    apply_d1_repairs(database_id, changes)
    print("XUYI_BLOG_SOURCE_MIGRATION", json.dumps({"states": states, "changed": len(changes)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


