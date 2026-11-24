"""XUYI editorial page rendering. Article copy lives in data/blog-guides.json."""
import json
import re
from site_renderer import BUILD_STATE, ROOT, e, photo, intro, SITE_ORIGIN

from blog_catalog_source import load_guides
from blog_content_normalization import dedupe_section_paragraphs
GUIDES = {post["slug"]:post for post in load_guides(ROOT)}
STATIC_GUIDE_UPDATED = {slug: str(post.get("updated") or "") for slug, post in GUIDES.items()}
# D1 is the source of truth for published Blog copy. Existing static slugs
# must render the reviewed D1 row too; otherwise the index can be current
# while the detail page silently keeps the old six-section template. Keep the
# original static editorial date for legacy evidence gates; D1 content changes
# still publish through the normal revision and live verification checks.
for _d1_post in BUILD_STATE.get("blogPosts",[]):
    if not isinstance(_d1_post,dict):continue
    _slug=str(_d1_post.get("slug") or "")
    if _slug in GUIDES and isinstance(_d1_post.get("sections"),list) and len(_d1_post["sections"])>=2:
        _original_updated=GUIDES[_slug].get("updated")
        GUIDES[_slug]={**GUIDES[_slug],**_d1_post}
        if _original_updated:GUIDES[_slug]["updated"]=_original_updated
COVER_OVERRIDES = json.loads((ROOT / "data/blog-cover-overrides.json").read_text(encoding="utf-8"))
assert set(COVER_OVERRIDES).issubset(GUIDES), "Unknown blog cover override"
EVIDENCE=json.loads((ROOT / "data/editorial-evidence.json").read_text(encoding="utf-8"))
assert set(EVIDENCE).issubset(GUIDES)
LEGACY_GUIDES = {
    "wholesale-plastic-water-bottle-buying-guide",
    "plastic-bottle-material-selection",
    "custom-logo-water-bottle-checklist",
    "sports-bottle-vs-water-jug",
    "kids-water-bottle-procurement",
    "shaker-bottle-wholesale"
}

CONTEXT_LINKS = {
    "wholesale-plastic-water-bottle-buying-guide": [("Browse all bottle models", "/products/"), ("OEM/ODM services", "/capabilities/oem-odm/")],
    "plastic-bottle-material-selection": [("Browse plastic bottle models", "/products/"), ("Quality control approach", "/quality-control/")],
    "custom-logo-water-bottle-checklist": [("Custom logo service", "/capabilities/custom-logo/"), ("Custom packaging", "/capabilities/custom-packaging/")],
    "sports-bottle-vs-water-jug": [("Sports bottles", "/collections/sports-water-bottles/"), ("Large water jugs", "/collections/large-capacity-water-jugs/")],
    "kids-water-bottle-procurement": [("Kids bottles", "/collections/kids-water-bottles/"), ("Request samples", "/request-sample/")],
    "shaker-bottle-wholesale": [("Protein shaker bottles", "/collections/plastic-shaker-bottles/"), ("Custom logo options", "/capabilities/custom-logo/")],
    "tritan-vs-pp-petg-pc": [("Plastic bottle range", "/products/"), ("Quality requirements", "/quality-control/")],
    "bpa-free-plastic-water-bottle-sourcing": [("Plastic bottle range", "/products/"), ("Quality control", "/quality-control/")],
    "water-bottle-lid-leakproof-testing": [("Bottle feature range", "/features/flip-top/"), ("Quality control", "/quality-control/")],
    "custom-water-bottle-moq-pricing": [("Wholesale bottle models", "/products/"), ("Custom packaging", "/capabilities/custom-packaging/")],
    "oem-vs-odm-plastic-water-bottles": [("OEM & ODM", "/capabilities/oem-odm/"), ("Request a sample", "/request-sample/")],
    "water-bottle-quality-control-checklist": [("Quality control", "/quality-control/"), ("Sample approval", "/request-sample/")],
    "custom-water-bottle-export-packaging": [("Shipping and logistics", "/shipping-logistics/"), ("Custom packaging", "/capabilities/custom-packaging/")],
    "how-to-start-private-label-water-bottle-brand": [("All product models", "/products/"), ("OEM and ODM service", "/capabilities/oem-odm/")],
    "water-bottle-logo-printing-methods": [("Custom logo service", "/capabilities/custom-logo/"), ("Request a sample", "/request-sample/")],
    "sports-water-bottle-customization": [("Sports bottle collection", "/collections/sports-water-bottles/"), ("Custom bottle service", "/capabilities/custom-water-bottle/")]
}

def cover_path(slug):
    cover=GUIDES[slug]["cover"]
    return COVER_OVERRIDES.get(slug, cover if str(cover).startswith("/") else "/media/ppt/" + cover)

def anchor(heading):
    return re.sub(r"[^a-z0-9-]+", "-", heading.lower().replace("’", "").replace("'", "")).strip("-")[:90]

def render_copy(value):
    """Escape D1 copy while preserving safe same-site Markdown links."""
    escaped = e(value)
    def replace(match):
        label, href = match.group(1), match.group(2)
        if not href.startswith("/") or href.startswith("//"):
            return match.group(0)
        return "<a href=\"" + e(href) + "\">" + label + "</a>"
    return re.sub(r"\[([^\]]+)\]\((/[^)\s]+)\)", replace, escaped)

def render_primary_evidence(slug):
    evidence=EVIDENCE.get(slug)
    if not evidence:return ""
    h='<section class="blog-evidence" id="primary-sources" aria-labelledby="primary-sources-heading"><span class="eyebrow">SOURCE-CHECKED BUYER NOTES</span><h2 id="primary-sources-heading">'+e(evidence["title"])+'</h2>'
    h+='<p>'+e(evidence["insight"])+'</p><p><strong>Practical next step:</strong> '+e(evidence["next_step"])+'</p>'
    h+='<h3>Primary references</h3><ul>'
    for source in evidence["sources"]:
        assert source["url"].startswith(("https://www.fda.gov/","https://eur-lex.europa.eu/","https://support.gs1.org/","https://food.ec.europa.eu/","https://www.iso.org/","https://www.eastman.com/","https://www.uspto.gov/","https://www.pantone.com/","https://health.clevelandclinic.org/"))
        h+='<li><a href="'+e(source["url"])+'" target="_blank" rel="noopener noreferrer">'+e(source["label"])+' ↗</a></li>'
    h+='</ul><p class="blog-evidence__caveat">External regulations and standards are independent references, not product certification or proof of testing by XUYI. Confirm applicability and the latest rules for the exact product, destination and transaction date.</p></section>'
    return h

BUYER_MATRICES = {
    **json.loads((ROOT / "data/blog-buyer-decision-tables.json").read_text(encoding="utf-8"))["articles"],
    **{post["slug"]:post["buyerDecisionTable"] for post in GUIDES.values() if "buyerDecisionTable" in post}
}
assert set(BUYER_MATRICES)==set(GUIDES),"Every reviewed buyer guide needs its own decision table"

def render_buyer_matrix(slug, override=None):
    """Render a source-backed editorial table, not post-build HTML rewrites."""
    matrix=override if override is not None else BUYER_MATRICES[slug]
    assert len(matrix["head"])==3 and len(matrix["rows"])>=4
    h='<section class="blog-buyer-matrix" id="buyer-decision-table"><h2>'+e(matrix["title"])+'</h2>'
    h+='<p>'+e(matrix["intro"])+'</p><div class="blog-buyer-matrix__scroll"><table>'
    h+='<thead><tr>'+''.join('<th scope="col">'+e(v)+'</th>' for v in matrix["head"])+'</tr></thead><tbody>'
    for cells in matrix["rows"]:
        assert len(cells)==3,(slug,cells)
        h+='<tr><th scope="row">'+e(cells[0])+'</th>'+''.join('<td>'+e(v)+'</td>' for v in cells[1:])+'</tr>'
    h+='</tbody></table></div><p class="blog-buyer-matrix__note">Buyer decision criteria, not XUYI certification, published MOQ or guaranteed delivery times. Verify the exact model and market requirements.</p>'
    h+='<nav class="blog-buyer-matrix__links" aria-label="Relevant product and collection references">'
    for label,url in matrix.get("links",[]):
        assert url.startswith("/") and not url.startswith("//"),url
        h+='<a href="'+e(url)+'">'+e(label)+' →</a>'
    return h+'</nav></section>'

BLOG_DEPTH=json.loads((ROOT/"data/blog-depth-evidence-en.json").read_text(encoding="utf8"))["articles"]

for dataset in ("part1","part2","part3"):
    extra=json.loads((ROOT/("data/blog-deep-research-"+dataset+".json")).read_text(encoding="utf8"))["articles"]
    for slug,entry in extra.items():
        if slug not in GUIDES:raise ValueError("Unknown deep article source: "+slug)
        if slug in BLOG_DEPTH:raise ValueError("Duplicate reviewed deep article: "+slug)
        # The published CMS article is authoritative: if its introduction
        # differs, do not insert a baseline supplement on the live route.
        BLOG_DEPTH[slug]={**entry,"baselineIntro":GUIDES[slug]["intro"]}

def render_depth_evidence(slug):
    entry=BLOG_DEPTH.get(slug)
    if not entry:return ""
    out='<section class="blog-deep-dive" id="source-reviewed-deep-dive"><h2>'+e(entry.get("title","Material sourcing: detailed buyer decisions"))+'</h2>'
    for item in entry["sections"]:
        out+='<section class="blog-deep-dive__section"><h3>'+e(item["heading"])+'</h3><p>'+e(item["paragraph"])+'</p></section>'
    if entry.get("sources"):
        out+='<nav class="blog-deep-dive__sources" aria-label="Official research references"><h3>Research references from official authorities</h3><ul>'
        for source in entry["sources"]:
            url=source["url"]
            if not url.startswith(("https://www.fda.gov/","https://www.cpsc.gov/","https://www.iso.org/","https://www.ftc.gov/","https://www.ista.org/","https://www.eastman.com/","https://support.gs1.org/","https://food.ec.europa.eu/","https://eur-lex.europa.eu/","https://echa.europa.eu/","https://iccwbo.org/","https://www.uspto.gov/")):
                raise ValueError("Unreviewed reference domain: "+url)
            out+='<li><a href="'+e(url)+'" rel="noopener noreferrer" target="_blank">'+e(source["label"])+' ↗</a></li>'
        out+='</ul><p>These are independent educational sources; they do not certify any XUYI bottle, factory or material.</p></nav>'
    return out+'</section>'

def owner_safe_depth(route,body):
    """Never add baseline text when a D1 owner changed the article introduction."""
    slug=route.strip("/").split("/")[-1]
    entry=BLOG_DEPTH.get(slug)
    if not entry or 'id="source-reviewed-deep-dive"' in body:return ""
    match=re.search(r'<p class="blog-lede">(.*?)</p>',body,re.S)
    if not match:return ""
    from html import unescape
    intro=unescape(re.sub(r'<[^>]*>','',match.group(1))).strip()
    return render_depth_evidence(slug) if intro==entry["baselineIntro"] else ""

def render_product_notes(post, section_index, locale="en"):
    notes=[x for x in post.get("product_notes",[]) if x.get("section")==section_index]
    out=""
    for note in notes:
        pattern=note["text"][locale]
        assert pattern.count("{product}")==1,(post["slug"],section_index,locale)
        sku=str(note["sku"])
        label=note.get("label",{}).get(locale) or sku
        prefix="" if locale=="en" else "/"+locale
        link='<a class="blog-editorial__product-link" href="'+prefix+'/products/'+e(sku)+'/">'+e(label)+'</a>'
        front,back=pattern.split("{product}")
        out+=' <span class="blog-editorial__product-note" data-editorial-model="'+e(sku)+'">'+e(front)+link+e(back)+'</span>'
    return out

def article_modified_date(slug,post):
    reviewed="2026-10-14" if slug in BLOG_DEPTH else "2026-10-10" if slug in EVIDENCE else post["updated"]
    return max(post["updated"],reviewed)

def ensure_related_guides(route, body):
    """Add three selected related cards only when an English CMS article has none."""
    match = re.fullmatch(r"/blog/([a-z0-9-]+)/", route)
    if not match:
        return body
    slug = match.group(1)
    post = GUIDES.get(slug)
    if not post:
        return body
    existing = body.count('class="blog-related__item"')
    if existing == 3:
        return body
    if existing:
        raise ValueError("Incomplete owner Blog related-card module: " + slug)
    selected = post.get("related", [])
    if len(selected) != 3 or len(set(selected)) != 3:
        raise ValueError("Expected three distinct related guides: " + slug)
    related = []
    for linked in selected:
        item = GUIDES.get(linked)
        if not item:
            raise ValueError("Unknown related guide " + linked + " for " + slug)
        related.append(item)
    pos = body.rfind("</article>")
    if pos < 0:
        return body
    h = '<section class="section section--soft blog-related"><div class="shell"><div class="section__head"><div><span class="eyebrow">CONTINUE READING</span><h2 class="section__title">Related Buying Guides</h2></div></div>'
    h += '<div class="blog-related__grid">'
    for item in related:
        h += '<article class="blog-related__item"><a href="/blog/' + e(item["slug"]) + '/">' + photo(cover_path(item["slug"]), item["title"], aspect_ratio="3/2") + '<strong>' + e(item["title"]) + '</strong></a><p>' + e(item["description"]) + '</p></article>'
    h += '</div><p class="blog-related__all"><a href="/blog/">View all XUYI buyer guides →</a></p></div></section>'
    return body[:pos] + h + body[pos:]

def render_article(slug):
    post=GUIDES[slug]
    sections=dedupe_section_paragraphs(post["sections"])
    related=[GUIDES[s] for s in post["related"]]
    h=intro("Blog / Buying Guide",post["title"],post["description"])
    h+='<section class="section blog-editorial"><div class="shell">'
    h+='<div class="blog-detail__cover">'+photo(cover_path(slug),post["title"]+" | XUYI plastic drinkware buyer guide",loading="eager",aspect_ratio="3/2")+'</div>'
    h+='<div class="blog-editorial__layout"><aside class="blog-editorial__aside"><div class="blog-toc"><span class="eyebrow">IN THIS GUIDE</span><nav aria-label="Article sections">'
    for item in sections:
        h+='<a href="#'+anchor(item["heading"])+'">'+e(item["heading"])+'</a>'
    h+='</nav><a class="blog-toc__quote" href="/contact/#inquiry">Discuss your project →</a></div></aside>'
    updated=article_modified_date(slug,post)
    # All 16 articles were actually published in D1 on Oct 9. The selected
    # evidence guides were revised Oct 10. Do not manufacture staggered dates.
    published=post["updated"]
    timeline='<time datetime="'+e(published)+'">Published '+e(published)+'</time>'
    if updated>published:timeline+=' · <time datetime="'+e(updated)+'">Reviewed '+e(updated)+'</time>'
    h+='<article class="article blog-editorial__body"><div class="blog-meta"><span>BUYER RESOURCES</span><span>'+timeline+'</span></div>'
    h+='<p class="blog-lede">'+e(post["intro"])+'</p>'
    h+='<div class="blog-takeaway"><strong>Before requesting a quote</strong><ul>'
    for tip in post["checklist"][:3]:h+='<li>'+e(tip)+'</li>'
    h+='</ul></div>'
    from blog_editorial_inline import english_note
    for index,section in enumerate(sections):
        h+='<section class="blog-section" id="'+anchor(section["heading"])+'"><h2>'+e(section["heading"])+'</h2><p>'+render_copy(section["paragraph"])+english_note(slug,index)+render_product_notes(post,index,'en')+'</p></section>'
    if post.get("inline_links"):
        h+='<nav class="blog-buyer-matrix__links blog-inline-links" aria-label="Related reading">'
        for label,href in post["inline_links"]:
            assert href.startswith("/") and not href.startswith("//"),href
            h+='<a href="'+e(href)+'">'+e(label)+' →</a>'
        h+='</nav>'
    h+=render_primary_evidence(slug)
    h+=render_buyer_matrix(slug)
    h+=render_depth_evidence(slug)
    h+='<section class="blog-checklist"><h2>Buyer checklist</h2><p>Use these points when comparing a factory sample, artwork approval and purchase quotation.</p><ul>'
    for tip in post["checklist"]:h+='<li>'+e(tip)+'</li>'
    valid_faqs=[qa for qa in post.get("faqs",[]) if isinstance(qa,dict) and str(qa.get("question") or "").strip() and str(qa.get("answer") or "").strip()]
    h+='</ul></section>'
    if valid_faqs:
        h+='<section class="blog-faq"><h2>Frequently asked questions</h2>'
        for qa in valid_faqs:
            h+='<details><summary>'+e(qa["question"])+'</summary><p>'+e(qa["answer"])+'</p></details>'
        h+='</section>'
    context=CONTEXT_LINKS.get(slug,[])
    if context:
        h+='<div class="blog-context-links"><h2>Explore XUYI products and services</h2>'
        for name,href in context:
            h+='<a href="'+e(href)+'">'+e(name)+' →</a>'
        h+='</div>'
    h+='<div class="blog-editorial__cta"><h2>Need a quote for a specific model?</h2>'
    h+='<p>Send the intended model, material requirements, expected order quantity, artwork and destination market. We will review the options for that exact product rather than assume one specification fits every bottle.</p>'
    h+='<a class="button" href="/contact/#inquiry">Request a Plastic Bottle Quote →</a></div>'
    # Selected related guides belong at the article end, not outside it.
    h+='<section class="section section--soft blog-related"><div class="shell"><div class="section__head"><div><span class="eyebrow">CONTINUE READING</span><h2 class="section__title">Related Buying Guides</h2></div></div>'
    h+='<div class="blog-related__grid">'
    for item in related:
        h+='<article class="blog-related__item"><a href="/blog/'+e(item["slug"])+'/">'+photo(cover_path(item["slug"]),item["title"],aspect_ratio="3/2")+'<strong>'+e(item["title"])+'</strong></a><p>'+e(item["description"])+'</p></article>'
    h+='</div><p class="blog-related__all"><a href="/blog/">View all XUYI buyer guides →</a></p></div></section></article></div></div></section>'
    return h

def enrich_article_html(document, slug):
    post=GUIDES[slug]
    updated=article_modified_date(slug,post)
    url=SITE_ORIGIN+"/blog/"+slug+"/"
    breadcrumb={"@type":"BreadcrumbList","itemListElement":[
      {"@type":"ListItem","position":1,"name":"Home","item":SITE_ORIGIN+"/"},
      {"@type":"ListItem","position":2,"name":"Blog","item":SITE_ORIGIN+"/blog/"},
      {"@type":"ListItem","position":3,"name":post["title"],"item":url}]}
    blogpost={"@type":"BlogPosting","@id":url+"#article","headline":post["title"],
      "description":post["description"],"mainEntityOfPage":{"@type":"WebPage","@id":url},
      "image":[SITE_ORIGIN+cover_path(slug)],
      "datePublished":post["updated"],"dateModified":updated,"inLanguage":"en","keywords":", ".join([post["primary_keyword"]]+post["secondary_keywords"]),
      "author":{"@type":"Organization","name":"XUYI Bottles","url":SITE_ORIGIN+"/"},
      "publisher":{"@type":"Organization","name":"XUYI Bottles","url":SITE_ORIGIN+"/"}}
    if slug in EVIDENCE:
        blogpost["citation"]=[{"@type":"CreativeWork","name":ref["label"],"url":ref["url"]} for ref in EVIDENCE[slug]["sources"]]
    # Legacy articles also have D1-published Oct 9 dates, not just new guides.
    valid_faqs=[qa for qa in post.get("faqs",[]) if isinstance(qa,dict) and str(qa.get("question") or "").strip() and str(qa.get("answer") or "").strip()]
    graph_nodes=[blogpost,breadcrumb]
    if valid_faqs:
        graph_nodes.append({"@type":"FAQPage","mainEntity":[{"@type":"Question","name":qa["question"],"acceptedAnswer":{"@type":"Answer","text":qa["answer"]}} for qa in valid_faqs]})
    graph={"@context":"https://schema.org","@graph":graph_nodes}
    metadata='<meta property="og:type" content="article"><meta property="article:published_time" content="'+e(post["updated"])+'"><meta property="article:modified_time" content="'+e(updated)+'">'
    metadata+='<meta name="keywords" content="'+e(", ".join([post["primary_keyword"]]+post["secondary_keywords"]))+'">'
    metadata+='<meta property="og:image" content="'+e(SITE_ORIGIN+cover_path(slug))+'">'
    metadata+='<script type="application/ld+json">'+json.dumps(graph,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")+'</script>'
    return document.replace("</head>",metadata+"</head>",1)


