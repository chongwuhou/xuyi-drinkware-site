"""Safe static fallback shells for published D1 Blog CMS articles.

The Pages Function remains the live English content owner. These shells
provide a readable fallback and, importantly, give reviewed translations a
real English source route from which to render canonical/hreflang pages.
"""
from html import escape
import json
import re
from blog_content_normalization import dedupe_section_paragraphs

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE = re.compile(r"^/(?:media/(?:ppt/slide-\d{3}\.webp|excel/row-\d{3}\.webp|group/[a-z0-9-]+\.webp|blog/[a-z0-9_-]+\.(?:webp|png|jpg|jpeg))|assets/[a-zA-Z0-9/_-]+\.(?:webp|png|jpg|jpeg))$")
PRODUCT_LINK = re.compile(r"\[([^\]\n]{2,100})\]\(/products/([a-zA-Z0-9_-]{2,80})/\)")
LOCAL_LINK = re.compile(r"^/(?!/)[A-Za-z0-9/_#-]+$")


def esc(value):
    return escape(str(value or ""), quote=True)


def _paragraph(value):
    text = esc(value)
    return PRODUCT_LINK.sub(
        lambda m: '<a class="blog-editorial__product-link" href="/products/' +
        m.group(2) + '/">' + m.group(1) + '</a>', text
    )


def _product_notes(post, section_index, locale="en"):
    notes = post.get("product_notes", [])
    if not isinstance(notes, list):
        return ""
    out = ""
    for note in notes:
        if not isinstance(note, dict) or note.get("section") != section_index:
            continue
        sku = str(note.get("sku") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", sku):
            continue
        text_map = note.get("text") if isinstance(note.get("text"), dict) else {}
        pattern = str(text_map.get(locale) or text_map.get("en") or "")
        if pattern.count("{product}") != 1:
            continue
        label_map = note.get("label") if isinstance(note.get("label"), dict) else {}
        label = str(label_map.get(locale) or label_map.get("en") or sku).strip()
        front, back = pattern.split("{product}")
        link = '<a class="blog-editorial__product-link" href="/products/' + esc(sku) + '/">' + esc(label) + '</a>'
        out += ' <span class="blog-editorial__product-note" data-editorial-model="' + esc(sku) + '">' + esc(front) + link + esc(back) + '</span>'
    return out


def _inline_links(post):
    links = post.get("inline_links", [])
    if not isinstance(links, list):
        return ""
    safe = [pair for pair in links if isinstance(pair, list) and len(pair) == 2
            and isinstance(pair[0], str) and isinstance(pair[1], str)
            and LOCAL_LINK.fullmatch(pair[1])]
    if not safe:
        return ""
    out = '<nav class="blog-buyer-matrix__links blog-inline-links" aria-label="Related reading">'
    out += ''.join('<a href="' + esc(url) + '">' + esc(label) + ' →</a>' for label, url in safe)
    return out + '</nav>'


def _sources(post):
    sources = post.get("sources")
    if not isinstance(sources, dict):
        return ""
    insight = str(sources.get("insight") or "").strip()
    next_step = str(sources.get("next_step") or "").strip()
    caveat = str(sources.get("caveat") or "").strip()
    if not insight and not next_step and not caveat:
        return ""
    out = '<section class="blog-evidence" id="primary-sources" aria-labelledby="primary-sources-heading"><span class="eyebrow">SOURCE-CHECKED BUYER NOTES</span><h2 id="primary-sources-heading">Reference points</h2>'
    if insight:
        out += '<p>' + esc(insight) + '</p>'
    if next_step:
        out += '<p><strong>Practical next step:</strong> ' + esc(next_step) + '</p>'
    out += '<h3>Primary references</h3><ul>'
    out += '<li><a href="https://www.fda.gov/food/food-ingredients-packaging/food-contact-substances" target="_blank" rel="noopener noreferrer">FDA food-contact substance reference ↗</a></li>'
    out += '<li><a href="https://eur-lex.europa.eu/eli/reg/2004/1935/oj" target="_blank" rel="noopener noreferrer">European food-contact materials framework ↗</a></li>'
    out += '</ul>'
    if caveat:
        out += '<p class="blog-evidence__caveat">' + esc(caveat) + '</p>'
    return out + '</section>'


def _date(value):
    raw = str(value or "")[:10]
    return raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) else ""


def _buyer_table(post):
    table = post.get("buyerDecisionTable")
    if not isinstance(table, dict):
        return ""
    head, rows = table.get("head"), table.get("rows")
    if not isinstance(head, list) or len(head) != 3:
        return ""
    if not isinstance(rows, list) or len(rows) < 4:
        return ""
    if any(not isinstance(row, list) or len(row) != 3 for row in rows):
        return ""
    out = '<section class="blog-buyer-matrix" id="buyer-decision-table"><h2>' + esc(table.get("title")) + '</h2><p>' + esc(table.get("intro")) + '</p><div class="blog-buyer-matrix__scroll"><table><thead><tr>'
    out += ''.join('<th scope="col">' + esc(value) + '</th>' for value in head)
    out += '</tr></thead><tbody>'
    for row in rows:
        out += '<tr><th scope="row">' + esc(row[0]) + '</th>' + ''.join(
            '<td>' + esc(value) + '</td>' for value in row[1:]
        ) + '</tr>'
    out += '</tbody></table></div><p class="blog-buyer-matrix__note">Buyer decision criteria, not XUYI certification, published MOQ or guaranteed delivery times. Verify the exact model and market requirements.</p>'
    links = table.get("links", [])
    if isinstance(links, list):
        safe = [pair for pair in links if isinstance(pair, list) and len(pair) == 2
                and isinstance(pair[0], str) and isinstance(pair[1], str)
                and LOCAL_LINK.fullmatch(pair[1])]
        if safe:
            out += '<nav class="blog-buyer-matrix__links" aria-label="Relevant product and collection references">'
            out += ''.join('<a href="' + esc(url) + '">' + esc(label) + ' →</a>'
                           for label, url in safe)
            out += '</nav>'
    return out + '</section>'


def render(post, known_slugs=()):
    if not isinstance(post, dict):
        raise ValueError("CMS Blog post must be an object")
    slug = str(post.get("slug") or "")
    if not SLUG.fullmatch(slug) or post.get("status") != "published":
        raise ValueError("Only valid published D1 Blog posts can be rendered")
    title = str(post.get("title") or "").strip()
    description = str(post.get("description") or "").strip()
    intro = str(post.get("intro") or "").strip()
    cover = str(post.get("cover") or "")
    sections = post.get("sections")
    if len(title) < 12 or len(description) < 25 or len(intro) < 50 or not IMAGE.fullmatch(cover):
        raise ValueError("Published D1 Blog post has incomplete safe metadata: " + slug)
    if not isinstance(sections, list) or not 2 <= len(sections) <= 24:
        raise ValueError("Published D1 Blog post has invalid sections: " + slug)
    if any(not isinstance(item, dict) or len(str(item.get("heading") or "")) < 5
           or len(str(item.get("paragraph") or "")) < 60 for item in sections):
        raise ValueError("Published D1 Blog post has an incomplete section: " + slug)
    sections = dedupe_section_paragraphs(sections)

    published = _date(post.get("published_at")) or _date(post.get("updated")) or _date(post.get("updated_at"))
    modified = _date(post.get("updated")) or _date(post.get("updated_at")) or published
    body = '<section class="page-intro"><div class="shell"><div class="breadcrumb"><a href="/">Home</a> / <a href="/blog/">Blog</a> / Buying Guide</div><span class="eyebrow">XUYI · PLASTIC DRINKWARE</span><h1>' + esc(title) + '</h1><p>' + esc(description) + '</p></div></section>'
    body += '<section class="section blog-editorial"><div class="shell"><div class="blog-detail__cover"><img src="' + esc(cover) + '" alt="' + esc(post.get("coverAlt") or title) + '" width="1200" height="800" loading="eager" decoding="async"></div><div class="blog-editorial__layout"><aside class="blog-editorial__aside"><div class="blog-toc"><span class="eyebrow">IN THIS GUIDE</span><nav aria-label="Article sections">'
    for index, section in enumerate(sections):
        body += '<a href="#article-section-' + str(index) + '">' + esc(section["heading"]) + '</a>'
    body += '</nav><a class="blog-toc__quote" href="/contact/#inquiry">Discuss your project →</a></div></aside><article class="article blog-editorial__body"><div class="blog-meta"><span>' + esc(post.get("group") or "BUYER RESOURCES") + '</span><span>'
    if published:
        body += '<time datetime="' + published + '">Published ' + published + '</time>'
    if modified and modified > published:
        body += ' · <time datetime="' + modified + '">Reviewed ' + modified + '</time>'
    body += '</span></div><p class="blog-author-byline"><a rel="author" href="/about/">By XUYI Bottles · Product Sourcing Editorial Team</a></p><p class="blog-lede">' + _paragraph(intro) + '</p>'

    checklist = post.get("checklist") if isinstance(post.get("checklist"), list) else []
    if checklist:
        body += '<div class="blog-takeaway"><strong>Before requesting a quote</strong><ul>' + ''.join(
            '<li>' + esc(item) + '</li>' for item in checklist[:3]
        ) + '</ul></div>'
    for index, section in enumerate(sections):
        body += '<section class="blog-section" id="article-section-' + str(index) + '"><h2>' + esc(section["heading"]) + '</h2><p>' + _paragraph(section["paragraph"]) + _product_notes(post, index) + '</p></section>'
    body += _inline_links(post) + _sources(post) + _buyer_table(post)
    if checklist:
        body += '<section class="blog-checklist"><h2>Buyer checklist</h2><ul>' + ''.join(
            '<li>' + esc(item) + '</li>' for item in checklist
        ) + '</ul></section>'
    faqs = post.get("faqs") if isinstance(post.get("faqs"), list) else []
    valid_faqs = [item for item in faqs if isinstance(item, dict) and item.get("question") and item.get("answer")]
    if valid_faqs:
        body += '<section class="blog-faq"><h2>Frequently asked questions</h2>'
        for item in valid_faqs:
            body += '<details><summary>' + esc(item["question"]) + '</summary><p>' + _paragraph(item["answer"]) + '</p></details>'
        body += '</section>'
    body += '<div class="blog-editorial__cta"><h2>Need a quote for a specific model?</h2><p>Send the model, expected order quantity, logo requirements and destination market. XUYI can review confirmed material and customization options.</p><a class="button" href="/contact/#inquiry">Request a Plastic Bottle Quote →</a></div>'

    related = post.get("related") if isinstance(post.get("related"), list) else []
    valid_related = [item for item in related if isinstance(item, str) and item != slug
                     and SLUG.fullmatch(item) and item in set(known_slugs)]
    if valid_related:
        body += '<section class="section section--soft blog-related"><div class="shell"><div class="section__head"><div><span class="eyebrow">CONTINUE READING</span><h2 class="section__title">Related Buying Guides</h2></div></div><div class="blog-related__grid">'
        for linked in valid_related[:3]:
            body += '<article class="blog-related__item"><a href="/blog/' + esc(linked) + '/">' + esc(linked.replace("-", " ").title()) + '</a></article>'
        body += '</div></div></section>'
    return body + '</article></div></div></section>'


def enrich(document, post, origin="https://xuyibottles.com"):
    slug = post["slug"]
    url = origin + "/blog/" + slug + "/"
    published = _date(post.get("published_at")) or _date(post.get("updated")) or _date(post.get("updated_at"))
    modified = _date(post.get("updated")) or _date(post.get("updated_at")) or published
    image = origin + str(post["cover"])
    metadata = '<meta property="og:type" content="article">'
    if published:
        metadata += '<meta property="article:published_time" content="' + published + '">'
    if modified:
        metadata += '<meta property="article:modified_time" content="' + modified + '">'
    metadata += '<meta property="og:image" content="' + esc(image) + '"><meta name="twitter:image" content="' + esc(image) + '">'
    keywords = [str(post.get("primary_keyword") or "").strip()]
    keywords += [str(value).strip() for value in (post.get("secondary_keywords") or []) if isinstance(value, str)]
    keywords = [value for value in keywords if value]
    if keywords:
        metadata += '<meta name="keywords" content="' + esc(", ".join(keywords)) + '">'
    graph = {
        "@context": "https://schema.org", "@type": "BlogPosting", "@id": url + "#article",
        "headline": post["title"], "description": post["description"],
        "mainEntityOfPage": {"@type": "WebPage", "@id": url}, "image": [image],
        "inLanguage": "en",
        "author": {"@type": "Organization", "name": "XUYI Bottles", "url": origin + "/about/"},
        "publisher": {"@type": "Organization", "name": "XUYI Bottles", "url": origin + "/"}
    }
    if published:
        graph["datePublished"] = published
    if modified:
        graph["dateModified"] = modified
    if keywords:
        graph["keywords"] = keywords
    scripts = '<script type="application/ld+json">' + json.dumps(
        graph, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c") + '</script>'
    faqs = post.get("faqs") if isinstance(post.get("faqs"), list) else []
    valid = [item for item in faqs if isinstance(item, dict) and isinstance(item.get("question"), str)
             and item["question"].strip() and isinstance(item.get("answer"), str) and item["answer"].strip()]
    if valid:
        faq = {
            "@context": "https://schema.org", "@type": "FAQPage", "inLanguage": "en", "url": url,
            "mainEntity": [{"@type": "Question", "name": item["question"],
                            "acceptedAnswer": {"@type": "Answer", "text": item["answer"]}}
                           for item in valid]
        }
        scripts += '<script type="application/ld+json">' + json.dumps(
            faq, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c") + '</script>'
    return document.replace("</head>", metadata + scripts + "</head>", 1)


