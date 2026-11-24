"""Source-rendered Product, WebPage, Breadcrumb, FAQ and collection ItemList JSON-LD.

Only visible page content and reviewed catalog fields are used. No offers,
prices, stock, ratings, certification or performance claims are inferred.
"""
from __future__ import annotations
from html import unescape,escape as html_escape
import json
import re

ORIGIN="https://xuyibottles.com"
DETAIL=re.compile(r"<details\b[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>",re.I|re.S)
FAQ_LIST=re.compile(r'<div\b[^>]*class="[^"]*\bfaq-list\b[^"]*"[^>]*>(.*?)</div>',re.I|re.S)
BLOG_FAQ_SECTION=re.compile(r'<section\b[^>]*class="[^"]*\bblog-faq\b[^"]*"[^>]*>(.*?)</section>',re.I|re.S)
CARD=re.compile(r'<a\b(?=[^>]*\bdata-product-card\b)([^>]*?)>',re.I|re.S)
HREF=re.compile(r'\bhref="([^"]+)"',re.I)
JSONLD=re.compile(r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',re.I|re.S)

HOME={"en":"Home","es":"Inicio","pt":"Início","ru":"Главная","tr":"Ana sayfa"}
BLOG={"en":"Blog","es":"Blog","pt":"Blog","ru":"Блог","tr":"Blog"}
PRODUCTS={"en":"Products","es":"Productos","pt":"Produtos","ru":"Продукция","tr":"Ürünler"}
PROPERTY={
 "en":{"capacity":"Catalog capacity (mL)","oz":"Approximate US fl oz size class","material":"Catalog-listed material","dimensions":"Catalog dimensions","colors":"Catalog-listed colors","unit_weight":"Catalog unit weight","packing":"Unit packing","carton_quantity":"Units per master carton","carton_size":"Master carton size","carton_gross_weight":"Master carton gross weight"},
 "es":{"capacity":"Capacidad del catálogo (mL)","oz":"Clase aproximada de onzas líquidas US","material":"Material indicado en el catálogo","dimensions":"Dimensiones del catálogo","colors":"Colores indicados en el catálogo","unit_weight":"Peso unitario del catálogo","packing":"Embalaje unitario","carton_quantity":"Unidades por caja máster","carton_size":"Tamaño de caja máster","carton_gross_weight":"Peso bruto de caja máster"},
 "pt":{"capacity":"Capacidade do catálogo (mL)","oz":"Classe aproximada de onças fluidas US","material":"Material indicado no catálogo","dimensions":"Dimensões do catálogo","colors":"Cores indicadas no catálogo","unit_weight":"Peso unitário do catálogo","packing":"Embalagem unitária","carton_quantity":"Unidades por caixa master","carton_size":"Dimensão da caixa master","carton_gross_weight":"Peso bruto da caixa master"},
 "ru":{"capacity":"Объём по каталогу (мл)","oz":"Примерный класс жидких унций США","material":"Материал по каталогу","dimensions":"Размеры по каталогу","colors":"Цвета по каталогу","unit_weight":"Вес единицы по каталогу","packing":"Индивидуальная упаковка","carton_quantity":"Количество в транспортной коробке","carton_size":"Размер транспортной коробки","carton_gross_weight":"Вес брутто транспортной коробки"},
 "tr":{"capacity":"Katalog kapasitesi (mL)","oz":"Yaklaşık ABD sıvı ons sınıfı","material":"Katalogda belirtilen malzeme","dimensions":"Katalog ölçüleri","colors":"Katalog renkleri","unit_weight":"Katalog birim ağırlığı","packing":"Tekli ambalaj","carton_quantity":"Ana koli adedi","carton_size":"Ana koli ölçüsü","carton_gross_weight":"Ana koli brüt ağırlığı"},
}

def plain(markup):
    return re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",markup))).strip()

def visible_faq(page):
    body=page.split("<main",1)[-1].split("</main>",1)[0]
    group=FAQ_LIST.search(body)
    if not group:return []
    pairs=[(plain(q),plain(a)) for q,a in DETAIL.findall(group.group(1))]
    pairs=[(q,a) for q,a in pairs if len(q)>=8 and len(a)>=15]
    return pairs if len({q for q,a in pairs})==len(pairs) else []


def visible_blog_faq(page):
    body=page.split("<main",1)[-1].split("</main>",1)[0]
    group=BLOG_FAQ_SECTION.search(body)
    if not group:return []
    pairs=[(plain(q),plain(a)) for q,a in DETAIL.findall(group.group(1))]
    pairs=[(q,a) for q,a in pairs if len(q)>=8 and len(a)>=15]
    return pairs if len({q for q,a in pairs})==len(pairs) else []

def actual_product_cards(page):
    body=page.split("<main",1)[-1].split("</main>",1)[0]
    links=[]
    for match in CARD.finditer(body):
        href=HREF.search(match.group(1))
        if not href:continue
        url=unescape(href.group(1)).split("?",1)[0].split("#",1)[0]
        if not re.fullmatch(r"/(?:es/|pt/|ru/|tr/)?products/[a-z0-9_-]+/",url,re.I):continue
        if url not in links:links.append(url)
    return links

def _head_meta(page):
    head=page.split("</head>",1)[0]
    title=re.search(r"<title>(.*?)</title>",head,re.I|re.S)
    desc=re.search(r'<meta\s+name="description"\s+content="([^"]*)"',head,re.I)
    return (unescape(title.group(1)).strip() if title else "",
            unescape(desc.group(1)).strip() if desc else "")

def _localized_blog_keywords(page,locale):
    """Derive target-language Blog keywords from the final visible D1-rendered page.

    Non-English pages must not inherit the English primary_keyword list. The
    visible translated title, description, headings and FAQ questions are the
    only inputs, so new D1 articles and configured locales work automatically.
    """
    title,description=_head_meta(page)
    candidates=[title,description]
    for pattern in (
        r"<h1\b[^>]*>(.*?)</h1>",
        r"<h2\b[^>]*>(.*?)</h2>",
        r"<h3\b[^>]*>(.*?)</h3>",
        r"<summary\b[^>]*>(.*?)</summary>",
    ):
        candidates.extend(match.group(1) for match in re.finditer(pattern,page,re.I|re.S))
    values=[]
    for value in candidates:
        text=re.sub(r"<[^>]+>"," ",unescape(str(value or "")))
        text=re.sub(r"\s+"," ",text).strip(" \\t\\r\\n|·•")
        if len(text)<4 or text.casefold() in {item.casefold() for item in values}:
            continue
        values.append(text[:180])
        if len(values)>=10:
            break
    return ", ".join(values)

def _route_base(route,locale):
    base=str(route or "/")
    prefix="/"+locale
    if locale!="en" and base.startswith(prefix+"/"):
        base=base[len(prefix):]
    return base

def _raw_values(row,field):
    values=[]
    variants=row.get("variants") or []
    if isinstance(variants,dict):variants=list(variants.values())
    for item in variants:
        if not isinstance(item,dict):continue
        value=str(item.get(field) or "").strip()
        if not value:continue
        if value.lower() in {"n/a","na","not specified","not provided","unknown","tbd","to be confirmed","-","—","none"}:continue
        if value not in values:values.append(value)
    direct=str(row.get(field) or "").strip()
    if direct and direct.lower() not in {"n/a","na","not specified","not provided","unknown","tbd","to be confirmed","-","—","none"} and direct not in values:
        values.append(direct)
    return values[:5]

def _properties(row,locale):
    from scripts.source_catalog_capacity_oz import catalog_volume_numbers,volume_terms,verified_source_material,format_ml
    labels=PROPERTY[locale]
    props=[]
    numbers=catalog_volume_numbers(row)
    if numbers:
        props.append({"@type":"PropertyValue","name":labels["capacity"],"value":" / ".join(format_ml(n) for n in numbers)})
        props.append({"@type":"PropertyValue","name":labels["oz"],"value":volume_terms(numbers,locale)})
    material=verified_source_material(row)
    raw_material=_raw_values(row,"material")
    if material or raw_material:
        props.append({"@type":"PropertyValue","name":labels["material"],"value":material or " / ".join(raw_material)})
    for field in ("dimensions","colors","unit_weight","packing","carton_quantity","carton_size","carton_gross_weight"):
        values=_raw_values(row,field)
        if values:
            props.append({"@type":"PropertyValue","name":labels[field],"value":" / ".join(values)})
    return props

def _existing_schema(page):
    types=set()
    scripts=[]
    for match in JSONLD.finditer(page):
        try:obj=json.loads(match.group(2))
        except (ValueError,TypeError):continue
        nodes=obj.get("@graph",[]) if isinstance(obj,dict) and isinstance(obj.get("@graph"),list) else [obj]
        for node in nodes:
            if isinstance(node,dict):
                kind=node.get("@type")
                if isinstance(kind,str):types.add(kind)
                elif isinstance(kind,list):types.update(kind)
        scripts.append((match,obj))
    return types,scripts

def _update_existing(page,canonical,locale,title,description,product_id,breadcrumb_id,webpage_id,sku,properties,images):
    def update(match):
        try:obj=json.loads(match.group(2))
        except (ValueError,TypeError):return match.group(0)
        nodes=obj.get("@graph",[]) if isinstance(obj,dict) and isinstance(obj.get("@graph"),list) else [obj]
        changed=False
        for node in nodes:
            if not isinstance(node,dict):continue
            kind=node.get("@type")
            if kind=="Product":
                for key,value in (("@id",product_id),("url",canonical),("sku",sku),("name",title),("description",description)):
                    if value and node.get(key)!=value:node[key]=value;changed=True
                if not node.get("brand"):node["brand"]={"@type":"Brand","name":"XUYI Bottles"};changed=True
                existing=node.get("additionalProperty") or []
                if isinstance(existing,dict):existing=[existing]
                if not isinstance(existing,list):existing=[]
                names={x.get("name") for x in existing if isinstance(x,dict)}
                for prop in properties:
                    if prop["name"] not in names:existing.append(prop);changed=True
                if existing:node["additionalProperty"]=existing
                if images:
                    if node.get("image")!=images:
                        node["image"]=images;changed=True
                elif "image" in node:
                    node.pop("image",None);changed=True
            elif kind=="BreadcrumbList":
                prefix="" if locale=="en" else "/"+locale
                expected_items=[
                    {"@type":"ListItem","position":1,"name":HOME[locale],"item":ORIGIN+prefix+"/"},
                    {"@type":"ListItem","position":2,"name":PRODUCTS[locale],"item":ORIGIN+prefix+"/products/"},
                    {"@type":"ListItem","position":3,"name":sku,"item":canonical},
                ]
                if node.get("@id")!=breadcrumb_id:
                    node["@id"]=breadcrumb_id
                    changed=True
                if node.get("itemListElement")!=expected_items:
                    node["itemListElement"]=expected_items
                    changed=True
            elif kind=="WebPage":
                for key,value in (("@id",webpage_id),("url",canonical),("name",title),("description",description),("inLanguage",locale)):
                    if value and node.get(key)!=value:node[key]=value;changed=True
                if product_id and node.get("mainEntity")!={"@id":product_id}:
                    node["mainEntity"]={"@id":product_id};changed=True
                if breadcrumb_id and node.get("breadcrumb")!={"@id":breadcrumb_id}:
                    node["breadcrumb"]={"@id":breadcrumb_id};changed=True
        if not changed:return match.group(0)
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
        return match.group(1)+payload+match.group(3)
    return JSONLD.sub(update,page)

def _product_row(route,locale):
    base=_route_base(route,locale)
    match=re.fullmatch(r"/products/([a-z0-9_-]+)/",base,re.I)
    if not match:return None
    from site_renderer import SERIES
    slug=match.group(1)
    return next((row for row in SERIES.values() if row.get("slug")==slug),None)

def _approved_image_url(url):
    from scripts.apply_gpt_reviewed_shaker_hd import approved_image_url
    value=str(url or "")
    if value.startswith(ORIGIN+"/"):
        return ORIGIN+approved_image_url(value[len(ORIGIN):])
    return approved_image_url(value)

def _product_nodes(page,route,locale,row):
    from scripts.source_catalog_capacity_oz import _seo_kind
    canonical=ORIGIN+route
    title,description=_head_meta(page)
    h1=re.search(r"<h1\b[^>]*>(.*?)</h1>",page,re.I|re.S)
    product_name=plain(h1.group(1)) if h1 else title
    model=str(row.get("model") or row.get("factoryModel") or "")
    product_id=canonical+"#product"
    breadcrumb_id=canonical+"#breadcrumb"
    webpage_id=canonical+"#webpage"
    product={
      "@type":"Product","@id":product_id,"name":product_name,"sku":model,
      "description":description,"category":_seo_kind(locale,row),"url":canonical,
      "brand":{"@type":"Brand","name":"XUYI Bottles"},
      "additionalProperty":_properties(row,locale),
    }
    from product_share_source import real_product_images
    images=[_approved_image_url(path) for path in real_product_images(row)]
    if images:
        product["image"]=[ORIGIN+path if path.startswith("/") else path for path in images]
    prefix="" if locale=="en" else "/"+locale
    breadcrumb={"@type":"BreadcrumbList","@id":breadcrumb_id,"itemListElement":[
      {"@type":"ListItem","position":1,"name":HOME[locale],"item":ORIGIN+prefix+"/"},
      {"@type":"ListItem","position":2,"name":PRODUCTS[locale],"item":ORIGIN+prefix+"/products/"},
      {"@type":"ListItem","position":3,"name":model,"item":canonical},
    ]}
    webpage={"@type":"WebPage","@id":webpage_id,"url":canonical,"name":title,
      "description":description,"inLanguage":locale,"mainEntity":{"@id":product_id},
      "breadcrumb":{"@id":breadcrumb_id},"isPartOf":{"@id":ORIGIN+"/#website"}}
    faq_pairs=visible_faq(page)
    faq={"@type":"FAQPage","@id":canonical+"#product-faq","url":canonical,"inLanguage":locale,
      "mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faq_pairs]} if faq_pairs else None
    return product,breadcrumb,webpage,faq,product_id,breadcrumb_id,webpage_id

def _listing_nodes(page,route,locale):
    canonical=ORIGIN+route
    title,description=_head_meta(page)
    links=actual_product_cards(page)
    if not links:return []
    list_id=canonical+"#visible-product-list"
    itemlist={"@type":"ItemList","@id":list_id,"url":canonical,"inLanguage":locale,
      "numberOfItems":len(links),"itemListElement":[
        {"@type":"ListItem","position":i+1,"url":ORIGIN+url} for i,url in enumerate(links)]}
    prefix="" if locale=="en" else "/"+locale
    webpage={"@type":"WebPage","@id":canonical+"#webpage","url":canonical,
      "name":title,"description":description,"inLanguage":locale,
      "mainEntity":{"@id":list_id},"isPartOf":{"@id":ORIGIN+"/#website"}}
    return [itemlist,webpage]


def _blog_nodes(page,route,locale):
    canonical=ORIGIN+route
    title,description=_head_meta(page)
    prefix="" if locale=="en" else "/"+locale
    breadcrumb={"@type":"BreadcrumbList","@id":canonical+"#breadcrumb","itemListElement":[
        {"@type":"ListItem","position":1,"name":HOME.get(locale,HOME["en"]),"item":ORIGIN+prefix+"/"},
        {"@type":"ListItem","position":2,"name":BLOG.get(locale,BLOG["en"]),"item":ORIGIN+prefix+"/blog/"},
        {"@type":"ListItem","position":3,"name":title,"item":canonical},
    ]}
    pairs=visible_blog_faq(page)
    faq={"@type":"FAQPage","@id":canonical+"#faq","url":canonical,"inLanguage":locale,
         "mainEntity":[{"@type":"Question","name":q,
                       "acceptedAnswer":{"@type":"Answer","text":a}} for q,a in pairs]} if pairs else None
    return breadcrumb,faq

def _update_blog_keywords(page,keywords):
    if not keywords:
        return page
    def update(match):
        try:obj=json.loads(match.group(2))
        except (ValueError,TypeError):return match.group(0)
        nodes=obj.get("@graph",[]) if isinstance(obj,dict) and isinstance(obj.get("@graph"),list) else [obj]
        changed=False
        for node in nodes:
            if isinstance(node,dict) and node.get("@type") in {"BlogPosting","Article"}:
                if node.get("keywords")!=keywords:
                    node["keywords"]=keywords
                    changed=True
        if not changed:return match.group(0)
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
        return match.group(1)+payload+match.group(3)
    page=JSONLD.sub(update,page)
    escaped=html_escape(keywords,quote=True)
    meta=re.compile(r"""<meta\s+name=["']keywords["'][^>]*>""",re.I)
    replacement='<meta name="keywords" content="'+escaped+'">'
    if meta.search(page):
        return meta.sub(replacement,page,count=1)
    return page.replace("</head>",replacement+"</head>",1)

def _update_blog_breadcrumb(page,breadcrumb):
    def update(match):
        try:obj=json.loads(match.group(2))
        except (ValueError,TypeError):return match.group(0)
        nodes=obj.get("@graph",[]) if isinstance(obj,dict) and isinstance(obj.get("@graph"),list) else [obj]
        changed=False
        for node in nodes:
            if isinstance(node,dict) and node.get("@type")=="BreadcrumbList":
                if node!=breadcrumb:
                    node.clear();node.update(breadcrumb);changed=True
        if not changed:return match.group(0)
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
        return match.group(1)+payload+match.group(3)
    return JSONLD.sub(update,page)

def _remove_schema_type(page,schema_type):
    """Remove stale nodes before rebuilding a visible-page schema contract."""
    def update(match):
        try:obj=json.loads(match.group(2))
        except (ValueError,TypeError):return match.group(0)
        if isinstance(obj,dict) and obj.get("@type")==schema_type:
            return ""
        graph=obj.get("@graph") if isinstance(obj,dict) else None
        if not isinstance(graph,list):return match.group(0)
        filtered=[node for node in graph if not (isinstance(node,dict) and node.get("@type")==schema_type)]
        if len(filtered)==len(graph):return match.group(0)
        if not filtered:return ""
        obj["@graph"]=filtered
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
        return match.group(1)+payload+match.group(3)
    return JSONLD.sub(update,page)

def add_at_render(page,route,locale):
    """Add/update structured data from the final visible source-rendered page."""
    if "</head>" not in page:return page
    base=_route_base(route,locale)
    canonical=ORIGIN+route
    title,description=_head_meta(page)
    nodes=[]
    if base.startswith("/products/") and base!="/products/":
        row=_product_row(route,locale)
        if row:
            product,breadcrumb,webpage,faq,product_id,breadcrumb_id,webpage_id=_product_nodes(page,route,locale,row)
            page=_update_existing(page,canonical,locale,title,description,product_id,breadcrumb_id,webpage_id,
                                  str(row.get("model") or ""),product["additionalProperty"],product.get("image",[]))
            types,_=_existing_schema(page)
            if "Product" not in types:nodes.append(product)
            if "BreadcrumbList" not in types:nodes.append(breadcrumb)
            if "WebPage" not in types:nodes.append(webpage)
            if faq and "FAQPage" not in types:nodes.append(faq)
    elif base=="/products/" or re.fullmatch(r"/collections/[a-z0-9_-]+/",base,re.I):
        listing=_listing_nodes(page,route,locale)
        if listing:
            types,_=_existing_schema(page)
            if "ItemList" not in types:nodes.append(listing[0])
            if "WebPage" not in types:nodes.append(listing[1])
    elif base.startswith("/blog/") and base!="/blog/":
        breadcrumb,faq=_blog_nodes(page,route,locale)
        page=_update_blog_breadcrumb(page,breadcrumb)
        page=_update_blog_keywords(page,_localized_blog_keywords(page,locale))
        # Rebuild FAQPage strictly from visible translated answers. This also
        # removes an old empty/wrong-language FAQ node left by a prior shell.
        page=_remove_schema_type(page,"FAQPage")
        types,_=_existing_schema(page)
        if "BreadcrumbList" not in types:nodes.append(breadcrumb)
        if faq:nodes.append(faq)
    if not nodes:return page
    payload=json.dumps({"@context":"https://schema.org","@graph":nodes},
                       ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    tag='<script type="application/ld+json">'+payload+'</script>'
    return page.replace("</head>",tag+"</head>",1)

