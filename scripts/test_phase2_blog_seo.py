#!/usr/bin/env python3
"""Phase-two Blog SEO gate: D1 dates, multilingual FAQ/Breadcrumb schema and image geometry."""
from __future__ import annotations
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
DIST=ROOT/"dist"
SNAPSHOT=ROOT/"_local_ops"/"build-snapshot.json"
JSONLD=re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',re.I|re.S)
IMG=re.compile(r"<img\b[^>]*>",re.I)
NS="{http://www.sitemaps.org/schemas/sitemap/0.9}"
BAD_TRANSLATION_FRAGMENTS = {
    "es": ("gorras deportivas",),
    "pt": ("especificar it", "depende depende"),
    "ru": ("спортивных кепок", "оба понятны, но не являются синонимами"),
    "tr": ("anlaşılır olabilir",),
}

def attr(tag,key):
    return re.search(r"\b"+re.escape(key)+r'=["\']([^"\']+)["\']',tag,re.I)

def schema_nodes(document):
    result=[]
    for match in JSONLD.finditer(document):
        try:data=json.loads(match.group(1))
        except (ValueError,TypeError):continue
        values=data.get("@graph",[]) if isinstance(data,dict) and isinstance(data.get("@graph"),list) else [data]
        result.extend(item for item in values if isinstance(item,dict))
    return result

def main():
    state=json.loads(SNAPSHOT.read_text(encoding="utf8"))
    published=[str(row.get("slug")) for row in state.get("blogPosts",[])
               if isinstance(row,dict) and row.get("status")=="published"]
    assert published and len(published)==len(set(published)), "D1 published Blog set is invalid"
    manifest=json.loads((DIST/"locale-manifest.json").read_text(encoding="utf8"))
    locales=manifest.get("locales") or []
    assert locales, "Locale manifest is empty"
    sitemap=ET.parse(DIST/"sitemap.xml").getroot()
    sitemap_rows={item.find(NS+"loc").text:item for item in sitemap if item.find(NS+"loc") is not None}
    checked=0
    faq_pages=0
    breadcrumb_pages=0
    image_count=0
    article_keywords={}
    citation_pages=0
    evidence_pages=0
    for language in locales:
        code=str(language.get("code") or "")
        prefix=str(language.get("pathPrefix") or "")
        root=DIST/(prefix if prefix else ".")/"blog"
        for slug in published:
            page=root/slug/"index.html"
            assert page.is_file(), (code,slug,"missing static Blog page")
            document=page.read_text(encoding="utf8")
            for fragment in BAD_TRANSLATION_FRAGMENTS.get(code, ()):
                assert fragment.casefold() not in document.casefold(), (code,slug,"known translation fragment",fragment)
            parsed=schema_nodes(document)
            blog_schema=[item for item in parsed if item.get("@type") in {"BlogPosting","Article"}]
            assert len(blog_schema)==1 and str(blog_schema[0].get("keywords") or "").strip(), (code,slug,"localized Blog keywords")
            visible_evidence = any(marker in document for marker in ('id="primary-sources"','id="source-reviewed-deep-dive"'))
            if visible_evidence:
                assert isinstance(blog_schema[0].get("citation"),list) and blog_schema[0]["citation"], (code,slug,"Blog citations")
                citation_pages+=1
                evidence_pages+=1
            article_keywords[(code,slug)]=str(blog_schema[0].get("keywords") or "").strip()
            breadcrumbs=[item for item in parsed if item.get("@type")=="BreadcrumbList"]
            assert len(breadcrumbs)==1 and len(breadcrumbs[0].get("itemListElement") or [])>=3,(code,slug,"BreadcrumbList")
            breadcrumb_pages+=1
            section=re.search(r'<section\b[^>]*class=["\'][^"\']*\bblog-faq\b[^"\']*["\'][^>]*>(.*?)</section>',document,re.I|re.S)
            pairs=re.findall(r"<details\b[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>",section.group(1),re.I|re.S) if section else []
            faqs=[item for item in parsed if item.get("@type")=="FAQPage"]
            if pairs:
                assert len(faqs)==1 and len(faqs[0].get("mainEntity") or [])==len(pairs),(code,slug,"FAQPage")
                faq_pages+=1
            else:
                assert not faqs, (code,slug,"FAQPage without visible FAQ answers")
            cover=re.search(r'<(?:div|figure)\b[^>]*class=["\'][^"\']*\bblog-(?:detail|editorial)__cover\b[^"\']*["\'][^>]*>\s*(<img\b[^>]*>)',document,re.I|re.S)
            assert cover,(code,slug,"Blog cover")
            tag=cover.group(1)
            loading=attr(tag,"loading")
            assert loading and loading.group(1).lower()=="eager",(code,slug,"cover loading")
            assert attr(tag,"width") and attr(tag,"height"),(code,slug,"cover geometry")
            body=document.split("</main>",1)[0]
            for image in IMG.findall(body):
                assert attr(image,"width") and attr(image,"height"),(code,slug,"image geometry")
                image_count+=1
            url="https://xuyibottles.com/"+(prefix+"/" if prefix else "")+"blog/"+slug+"/"
            item=sitemap_rows.get(url)
            assert item is not None and item.find(NS+"lastmod") is not None,(code,slug,"sitemap lastmod")
            checked+=1
    for language in locales:
        code=str(language.get("code") or "")
        if code=="en": continue
        for slug in published:
            localized=article_keywords.get((code,slug),"")
            english=article_keywords.get(("en",slug),"")
            assert localized and localized != english, (code,slug,"English Blog keywords inherited")
    print("XUYI_PHASE2_BLOG_SEO_PASSED",checked,"localized_blog_pages",faq_pages,"FAQPage",breadcrumb_pages,"BreadcrumbList",image_count,"images","localized_keywords",len(article_keywords),"citation_pages",citation_pages,"evidence_pages",evidence_pages)

if __name__=="__main__":
    main()

