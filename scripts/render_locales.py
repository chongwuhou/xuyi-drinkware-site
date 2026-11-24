#!/usr/bin/env python3

"""Only publish complete reviewed translations in XUYI D1.

Keeps canonical/hreflang accurate: no English-body fake translated pages.

Uses precisely the same header, footer, side rail and assets as the English UI.

No additional language is published solely by being enabled in settings.

"""

import html

import json

import os

from pathlib import Path

import re

from urllib.parse import urlsplit

import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

from home_banner_config import tag as banner_tag,for_locale as banner_slides

from locale_registry import approved_locales,local_url

from product_locale_seo import polish_product_head

from media_alt_render import apply_media_alts

from image_alt_quality import polish_image_alt

from product_material_performance import inject as inject_materials

from factory_catalog_locales import catalog_cards as factory_catalog_cards

ROOT=Path(__file__).resolve().parent.parent

DIST=ROOT/"dist"

SNAPSHOT=ROOT/"_local_ops/build-snapshot.json"

SITE_CONFIG=json.loads((ROOT/"deployment/site.config.json").read_text(encoding="utf-8"))

ORIGIN=SITE_CONFIG["site"]["origin"]

UI_TRANSLATIONS=json.loads((ROOT/"data/ui-translations.json").read_text(encoding="utf-8"))

RUNTIME_UI_TRANSLATIONS=json.loads((ROOT/"data/runtime-ui-translations.json").read_text(encoding="utf-8"))

LOCALIZED_DATE_LABELS={
    locale:(labels["published"],labels["reviewed"])
    for locale,labels in json.loads((ROOT/"data/blog-date-labels.json").read_text(encoding="utf-8")).items()
}

GALLERY_FALLBACK_TITLES={
    locale:entry["title"]
    for locale,entry in json.loads((ROOT/"data/gallery-short-titles.json").read_text(encoding="utf-8")).items()
}

def correct_reviewed_drinkware_terms(markup,locale):

    """Repair identified false-friend translations without altering SKU/specs.

    Rendered local HTML only: original D1 copy remains untouched.

    Plastic drinkware is neither liquid beverages nor a mechanical variator.

    """

    changes={

        "es":[("variadores de plástico","botellas de plástico"),

              ("bebidas de plástico","botellas de plástico")],

        "pt":[("bebidas de plástico","garrafas de plástico")],

    }

    for incorrect,correct in changes.get(locale,[]):

        pat=re.compile(re.escape(incorrect),re.I)

        def replacement(match):

            raw=match.group()

            if raw.isupper():return correct.upper()

            if raw[:1].isupper():return correct[:1].upper()+correct[1:]

            return correct

        markup=pat.sub(replacement,markup)

    return markup

def dedupe_catalog_cards(body):
    """Keep one localized product card per href before catalog enrichers run."""
    seen=set()
    pattern=re.compile(r'<a\b[^>]*\bdata-product-card\b[^>]*>[\s\S]*?</a>',re.I|re.S)
    def replace(match):
        card=match.group(0)
        opening=card.split(">",1)[0]
        href=re.search(r'\bhref=["\']([^"\']+)["\']',opening,re.I)
        if not href:
            return card
        url=href.group(1)
        if url in seen:
            return ""
        seen.add(url)
        return card
    return pattern.sub(replace,body)

def _localized_blog_card(slug,locale,fields,source):
    """Build a missing index card from the reviewed D1 article record."""
    title=str((fields or {}).get("title") or (source or {}).get("title") or "").strip()
    description=str((fields or {}).get("description") or (source or {}).get("description") or "").strip()
    cover=str((source or {}).get("cover") or "").strip()
    main=str((fields or {}).get("mainHtml") or "")
    cover_match=re.search(r'<div class="blog-detail__cover"><img\b[^>]*\bsrc="([^"]+)"',main,re.I)
    if cover_match and cover_match.group(1).startswith("/"):
        cover=cover_match.group(1)
    if not cover.startswith("/"):
        cover="/media/blog/"+cover.lstrip("/")
    prefix="/"+locale
    url=prefix+"/blog/"+slug+"/"
    category=html.escape(str((source or {}).get("group") or "BUYER RESOURCES").upper())
    return ('<article class="news-card"><a class="news-card__image" href="'+html.escape(url,quote=True)+'">'
            '<img src="'+html.escape(cover,quote=True)+'" alt="'+html.escape(title,quote=True)+'" loading="lazy"></a>'
            '<div class="news-card__info"><span class="news-card__category">'+category+'</span>'
            '<h3><a href="'+html.escape(url,quote=True)+'">'+html.escape(title)+'</a></h3>'
            '<p>'+html.escape(description)+'</p><a class="news-card__read" href="'+html.escape(url,quote=True)+'">Read Article →</a></div></article>')

def sort_localized_blog_index(body,ordered_slugs,replacements=None):
    """Order all localized cards by D1 and fill cards missing from an old index override."""
    if not ordered_slugs:
        return body
    replacements=replacements or {}
    cards=list(re.finditer(r'<article class="news-card">[\s\S]*?</article>',body,re.I))
    parsed=[]
    for match in cards:
        links=re.findall(r'href=["\']/((?:[a-z0-9_-]+/)?blog/([a-z0-9]+(?:-[a-z0-9]+)*)/)["\']',match.group(0),re.I)
        slugs={slug for _,slug in links}
        if len(slugs)!=1:
            return body
        slug=next(iter(slugs))
        if any(item[0]==slug for item in parsed):
            return body
        parsed.append((slug,match.group(0)))
    by_slug=dict(parsed)
    missing=[slug for slug in ordered_slugs if slug not in by_slug]
    if any(slug not in replacements for slug in missing):
        return body
    ordered_cards=[by_slug.get(slug) or replacements[slug] for slug in ordered_slugs]
    actual=[slug for slug,_ in parsed]
    if not missing and actual==list(ordered_slugs):
        return body
    if cards:
        separator=body[cards[0].end():cards[1].start()] if len(cards)>1 else "\n"
        replacement=separator.join(ordered_cards)
        return body[:cards[0].start()]+replacement+body[cards[-1].end():]
    grid=re.search(r'(<div class="blog-listing__grid">)([\s\S]*?)(</div>)',body,re.I)
    if not grid:
        return body
    replacement="\n".join(ordered_cards)
    return body[:grid.start(2)]+replacement+body[grid.end(2):]

def relocate_product_intro(body):
    """Move the existing product intro below the full two-column product block.

    Preserve translated/editor-owned copy exactly; only change its layout position.
    """
    h1=re.search(r"<h1\b[^>]*>.*?</h1>",body,re.I|re.S)
    if not h1:
        return body
    rest=body[h1.end():]
    intro=re.match(r'\s*(<p\b[^>]*class="[^"]*\bcopy-muted\b[^"]*"[^>]*>.*?</p>)\s*(?=<table\b)',rest,re.I|re.S)
    if not intro:
        return body
    paragraph=html.unescape(intro.group(1))
    body=body[:h1.end()]+rest[intro.end():]
    if '<div class="product-detail__lead">' in body:
        return body
    start=body.find('<div class="product-detail">')
    if start<0:
        return body
    depth=0
    closing_end=None
    for match in re.finditer(r'<div\b[^>]*>|</div>',body[start:],re.I):
        token=match.group(0)
        if token.lower().startswith('</div'):
            depth-=1
            if depth==0:
                closing_end=start+match.end()
                break
        else:
            depth+=1
    if closing_end is None:
        raise RuntimeError("Cannot locate matching product-detail closing div")
    return body[:closing_end]+'<div class="product-detail__lead">'+paragraph+'</div>'+body[closing_end:]

# CMS-owned Blog translations may use direct or wrapped timeline markup.
def localize_blog_timeline(body,original,locale,route):

    """Reflect actual source publication/review dates in the translated page.

    Localized D1 HTML predates the truthful publication-vs-review distinction.

    Read dates from the canonical article HEAD; never backdate or guess dates.

    """

    if not re.fullmatch(r"/blog/[a-z0-9-]+/",route):return body

    def dated(key):

        match=re.search(r'<meta property="article:'+key+r'_time" content="(\d{4}-\d{2}-\d{2})">',original)

        return match.group(1) if match else None

    published,modified=dated("published"),dated("modified")

    if not published:return body  # No verified source date: preserve approved D1 copy.

    first,reviewed=LOCALIZED_DATE_LABELS[locale]

    timeline='<time datetime="'+published+'">'+html.escape(first)+" "+published+"</time>"

    if modified and modified>published:

        timeline+=' · <time datetime="'+modified+'">'+html.escape(reviewed)+" "+modified+"</time>"

    updated,count=re.subn(r'(<div class="blog-meta">\s*<span>[^<]*</span>\s*)(?:<span>.*?</span>|<time\b[^>]*>.*?</time>)(\s*</div>)',
        lambda match:match.group(1)+'<span>'+timeline+'</span>'+match.group(2),body,count=1,flags=re.S)

    if count!=1:raise RuntimeError("Cannot update localized blog date safely: "+locale+" "+route)

    return updated

BLOG_BYLINES={
    "en":"By XUYI Bottles · Product Sourcing Editorial Team",
    "es":"Por XUYI Bottles · Equipo editorial de abastecimiento de productos",
    "pt":"Por XUYI Bottles · Equipa editorial de aprovisionamento de produtos",
    "ru":"XUYI Bottles · Редакционная команда по подбору продукции",
    "tr":"XUYI Bottles · Ürün tedarik editör ekibi",
}
def localize_blog_byline(body,locale,route):
    """Keep the visible author line in the same language as the article."""
    if not re.fullmatch(r"/blog/[a-z0-9-]+/",route):return body
    label=html.escape(BLOG_BYLINES.get(locale,BLOG_BYLINES["en"]))
    pattern=r'(<p class="blog-author-byline"><a\b[^>]*>).*?(</a></p>)'
    updated,count=re.subn(pattern,lambda match:match.group(1)+label+match.group(2),body,count=1,flags=re.S)
    return updated if count else body

def dedupe_localized_blog_sections(body,route):
    """Hide exact repeated long section copy at render time.

    Existing translated D1 HTML is still the source record; this is a
    deterministic presentation guard for records created before the batch
    publisher learned to normalize section paragraphs. It only removes an
    identical long paragraph from a later ``blog-section`` and never touches
    headings, FAQ answers, tables, links, or other article regions.
    """
    if not re.fullmatch(r"/blog/[a-z0-9-]+/",route):
        return body
    seen=set()
    pattern=re.compile(
        r'(<section class="blog-section"[^>]*>[\s\S]*?<p\b[^>]*>)([\s\S]*?)(</p>[\s\S]*?</section>)',
        re.I,
    )
    def replace(match):
        chunks=[chunk.strip() for chunk in re.split(r"\n\s*\n",match.group(2)) if chunk.strip()]
        kept=[]
        for chunk in chunks:
            plain=html.unescape(re.sub(r"<[^>]+>"," ",chunk))
            key=re.sub(r"\s+"," ",plain).strip().casefold()
            if len(key)>=80 and key in seen:
                continue
            if key:
                seen.add(key)
            kept.append(chunk)
        return match.group(1)+"\n\n".join(kept)+match.group(3)
    return pattern.sub(replace,body)

def localize_structured_data(markup,locale,route,localized,fields,approved_routes,path_prefix=None):

    """Match JSON-LD to the reviewed language page, never the English source.

    Product identifiers, images and the global legal Organization remain

    untouched; only page-local language, URLs and human-facing text change.

    Untranslated FAQ answers are dropped rather than represented as reviewed.

    """

    own=ORIGIN+localized

    source=ORIGIN+route

    h1match=re.search(r'<h1\b[^>]*>(.*?)</h1>',fields["mainHtml"],re.S|re.I)

    heading=html.unescape(re.sub(r'<[^>]*>',' ',h1match.group(1))).strip() if h1match else ""

    heading=re.sub(r'\s+',' ',heading) or fields["title"].split(" | ",1)[0]

    ui=UI_TRANSLATIONS.get(locale,{})

    def localize_item(item):

        if not isinstance(item,dict):return item

        typ=item.get("@type")

        if typ in ("FAQPage","ItemList"):return None  # regenerate from visible translated page

        if typ=="Organization":return item  # One globally identifiable legal company.

        if typ in ("Product","BlogPosting","Service","WebPage"):

            for key in ("@id","url"):

                if isinstance(item.get(key),str) and item[key].startswith(source):

                    item[key]=own+item[key][len(source):]

            if isinstance(item.get("mainEntityOfPage"),dict):

                x=item["mainEntityOfPage"]

                if isinstance(x.get("@id"),str) and x["@id"].startswith(source):

                    x["@id"]=own+x["@id"][len(source):]

            elif item.get("mainEntityOfPage")==source:item["mainEntityOfPage"]=own

            item["inLanguage"]=locale

            if typ=="BlogPosting":item["headline"]=fields["title"]

            else:item["name"]=heading

            item["description"]=fields["description"]

        if typ=="BreadcrumbList":

            for crumb in item.get("itemListElement",[]):

                value=crumb.get("item","")

                if not isinstance(value,str) or not value.startswith(ORIGIN+"/"):continue

                original_route=value[len(ORIGIN):]

                if original_route in approved_routes:

                    crumb["item"]=ORIGIN+"/"+(path_prefix or locale)+original_route

                    if original_route=="/":crumb["name"]=ui.get("Home",crumb.get("name","Home"))

                    elif original_route==route:crumb["name"]=heading

                    elif original_route=="/products/":crumb["name"]=ui.get("Products",crumb.get("name","Products"))

                    elif original_route=="/blog/":crumb["name"]=ui.get("Blog",crumb.get("name","Blog"))

        return item

    def replace(match):

        try:data=json.loads(match.group(1))

        except (ValueError,TypeError) as exc:raise RuntimeError("Invalid source JSON-LD: "+route) from exc

        if not isinstance(data,dict):raise RuntimeError("JSON-LD root must be an object: "+route)

        if isinstance(data.get("@graph"),list):

            data["@graph"]=[v for raw in data["@graph"] if (v:=localize_item(raw)) is not None]

        else:

            data=localize_item(data)

            if data is None:return ""

        return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")+'</script>'

    return re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>',replace,markup)

def translate_chrome(chunk,locale,ui_override=None):

    mappings={**UI_TRANSLATIONS.get(locale,{})}

    if isinstance(ui_override,dict):

        mappings.update({key:value for key,value in ui_override.items()

                         if key in mappings and isinstance(value,str) and value.strip()})

    # Translate exact shared header/footer text and human-facing alt,

    # aria-label, placeholder and title values. Never edit href/src/IDs.

    def replace(match):

        content=match.group(1)

        leading=content[:len(content)-len(content.lstrip())]

        trailing=content[len(content.rstrip()):]

        value=html.unescape(content.strip())

        translated=mappings.get(value)

        if not translated:return match.group(0)

        return ">"+leading+html.escape(translated)+trailing+"<"

    chunk=re.sub(r">([^<>]+)<",replace,chunk)

    def attribute(match):

        old=html.unescape(match.group(2))

        translated=mappings.get(old)

        if not translated:return match.group(0)

        return match.group(1)+'="'+html.escape(translated,quote=True)+'"'

    return re.sub(r'\b(aria-label|alt|placeholder|title)="([^"]*)"',attribute,chunk)

def valid_route(route):

    return isinstance(route,str) and (route=="/" or re.fullmatch(r"/(?:[a-z0-9_-]+/)+",route) is not None)

def swap_meta(page,name,value):

    tag='<meta name="'+name+'" content="'

    return re.sub(re.escape(tag)+r'[^"]*">',tag+html.escape(value,quote=True)+'">',page,count=1)

def localize_verified_links(markup, locale, path_prefix, published_routes):

    """Keep navigation on the current locale only where approved pages exist.

    Unknown targets intentionally fall back to the English source page; never

    create translated-looking links that lead to a 404 or an unreviewed page.

    """

    prefix = "/" + path_prefix.strip("/")

    def replace(match):

        raw = html.unescape(match.group(2))

        parts = urlsplit(raw)

        if not raw.startswith("/") or raw.startswith("//") or parts.path not in published_routes:

            return match.group(0)

        target = prefix + parts.path

        if parts.query: target += "?" + parts.query

        if parts.fragment: target += "#" + parts.fragment

        return match.group(1) + html.escape(target, quote=True) + match.group(3)

    return re.sub(r'(<a\b[^>]*?\bhref=")([^"]+)(")', replace, markup, flags=re.I)

CONTACT_FORM_TRANSLATIONS=json.loads((ROOT/"data/contact-form-translations.json").read_text(encoding="utf-8"))

def localized_contact_body(original, translated_body, locale):

    """Use the SAME inquiry form fields as English, with translated labels.

    The D1 page translation contains safe static HTML, intentionally without

    a <form>. This build-stage component restores the shared form structure

    without granting D1 untrusted translations the ability to inject forms.

    The existing front-end + server SMTP readiness gates remain authoritative.

    """

    original_body=original.split('<main id="main-content">',1)[1].split("</main>",1)[0]

    english=re.search(r'<form class="form" id="inquiry"[\s\S]*?</form>',original_body)

    if not english:raise RuntimeError("English contact form missing")

    form=english.group(0)

    translations=CONTACT_FORM_TRANSLATIONS[locale]

    # Make stable option values independent of their translated visible text.

    form=re.sub(r'<option>([^<]+)</option>',

        lambda m:'<option value="'+html.escape(html.unescape(m.group(1)),quote=True)+'">'+m.group(1)+'</option>',form)

    def translate_node(match):

        source=html.unescape(match.group(1).strip())

        if not source or source not in translations:return match.group(0)

        original_text=match.group(1)

        before=original_text[:len(original_text)-len(original_text.lstrip())]

        after=original_text[len(original_text.rstrip()):]

        return '>'+before+html.escape(translations[source])+after+'<'

    form=re.sub(r'>([^<>]+)<',translate_node,form)

    form=re.sub(r'(aria-label|placeholder)="([^"]+)"',

        lambda m:m.group(1)+'="'+html.escape(translations.get(html.unescape(m.group(2)),html.unescape(m.group(2))),quote=True)+'"',form)

    # Remove the earlier machine-translation fallback block, not the bilingual

    # company contacts, their data-site-* attributes, or the surrounding grid.

    fallback=r'<section class="section"><div class="shell"><h2>[\s\S]*?</section>(?=</div></div></section>\s*$)'

    updated,count=re.subn(fallback,lambda _:form,translated_body,count=1)

    if count!=1:raise RuntimeError("Localized contact fallback block mismatch for "+locale)

    # The D1-reviewed foreign-language body predates the visible-number design.

    # Reuse the actual English contact number without changing the approved

    # translation or weakening the safe-form/HTML checks.

    source=re.search(r'<a\b(?=[^>]*\bdata-site-whatsapp-number\b)[^>]*>([^<]+)</a>',original_body)

    number=re.search(r'\+\d[\d ]{7,}',html.unescape(source.group(1))) if source else None

    if not number:raise RuntimeError("English contact WhatsApp number missing")

    def add_number(match):

        attrs=match.group(1)

        if "data-site-whatsapp-number" not in attrs:attrs+=" data-site-whatsapp-number"

        label=match.group(2).rstrip()

        arrow=" →" if label.endswith("→") else ""

        if arrow:label=label[:-1].rstrip()

        return attrs+">"+label+" · "+html.escape(number.group(0).strip())+arrow+"</a>"

    updated,count=re.subn(r'(<a\b(?=[^>]*\bdata-site-whatsapp\s)[^>]*)(?:>)([^<]+)</a>',add_number,updated,count=1)

    if count!=1:raise RuntimeError("Translated contact WhatsApp link missing: "+locale)

    return updated

def main():

    if not SNAPSHOT.is_file():

        print("XUYI_LOCALES_SKIPPED: no reviewed D1 snapshot")

        return

    data=json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    if data.get("site")!="xuyi-drinkware-site":raise RuntimeError("Wrong locale source site")

    languages=(data.get("languages") or {}).get("languages",[])

    ready=approved_locales(data)

    # Preserve D1-reviewed UI copy while getting the supported code and URL

    # prefix solely from the registry; no es/pt/ru/tr enumeration here.

    original={r.get("code"):r for r in languages}

    live={r["code"]:{**original.get(r["code"],{}),**r}

          for r in ready if r["code"]!="en"}

    translated={}
    blog_order=[str(row.get("slug")) for row in data.get("blogPosts",[])
                if isinstance(row,dict) and row.get("status")=="published"
                and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",str(row.get("slug","")))]
    if len(blog_order)!=len(set(blog_order)):
        raise RuntimeError("D1 Blog snapshot contains duplicate published slugs")
    blog_sources={str(row.get("slug")):row for row in data.get("blogPosts",[])
                  if isinstance(row,dict) and isinstance(row.get("slug"),str)}
    source_generated_routes=set()

    for item in data.get("translations",[]):

        rid=item.get("resourceId","")

        if not rid.startswith("page:"):continue

        from product_slug_fix import route as canonical_product_route

        route=canonical_product_route(rid[5:]);loc=item.get("locale");fields=item.get("content") or {}

        if not valid_route(route) or loc not in live:continue

        if not all(isinstance(fields.get(k),str) and fields[k].strip() for k in ("title","description","mainHtml")):continue

        body=fields["mainHtml"]

        if len(body)<120 or re.search(r"<\s*(?:script|iframe|object|embed|form|style|link|base|meta|svg|math|template)\b|\bon[a-z-]+\s*=|\bsrcdoc\s*=|(?:javascript|vbscript|data)\s*:",body,re.I):continue

        src=DIST/route.lstrip("/")/"index.html"

        if route=="/":src=DIST/"index.html"

        if src.is_file():

            # A newer D1 edit stored under the clean route wins over the

            # old imported Chinese-variant URL record, independent of order.

            direct=(rid[5:]==route)

            if direct or (route,loc) not in translated:

                translated[(route,loc)]=fields

    # Reviewed source-photo LO additions have their own five-language native

    # content and SEO copy. Existing D1 translations always win, and no older

    # page translation is changed or auto-translated.

    from lo_catalog import LO_PRODUCTS,detail as lo_detail

    from site_renderer import SERIES

    for row in LO_PRODUCTS:

        model=row["model"]

        route="/products/"+row["slug"]+"/"

        src=DIST/route.lstrip("/")/"index.html"

        # Partial isolated translation fixtures contain only selected source

        # routes. Production builds always include all LO pages.

        if not src.is_file():continue

        for loc in live:

            if (route,loc) not in translated:

                copy=row["locales"][loc]

                translated[(route,loc)]={

                    "title":copy["seoTitle"],"description":copy["seoDescription"],

                    "mainHtml":lo_detail(SERIES[model],loc)}

    # G-series numbers ARE factory model IDs. Do not invent their currently

    # unprovided per-SKU capacity, material, packaging or test specifications.

    from gallery_catalog import GALLERY,detail as gallery_detail,LABELS as gallery_labels

    for row in GALLERY:

        route="/products/"+row["slug"]+"/"

        src=DIST/route.lstrip("/")/"index.html"

        if not src.is_file():continue

        for loc in live:

            if (route,loc) not in translated:

                name=row["locales"][loc]

                translated[(route,loc)]={

                    "title":(name+" | "+row["model"]+" | XUYI") if len(name+" | "+row["model"]+" | XUYI")<=60 else (GALLERY_FALLBACK_TITLES[loc]+" "+row["model"]+" | XUYI"),

                    "description":name+". "+gallery_labels[loc][2],

                    "mainHtml":gallery_detail(SERIES[row["model"]],loc)}

    # New factory models have reviewed English source data but no D1 locale
    # entries yet. Generate model-specific native pages only where D1 is absent.
    from factory_product_locales import SOURCE_DOCUMENTS as FACTORY_SOURCE_DOCUMENTS, translation_for as factory_translation_for
    from site_renderer import SERIES
    for product in SERIES.values():
        if product.get("manualNew") is not True or product.get("sourceDocument") not in FACTORY_SOURCE_DOCUMENTS:
            continue
        route="/products/"+str(product.get("slug") or product.get("model"))+"/"
        src=DIST/route.lstrip("/")/"index.html"
        if not src.is_file():
            continue
        for loc in live:
            if (route,loc) not in translated:
                translated[(route,loc)]=factory_translation_for(product,loc,SERIES)
                source_generated_routes.add((route,loc))

    # D1-published catalogs are fixed HTML snapshots; add only the eight

    # source-verified LO cards to their native-language grids, without

    # replacing the approved surrounding content.

    from lo_catalog import catalog_cards

    from gallery_catalog import catalog_cards as gallery_catalog_cards

    for loc in live:

        if ("/",loc) not in translated:

            raise RuntimeError("Refusing to publish "+loc+" without a reviewed localized homepage")

    routes_by_locale = {locale: {route for route, lang in translated if lang == locale}

                        for locale in live}

    created=0

    for (route,loc),fields in translated.items():

        original_owner_body=fields.get("mainHtml")

        # Apply known photo corrections before localized CMS HTML rendering.

        # Only unchanged legacy covers are affected; admin edits take priority.

        if route.startswith("/blog/"):

            from blog_media_source import blog_cover_from_cms_source

            fields={**fields,"mainHtml":blog_cover_from_cms_source(fields["mainHtml"],route,loc)}

        # Blog list: normalize only the reviewed legacy secondary title.

        # This changes the source render, never dist or the CMS record.

        if route=="/blog/":

            from blog_listing_layout import single_blog_index_heading

            fields={**fields,"mainHtml":single_blog_index_heading(fields["mainHtml"],loc)}
            fallback_cards={
                slug:_localized_blog_card(
                    slug,loc,translated.get(("/blog/"+slug+"/",loc),{}),blog_sources.get(slug,{})
                )
                for slug in blog_order
            }
            fields={**fields,"mainHtml":sort_localized_blog_index(fields["mainHtml"],blog_order,fallback_cards)}

        # Correct a reviewed Turkish bottle-cap false friend in D1 source

        # fields *before* constructing HTML, SEO, OG and JSON-LD. Owner-edited

        # D1 text takes precedence; do not patch rendered dist files.

        from turkish_bottle_cap_source import reviewed_turkish_bottle_caps

        fields=reviewed_turkish_bottle_caps(route,loc,fields)

        from spanish_reviewed_copy import reviewed_spanish_copy

        fields=reviewed_spanish_copy(route,loc,fields)

        if route.startswith("/blog/"):

            from blog_editorial_inline import reviewed_localized_article

            fields={**fields,"mainHtml":reviewed_localized_article(fields["mainHtml"],route,loc,source_original=original_owner_body)}

        from blog_meta_description_overrides import apply as apply_blog_meta_description_override
        fields=apply_blog_meta_description_override(fields,route,loc,translated)

        original=(DIST/route.lstrip("/")/"index.html" if route!="/" else DIST/"index.html").read_text(encoding="utf-8")

        if '<main id="main-content">' not in original:continue

        prefix,remainder=original.split('<main id="main-content">',1)

        _,suffix=remainder.split('</main>',1)

        ui=live[loc].get("uiText",{})

        # A small JSON bundle provides translations for the shared JavaScript

        # carousel, catalog filters, FAQ search and inquiry status messages.

        # This also prevents the homepage hero reverting to English on rotation.

        runtime=RUNTIME_UI_TRANSLATIONS.get(loc,{})

        encoded=json.dumps(runtime,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")

        prefix=prefix.replace("</head>",'<script type="application/json" id="xuyi-runtime-ui">'+encoded+"</script></head>",1)

        if route=="/about/":

            from about_company_page import source as about_source,apply_body,metadata_unchanged,baseline_body

            fields={**fields}

            owner_body_is_baseline=baseline_body(fields['mainHtml'],loc)

            fields['mainHtml']=apply_body(fields['mainHtml'],loc)

            if owner_body_is_baseline and metadata_unchanged(fields.get('title',''),fields.get('description',''),loc):

                fields['title']=about_source(loc)['title']

                fields['description']=about_source(loc)['description']

        # 2506 source capacity is unverified. Shorten only known factory

        # default title; D1 owner-rewritten titles retain absolute priority.

        if route=="/products/2506/":

            source_titles=json.loads((ROOT/"data/product-2506-short-titles.json").read_text(encoding="utf8"))["locales"]

            previous=source_titles.get(loc)

            if previous and fields["title"]==previous["original"]:

                fields={**fields,"title":previous["revised"]}

        body=(localized_contact_body(original,fields["mainHtml"],loc) if route=="/contact/" else fields["mainHtml"])

        if route=="/":

            from home_bpa_source import add_home_bpa_note

            body=add_home_bpa_note(body,loc)

        if route=="/why-us/":

            from why_us_source import augment as why_us_buyer_evidence

            body=why_us_buyer_evidence(body,loc)

        if route.startswith("/products/") and route!="/products/":

            from site_renderer import SERIES, PRODUCT_OVERRIDES

            from sku_unique_openings import editor_intro

            current_product=next((v for v in SERIES.values() if v["slug"]==route.split("/")[2]),None)

            if current_product is not None:

                body=editor_intro(body,current_product,loc)

                from sku_factual_sections import apply as verified_sku_sections

                body=verified_sku_sections(body,current_product,loc)
                # A D1 owner-selected SKU main photo is global across locales.
                # Older translated HTML may retain a previous catalog photo;
                # sync only the hero to the same reviewed source as Product.image.
                override=PRODUCT_OVERRIDES.get(str(current_product.get("model")),{})
                selected=override.get("image") if isinstance(override,dict) else None
                if isinstance(selected,str):
                    from product_image_sitemap import image_path
                    selected=image_path(selected,ORIGIN)
                    if selected:
                        pattern=r'(<img\b(?=[^>]*\bid="main-photo")[^>]*\bsrc=")[^"]+(")'
                        body,count=re.subn(pattern,lambda match:match.group(1)+selected+match.group(2),body,count=1,flags=re.I)
                        if count!=1:
                            raise RuntimeError("D1-selected main photo missing from localized product body: "+loc+" "+route)
        # Translated D1 body takes precedence; add common scenario-specific

        # buyer guidance inside the locale renderer before final HTML write.

        if route.startswith(("/applications/","/features/")):

            from curated_application_feature_answers import render_buyer_evidence

            body+=render_buyer_evidence(route,loc,body)

        if route.startswith("/blog/"):

            body=localize_blog_timeline(body,original,loc,route)
            body=localize_blog_byline(body,loc,route)
            body=dedupe_localized_blog_sections(body,route)

            # Do not append the legacy heuristic GEO block. Localized Blog
            # evidence must come from the translated D1/source-reviewed body.

        if route=="/products/" or route.startswith("/collections/"):

            body=dedupe_catalog_cards(body)

            body=gallery_catalog_cards(body,loc,route)

            body=catalog_cards(body,loc,route)

            body=factory_catalog_cards(body,loc,route,routes_by_locale[loc])

            body=dedupe_catalog_cards(body)

        if route=="/products/" or route.startswith("/collections/"):

            from catalog_crawlable_pagination import upgrade_localized_cms,upgrade_localized_catalog_navigation

            if route=="/products/":

                body=upgrade_localized_cms(body)

            body=upgrade_localized_catalog_navigation(

                body,loc,live[loc].get("pathPrefix",loc),

                UI_TRANSLATIONS.get(loc,{}),route

            )

        # Canonicalize only known broken transparent-variant hyperlinks.

        # Preserves owner-edited text, images, SEO and approved custom links.

        from product_slug_fix import normalize_local_links

        body=normalize_local_links(body)

        if route.startswith("/products/") and route!="/products/":

            # D1 translated bodies replace the English product HTML. Re-add

            # the same reviewed presentation module in this locale, without

            # touching the existing translated descriptions or SKU data.

            from site_renderer import SERIES

            model=route.removeprefix("/products/").strip("/")

            product=next((obj for obj in SERIES.values() if obj["slug"]==model),None)

            if product is None:raise ValueError("Missing material source for "+route)

            body=inject_materials(body,product,loc,route,routes_by_locale[loc])
            from scripts.source_catalog_capacity_oz import source_body_enrichment
            body=source_body_enrichment(body,loc,product)

            from collections import Counter

            from product_source_identity import source_product_identity

            body=source_product_identity(body,product,loc,Counter(x["images"][0] for x in SERIES.values()),allow_unbaselined=(route,loc) in source_generated_routes)

            from g_series_material_options import render_g_material_options

            body+=render_g_material_options(route,loc,body)

            # The D1-authored product introduction belongs immediately after H1; do not relocate it.

        # The homepage body is a D1-approved translation of previous English

        # markup. Refresh ONLY the immutable generic hero image asset; leave

        # all user-translated text and model photos unchanged.

        if route=="/":

            from media_quality_guard import upgrade_home_visual

            body=upgrade_home_visual(body,loc)

            from home_intro_source_photo import reviewed_home_intro_photo

            body=reviewed_home_intro_photo(body)

            prefix,count=re.subn(r'<script type="application/json" id="xuyi-home-banners">[^<]*</script>',

              lambda _:banner_tag(data,loc,routes_by_locale[loc]),prefix,count=1)

            if count!=1:raise RuntimeError("English homepage must have exactly one banner configuration")

            slide=banner_slides(data,loc,routes_by_locale[loc])[0]

            heading=html.escape(slide["title"])+" <span>"+html.escape(slide["highlight"])+"</span>"

            body=re.sub(r'(<h1\b[^>]*\bid="hero-title"[^>]*>).*?(</h1>)',

              lambda m:m.group(1)+heading+m.group(2),body,count=1,flags=re.S)

            body=re.sub(r'(<p\b[^>]*\bid="hero-description"[^>]*>).*?(</p>)',

              lambda m:m.group(1)+html.escape(slide["description"])+m.group(2),body,count=1,flags=re.S)

            body=re.sub(r'(<a\b(?=[^>]*\bid="hero-cta")[^>]*>).*?(</a>)',

              lambda m:m.group(1)+html.escape(slide["cta"])+m.group(2),body,count=1,flags=re.S)

            body=re.sub(r'(<img\b(?=[^>]*\bid="hero-image")[^>]*\balt=")[^"]+(")',

              lambda m:m.group(1)+html.escape(slide["alt"])+m.group(2),body,count=1)

            body=re.sub(r'(<img\b(?=[^>]*\bid="hero-image")[^>]*\bsrc=")[^"]+(")',

              lambda m:m.group(1)+html.escape(slide["img"])+m.group(2),body,count=1)

            body=re.sub(r'(<a\b(?=[^>]*\bid="hero-cta")[^>]*\bhref=")[^"]+(")',

              lambda m:m.group(1)+html.escape(slide["link"])+m.group(2),body,count=1)

        if route=="/":

            # Selected the final hero slide; now reserve its image geometry.

            from home_source_image_geometry import source_image_geometry

            body=source_image_geometry(body,route,loc)

        text=translate_chrome(prefix,loc,ui)+'<main id="main-content">'+body+'</main>'+translate_chrome(suffix,loc,ui)

        text=localize_verified_links(text,loc,live[loc].get("pathPrefix",loc),routes_by_locale[loc])
        text=dedupe_catalog_cards(text)
        from site_renderer import SERIES
        from scripts.source_catalog_capacity_oz import enrich_catalog_body
        text=enrich_catalog_body(text,loc,SERIES)

        text=text.replace('<html lang="en">','<html lang="'+loc+'">',1)

        text=re.sub(r'<title>[^<]*</title>','<title>'+html.escape(fields["title"])+'</title>',text,count=1)

        text=swap_meta(text,"description",fields["description"])

        for property_name,value in (("og:title",fields["title"]),("og:description",fields["description"])):

            tag='<meta property="'+property_name+'" content="'+html.escape(value,quote=True)+'">'

            current=r'<meta property="'+property_name+'" content="[^"]*">'

            if re.search(current,text):text=re.sub(current,lambda _:tag,text,count=1)

            else:text=text.replace("</head>",tag+"</head>",1)

        localized="/"+live[loc]["pathPrefix"]+(route if route!="/" else "/")

        localized=re.sub("/+","/",localized)

        canonical=ORIGIN+localized

        text=re.sub(r'<link rel="canonical" href="[^"]*">','<link rel="canonical" href="'+canonical+'">',text,count=1)

        text=re.sub(r'<meta property="og:url" content="[^"]*">','<meta property="og:url" content="'+canonical+'">',text,count=1)

        text=localize_structured_data(text,loc,route,localized,fields,routes_by_locale[loc],live[loc]["pathPrefix"])

        # Reflect the final D1/CMS localized Blog cover into OG/BlogPosting

        # at the source render boundary, never after dist is generated.

        if route.startswith("/blog/") and route!="/blog/":

            from blog_media_source import article_social_image_from_cms_source

            text=article_social_image_from_cms_source(text,route)

        text=polish_product_head(text,loc,route)

        text=correct_reviewed_drinkware_terms(text,loc)

        text=polish_image_alt(text,loc)

        text=apply_media_alts(text,data,loc)

        if route.startswith('/products/') and route!='/products/':

            from source_catalog_capacity_oz import pre_render_verified_meta

            from site_renderer import SERIES

            model=route.removeprefix('/products/').strip('/')

            source_row=next((v for v in SERIES.values() if v['slug']==model),None)

            if source_row:text=pre_render_verified_meta(text,loc,source_row,data)

        # Build visible FAQs and product card listings from the approved

        # translated D1 body during rendering; never patch generated pages.

        # Product/FAQ/WebPage and trust metadata are finalized after D1 SEO overrides.

        from search_intent_roles import render_search_intent

        text=render_search_intent(text,route,loc)

        # Enhance the D1-approved HTML at the locale source-render stage.

        from responsive_image_render import enhance_source_markup

        text=enhance_source_markup(text)

        # Source-render public, SKU-matched customer reviews from D1.

        if route.startswith("/products/") and route!="/products/":

            from site_renderer import SERIES

            from product_reviews_source import at_product_source

            sku=route.removeprefix("/products/").strip("/")

            product=next((v for v in SERIES.values() if v["slug"]==sku),None)

            if product:text=at_product_source(text,product["model"],loc,data)

            # D1 product SEO outranks every older localized/static fallback.

            if product:

                from product_seo_d1_source import apply_d1_product_seo
                text=apply_d1_product_seo(text,product["slug"],loc,data)
        from scripts.reviewed_editorial_images import apply_to_document as apply_reviewed_editorial_images
        text=apply_reviewed_editorial_images(text,localized,loc)
        from scripts.reviewed_lowres_editorial_round2 import apply_to_document as apply_reviewed_lowres_images
        text=apply_reviewed_lowres_images(text,localized,loc)
        from scripts.repair_mismatched_sports_category import apply_to_document as repair_sports_category_image
        text=repair_sports_category_image(text,localized,loc)
        from scripts.repair_remaining_category_cards import apply_to_document as repair_remaining_category_images
        text=repair_remaining_category_images(text,localized,loc)
        from scripts.apply_gpt_reviewed_shaker_hd import apply_to_document as apply_approved_product_images
        text=apply_approved_product_images(text,localized,loc)
        from responsive_image_render import promote_primary_blog_image
        if route.startswith('/blog/') and route!='/blog/':text=promote_primary_blog_image(text)
        text=enhance_source_markup(text, include_legacy=True)
        from scripts.polish_priority_seo import apply_to_document as apply_priority_seo
        text=apply_priority_seo(text,localized,loc)
        from scripts.curated_buyer_seo_round2 import apply_to_document as apply_curated_buyer_seo
        text=apply_curated_buyer_seo(text,localized,loc)
        from scripts.buyer_journey_internal_links import apply_to_document as apply_buyer_journey_links
        text,_=apply_buyer_journey_links(text,localized,loc)
        from seo_structured_components import add_at_render
        text=add_at_render(text,localized,loc)
        from scripts.contextual_share_metadata import apply_to_document as apply_contextual_share_preview
        text,_=apply_contextual_share_preview(text,localized,loc)
        from scripts.verified_trust_technical_seo import add_at_render as add_trust_technical_seo
        text=add_trust_technical_seo(text,localized,loc)
        from scripts.product_hreflang import apply_to_document as apply_product_hreflang
        text=apply_product_hreflang(text,localized,loc,languages)
        # Re-apply at the final document boundary so later SEO/enrichment
        # helpers cannot reintroduce a different localized card sequence.
        if route=="/blog/":
            text=sort_localized_blog_index(text,blog_order)
        dest=DIST/localized.lstrip("/")/"index.html";dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(text,encoding="utf-8")

        if route.startswith("/products/") and route!="/products/":
            # The localized image sitemap must use the final rendered D1-selected hero.
            translated[(route,loc)]={**fields,"mainHtml":body}
        created+=1

    # Only link routes that really exist in the generated release.

    alternates={}

    for route,loc in translated:

        prefix=live[loc]["pathPrefix"]

        dest=DIST/prefix/route.lstrip("/")/"index.html"

        if dest.is_file():alternates.setdefault(route,[]).append((loc,"/"+prefix+route))

    for route,alts in alternates.items():
        if route.startswith("/products/"):
            continue  # Product hreflang was emitted by the shared source renderer.

        src=DIST/route.lstrip("/")/"index.html" if route!="/" else DIST/"index.html"

        for link in [src]+[DIST/url.lstrip("/")/"index.html" for _,url in alts]:

            content=link.read_text(encoding="utf-8")

            tags=['<link rel="alternate" hreflang="en" href="'+ORIGIN+route+'">']

            tags.extend('<link rel="alternate" hreflang="'+lang+'" href="'+ORIGIN+url+'">' for lang,url in sorted(alts))

            tags.append('<link rel="alternate" hreflang="x-default" href="'+ORIGIN+route+'">')

            content=content.replace('</head>',''.join(tags)+'</head>',1)

            link.write_text(content,encoding="utf-8")

    # English-only new D1 products/articles must remain publishable BEFORE

    # their foreign translations are approved. A self link + English default

    # is safe; NEVER advertise a foreign locale without its real HTML page.

    # Read the English sitemap rather than guessing source pages or admin URLs.

    english_xml=(DIST/"sitemap.xml").read_text(encoding="utf-8")

    published_prefixes={"/"+entry["pathPrefix"]+"/" for entry in ready if entry["pathPrefix"]}

    english_urls=[

        route for route in re.findall(r"<loc>"+re.escape(ORIGIN)+r"(/[^<]*)</loc>",english_xml)

        if not any(route.startswith(prefix) for prefix in published_prefixes)

    ]

    for route in english_urls:

        if route in alternates:continue

        src=DIST/route.lstrip("/")/"index.html" if route!="/" else DIST/"index.html"

        if not src.is_file():raise RuntimeError("English sitemap URL has no page: "+route)

        content=src.read_text(encoding="utf-8")

        tags=('<link rel="alternate" hreflang="en" href="'+ORIGIN+route+'">'

              '<link rel="alternate" hreflang="x-default" href="'+ORIGIN+route+'">')

        if '<link rel="alternate" hreflang=' in content:

            if content.count(tags)==1:continue # an idempotent second renderer run

            raise RuntimeError("Stale alternates on English-only route: "+route)

        src.write_text(content.replace("</head>",tags+"</head>",1),encoding="utf-8")

    # Extend the existing English sitemap with *real* reviewed routes only.

    # The site-wide noindex gate is independent and remains unchanged.

    sitemap=DIST/"sitemap.xml"

    if alternates and sitemap.is_file():

        xml=sitemap.read_text(encoding="utf-8")

        added=[]

        from sitemap_modification import source_lastmod,review_change_dates
        from site_renderer import SERIES,BUILD_STATE
        reviewed_date_changes=review_change_dates(SERIES,BUILD_STATE.get("productReviews",[]))
        for route,alts in sorted(alternates.items()):

            for _,url in sorted(alts):

                absolute=ORIGIN+url

                if "<loc>"+html.escape(absolute)+"</loc>" not in xml:

                    # The D1 translation is the authoritative locale content.

                    # Baseline records change only on significant editorial edits.

                    modified=source_lastmod(url,_,translated.get((route, _),{}),review_dates=reviewed_date_changes)

                    from product_image_sitemap import xml_image_for_product

                    # The translated D1 main photo takes precedence; do not

                    # manufacture different URLs for repeated source imagery.

                    owner_body=translated.get((route,_),{}).get("mainHtml")

                    image_xml=xml_image_for_product(route,SERIES,owner_body,ORIGIN)

                    added.append(" <url><loc>"+html.escape(absolute)+"</loc>"

                      +("<lastmod>"+modified+"</lastmod>" if modified else "")

                      +image_xml+"</url>")

        if added:

            if "</urlset>" not in xml:raise RuntimeError("Invalid XUYI sitemap: no urlset closing tag")

            xml=xml.replace("</urlset>","\n".join(added)+"\n</urlset>",1)

            sitemap.write_text(xml,encoding="utf-8")

    # Actual published output is authoritative; disabled/draft or missing

    # language pages must not become sitemap/hreflang entries.

    manifest={"schemaVersion":1,"site":"xuyi-drinkware-site","sourceLocale":"en",

              "defaultLocale":"en","origin":ORIGIN,"locales":ready,

              "routes":{lang["code"]:sorted(

                "/"+f.relative_to(DIST/(lang["pathPrefix"] or ".")).as_posix().removesuffix("index.html")

                for f in (DIST/(lang["pathPrefix"] or ".")).rglob("index.html")

                if (lang["code"]!="en" or f.relative_to(DIST).parts[0] not in

                    {x["pathPrefix"] for x in ready if x["code"]!="en"}|{"admin"}))

                for lang in ready}}

    (DIST/"locale-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print("XUYI_REVIEWED_LOCALIZED_PAGES",created,"LANGUAGES",sorted(live),"ALTERNATE_SETS",len(alternates))

if __name__=="__main__":main()


