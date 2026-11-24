#!/usr/bin/env python3
"""Regression checks for shared Blog source/render contracts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.render_locales import dedupe_localized_blog_sections
from seo_structured_components import add_at_render


LONG = "Confirm the approved model, closure, material and destination requirements before the buyer releases a wholesale order."


def jsonld_types(page: str) -> list[str]:
    result = []
    marker = '<script type="application/ld+json">'
    for chunk in page.split(marker)[1:]:
        raw = chunk.split("</script>", 1)[0]
        payload = json.loads(raw)
        nodes = payload.get("@graph", []) if isinstance(payload, dict) and isinstance(payload.get("@graph"), list) else [payload]
        result.extend(node.get("@type") for node in nodes if isinstance(node, dict) and node.get("@type"))
    return result


def test_localized_section_dedupe() -> None:
    body = (
        '<main><section class="blog-section"><h2>One</h2><p>' + LONG + '</p></section>'
        '<section class="blog-section"><h2>Two</h2><p>' + LONG + '</p></section></main>'
    )
    output = dedupe_localized_blog_sections(body, "/blog/example/")
    assert output.count(LONG) == 1, output
    assert "<h2>One</h2>" in output and "<h2>Two</h2>" in output


def test_blog_faq_schema_matches_visible_answers() -> None:
    page = (
        '<html><head><title>Example</title><meta name="description" content="Example"></head><body><main>'
        '<section class="blog-faq"><h2>FAQ</h2><details><summary>Can buyers verify the model?</summary>'
        '<p>Yes. Verify the model and the approved specification before ordering.</p></details></section>'
        '</main><script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'
        '</body></html>'
    )
    output = add_at_render(page, "/blog/example/", "es")
    types = jsonld_types(output)
    assert types.count("FAQPage") == 1, types
    assert types.count("BreadcrumbList") == 1, types

    no_faq = page.replace('<details><summary>Can buyers verify the model?</summary><p>Yes. Verify the model and the approved specification before ordering.</p></details>', "")
    output = add_at_render(no_faq, "/blog/example/", "es")
    assert "FAQPage" not in jsonld_types(output), output


if __name__ == "__main__":
    test_localized_section_dedupe()
    test_blog_faq_schema_matches_visible_answers()
    print("XUYI_BLOG_SOURCE_CONTRACT_PASSED")

