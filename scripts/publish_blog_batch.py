#!/usr/bin/env python3
"""Publish a reviewed multilingual Blog batch through the D1/R2 CMS route.

The batch is editorial input only. Public language configuration is read from
the site, media is uploaded to R2 before D1 is written, and D1 remains the
runtime source of truth after publication.
"""
from __future__ import annotations

import base64
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ORIGIN = os.environ.get("XUYI_SITE_ORIGIN", "https://xuyibottles.com").rstrip("/")
INTENT = "explicit-owner-approval"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def ui(data, key, fallback):
    return str((data.get("ui") or {}).get(key) or fallback)


def request_json(path, token=None, payload=None):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "XUYI-Blog-Batch-Publisher/2.0",
        "x-xuyi-publish-intent": INTENT,
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(ORIGIN + path, data=body, method="GET" if body is None else "POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:1000]
        raise SystemExit("XUYI request " + path + " HTTP " + str(err.code) + ": " + detail)


def public_locale_config():
    config = request_json("/api/site-settings")
    languages = config.get("languages") or {}
    source = str(languages.get("sourceLocale") or "en")
    items = languages.get("items") or []
    public_items = [item for item in items if item.get("public") is not False]
    prefixes = {}
    for item in public_items:
        code = str(item.get("code"))
        raw_prefix = str(item.get("pathPrefix") or "")
        prefixes[code] = "" if code == source else (raw_prefix if raw_prefix.startswith("/") else "/" + (raw_prefix or code))
    if source not in prefixes:
        prefixes[source] = ""
    targets = [code for code in prefixes if code != source]
    if not targets:
        raise SystemExit("No published target languages found in D1 configuration")
    return source, prefixes, targets


def resolve_media(media, batch_path):
    result = []
    root = Path(batch_path).resolve().parent.parent
    for item in media:
        row = dict(item)
        if not row.get("contentBase64") and row.get("sourcePath"):
            candidate = Path(str(row["sourcePath"]))
            if not candidate.is_absolute():
                candidate = root / candidate
            row["contentBase64"] = base64.b64encode(candidate.read_bytes()).decode("ascii")
        row.pop("sourcePath", None)
        result.append(row)
    return result


def publish_media(token, media):
    if not media:
        return {"uploaded": [], "kept": []}
    result = request_json("/api/admin/blog-media-batch", token, {"media": media})
    if result.get("success") is not True:
        raise SystemExit("R2 media upload was not confirmed")
    print("XUYI_BLOG_MEDIA_UPLOADED", json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def localized_product_note(post, locale, prefixes, section_index):
    for note in post.get("product_notes", []):
        if int(note.get("section", -1)) != section_index:
            continue
        pattern = str((note.get("text") or {}).get(locale) or "")
        label = str((note.get("label") or {}).get(locale) or note.get("sku") or "")
        if pattern.count("{product}") != 1:
            raise ValueError("invalid product note " + post["slug"])
        front, back = pattern.split("{product}")
        href = prefixes.get(locale, "/" + locale) + "/products/" + str(note["sku"]) + "/"
        return (' <span class="blog-editorial__product-note" data-editorial-model="' + esc(note["sku"]) + '">' + esc(front)
                + '<a class="blog-editorial__product-link" href="' + href + '">' + esc(label) + '</a>' + esc(back) + '</span>')
    return ""


def main_html(post, locale, data, prefixes, source_locale):
    slug = post["slug"]
    sections = data["sections"]
    if len(sections) != 7:
        raise ValueError(slug + " must have 7 translated sections")
    def section_parts(section):
        if isinstance(section, dict):
            return str(section.get("heading", "")), str(section.get("paragraph", ""))
        return str(section[0]), str(section[1])
    prefix = prefixes.get(locale, "" if locale == source_locale else "/" + locale)
    body = ('<section class="page-intro"><div class="shell"><div class="breadcrumb"><a href="' + prefix + '/">' + esc(ui(data, "home", "Home"))
            + '</a> / <a href="' + prefix + '/blog/">' + esc(ui(data, "blog", "Blog")) + '</a> / ' + esc(ui(data, "buyingGuide", "Buying Guide")) + '</div>'
            '<span class="eyebrow">' + esc(data["category"]) + '</span><h1>' + esc(data["title"]) + '</h1><p>' + esc(data["description"]) + '</p></div></section>')
    body += ('<section class="section blog-editorial"><div class="shell"><div class="blog-detail__cover"><img src="' + esc(post["cover"]) + '" alt="' + esc(post["coverAlt"]) + '" width="1200" height="800" loading="eager" decoding="async"></div>'
             '<div class="blog-editorial__layout"><aside class="blog-editorial__aside"><div class="blog-toc"><span class="eyebrow">' + esc(ui(data, "inThisGuide", "IN THIS GUIDE"))
             + '</span><nav aria-label="' + esc(ui(data, "articleSections", "Article sections")) + '">')
    for i, section in enumerate(sections):
        heading, _ = section_parts(section)
        body += '<a href="#article-section-' + str(i) + '">' + esc(heading) + '</a>'
    body += ('</nav><a class="blog-toc__quote" href="' + prefix + '/contact/#inquiry">' + esc(ui(data, "discussProject", "Discuss your project →")) + '</a></div></aside><article class="article blog-editorial__body">'
             '<div class="blog-meta"><span>' + esc(data["category"]) + '</span><span><time datetime="' + post["updated"] + '">' + post["updated"] + '</time></span></div>'
             '<p class="blog-author-byline"><a rel="author" href="' + prefix + '/about/">XUYI Bottles · Product Sourcing Editorial Team</a></p><p class="blog-lede">' + esc(data["intro"]) + '</p>')
    body += '<div class="blog-takeaway"><strong>' + esc(ui(data, "beforeOrder", "Before releasing a wholesale order")) + '</strong><ul>' + ''.join("<li>" + esc(x) + "</li>" for x in data["checklist"][:3]) + '</ul></div>'
    for i, section in enumerate(sections):
        heading, paragraph = section_parts(section)
        body += '<section class="blog-section" id="article-section-' + str(i) + '"><h2>' + esc(heading) + '</h2><p>' + esc(paragraph) + localized_product_note(post, locale, prefixes, i) + '</p></section>'
    ev = data.get("evidence") or post["evidence"]
    body += ('<section class="blog-evidence" id="primary-sources" aria-labelledby="primary-sources-heading"><span class="eyebrow">' + esc(ui(data, "sourceCheckedNotes", "SOURCE-CHECKED BUYER NOTES"))
             + '</span><h2 id="primary-sources-heading">' + esc(ev["insight"].split(".")[0]) + '</h2><p>' + esc(ev["insight"]) + '</p><p><strong>' + esc(ui(data, "practicalNextStep", "Practical next step:")) + '</strong> ' + esc(ev["next_step"]) + '</p><h3>' + esc(ui(data, "primaryReferences", "Primary references")) + '</h3><ul>')
    for i, ref in enumerate(ev["sources"]):
        label = data["sourceLabels"][i] if i < len(data["sourceLabels"]) else ref["label"]
        body += '<li><a href="' + esc(ref["url"]) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + ' ↗</a></li>'
    body += '</ul><p class="blog-evidence__caveat">' + esc(ui(data, "evidenceCaveat", "These independent references do not certify an XUYI bottle, factory, material or test. Verify the exact model, destination market and current requirements.")) + '</p></section>'
    matrix = data["matrix"]
    body += ('<section class="blog-buyer-matrix" id="buyer-decision-table"><h2>' + esc(matrix["title"]) + '</h2><p>' + esc(matrix["intro"]) + '</p><div class="blog-buyer-matrix__scroll"><table><thead><tr>'
             + ''.join('<th scope="col">' + esc(x) + '</th>' for x in matrix["head"]) + '</tr></thead><tbody>')
    for row in matrix["rows"]:
        body += '<tr><th scope="row">' + esc(row[0]) + '</th><td>' + esc(row[1]) + '</td><td>' + esc(row[2]) + '</td></tr>'
    body += '</tbody></table></div><p class="blog-buyer-matrix__note">' + esc(ui(data, "matrixNote", "Buyer decision criteria, not XUYI certification, published MOQ or guaranteed delivery times. Verify the exact model and market requirements.")) + '</p></section>'
    body += '<section class="blog-checklist"><h2>' + esc(ui(data, "buyerChecklist", "Buyer checklist")) + '</h2><ul>' + ''.join("<li>" + esc(x) + "</li>" for x in data["checklist"]) + '</ul></section>'
    body += '<section class="blog-faq"><h2>' + esc(ui(data, "faqHeading", "Frequently asked questions")) + '</h2>' + ''.join('<details><summary>' + esc(q) + '</summary><p>' + esc(a) + '</p></details>' for q, a in data["faqs"]) + '</section>'
    body += '<div class="blog-editorial__cta"><h2>' + esc(ui(data, "quoteHeading", "Need a quote for a specific model?")) + '</h2><p>' + esc(ui(data, "quoteBody", "Send the model, expected order quantity, customization and destination market so the sourcing team can review the confirmed scope.")) + '</p><a class="button" href="' + prefix + '/contact/#inquiry">' + esc(ui(data, "quoteButton", "Request a Plastic Bottle Quote →")) + '</a></div>'
    body += '<section class="section section--soft blog-related"><div class="shell"><div class="section__head"><div><span class="eyebrow">' + esc(ui(data, "continueReading", "CONTINUE READING")) + '</span><h2 class="section__title">' + esc(ui(data, "relatedGuides", "Related Buying Guides")) + '</h2></div></div><div class="blog-related__grid">'
    for item in data["related"]:
        body += '<article class="blog-related__item"><a href="' + prefix + '/blog/' + item["slug"] + '/"><strong>' + esc(item["title"]) + '</strong></a><p>' + esc(item["description"]) + '</p></article>'
    return body + '</div></div></section></article></div></div></section>'


def card_html(post, data, prefix):
    url = prefix + "/blog/" + post["slug"] + "/"
    return ('<article class="news-card"><a class="news-card__image" href="' + url + '"><img src="' + esc(post["cover"]) + '" alt="' + esc(data["title"]) + '" width="1200" height="800" loading="lazy"></a>'
            '<div class="news-card__info"><span class="news-card__category">' + esc(data["category"]) + '</span><h3><a href="' + url + '">' + esc(data["title"]) + '</a></h3><p>' + esc(data["description"]) + '</p><a class="news-card__read" href="' + url + '">' + esc(ui(data, "readArticle", "Read Article →")) + '</a></div></article>')


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: publish_blog_batch.py <reviewed-batch.json>")
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not token:
        raise SystemExit("CLOUDFLARE_API_TOKEN unavailable")
    batch_path = Path(sys.argv[1])
    document = json.loads(batch_path.read_text(encoding="utf-8"))
    rows = document.get("posts", []) if isinstance(document, dict) else document
    media = document.get("media", []) if isinstance(document, dict) else []
    if not isinstance(rows, list) or not rows:
        raise SystemExit("source must contain a non-empty posts list")
    source_locale, prefixes, targets = public_locale_config()
    publish_media(token, resolve_media(media, batch_path))
    posts, translations, cards = [], [], []
    for source in rows:
        content = {k: v for k, v in source.items() if k not in {"locales", "localized_related"}}
        required = ("slug", "title", "description", "intro", "cover", "updated", "sections", "checklist", "faqs", "related", "product_notes", "buyerDecisionTable", "evidence")
        for key in required:
            if key not in content:
                raise ValueError(source.get("slug", "") + " missing " + key)
        posts.append({"slug": source["slug"], "publishedAt": source["updated"] + "T12:00:00.000Z", "post": content})
        locales = source.get("locales") or {}
        if set(locales) != set(targets):
            raise ValueError(source["slug"] + " locale set mismatch; D1 configured targets are " + ",".join(targets))
        related_map = source.get("localized_related") or {}
        for locale in targets:
            data = dict(locales[locale])
            data["related"] = []
            for related_slug in source["related"]:
                item = (related_map.get(locale) or {}).get(related_slug)
                if not item:
                    raise ValueError(source["slug"] + " missing related translation " + locale + " " + related_slug)
                data["related"].append({"slug": related_slug, "title": item["title"], "description": item["description"]})
            main = main_html(source, locale, data, prefixes, source_locale)
            if main.count('class="blog-section"') != 7 or main.count('class="blog-editorial__product-link"') != 3 or main.count('class="blog-related__item"') != 3 or main.count('class="blog-buyer-matrix"') != 1 or main.count("<details>") != 4:
                raise ValueError(source["slug"] + " " + locale + " HTML contract failed")
            translations.append({"route": "/blog/" + source["slug"] + "/", "locale": locale, "title": data["title"], "description": data["description"], "mainHtml": main})
            cards.append({"slug": source["slug"], "locale": locale, "html": card_html(source, data, prefixes.get(locale, "/" + locale))})
    result = request_json("/api/admin/blog-batch", token, {"posts": posts, "translations": translations, "indexCards": cards})
    print("XUYI_BLOG_BATCH_PUBLISHED", json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


