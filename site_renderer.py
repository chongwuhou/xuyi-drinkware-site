from pathlib import Path
from functools import lru_cache
import json,html,re,collections,os,hashlib
from home_banner_config import tag as banner_tag,for_locale as banner_slides
from locale_registry import approved_locales
ROOT=Path(__file__).parent
def _asset_version():
 data=[]
 for name in ("site.css","site-settings.css"):
  asset=ROOT/"assets"/name
  if asset.is_file():data.append(asset.read_bytes())
 return hashlib.sha256(b"\0".join(data)).hexdigest()[:12]
ASSET_VERSION=_asset_version()
INDEXING_APPROVED=(json.loads((ROOT/"deployment/site.config.json").read_text(encoding="utf-8"))
                   .get("site",{}).get("indexingApproved") is True)
BUILD_STATE={}
_build_state_path=os.environ.get("XUYI_BUILD_SNAPSHOT","")
if _build_state_path:
 _state_path=Path(_build_state_path).resolve()
 if not _state_path.is_file():raise RuntimeError("Missing XUYI build snapshot")
 BUILD_STATE=json.loads(_state_path.read_text(encoding="utf-8"))
 if BUILD_STATE.get("site")!="xuyi-drinkware-site" or BUILD_STATE.get("schemaVersion")!=1:
  raise RuntimeError("Refusing build snapshot from another project")
BUILD_LANGUAGES=approved_locales(BUILD_STATE,require_resources=False) if BUILD_STATE else []
PAGE_OVERRIDES={str(v.get("route")):v for v in BUILD_STATE.get("pages",[]) if isinstance(v,dict)}
PRODUCT_OVERRIDES={str(v.get("model")):v.get("content",{}) for v in BUILD_STATE.get("products",[]) if isinstance(v,dict)}
BRAND_CONFIG=BUILD_STATE.get("brand") or {}
BODY_OVERRIDES={str(r.get("route")):r.get("mainHtml","")
                for r in BUILD_STATE.get("pageBodies",[]) if isinstance(r,dict)}
from product_slug_fix import ALIASES as LEGACY_PRODUCT_SLUGS
for _old,_new in LEGACY_PRODUCT_SLUGS.items():
 _old_route='/products/'+_old+'/'
 _new_route='/products/'+_new+'/'
 # Legacy D1 SEO/body records remain authoritative until the owner migrates
 # the CMS route. A later explicit new-route edit always wins.
 if _old_route in PAGE_OVERRIDES:PAGE_OVERRIDES.setdefault(_new_route,PAGE_OVERRIDES[_old_route])
 if _old_route in BODY_OVERRIDES:BODY_OVERRIDES.setdefault(_new_route,BODY_OVERRIDES[_old_route])
BUILD_OUTPUT_DIR=os.environ.get("XUYI_OUTPUT_DIR",".")
if BUILD_OUTPUT_DIR not in (".","dist"):
 raise ValueError("XUYI_OUTPUT_DIR must be . or dist")

@lru_cache(maxsize=8)
def read_template(name):
 if name not in {"shell","header","footer","sidebar","home","listing","content","static","product-card","category-card","page-intro","catalog-filter","catalog-pagination","faq-list","product-spec","product-thumbnails","product-benefit","product-overview","contact-form","section-heading","head","process-step"}:raise ValueError("Unknown site partial")
 return (ROOT/"templates"/"site"/(name+".html")).read_text(encoding="utf-8").rstrip(chr(10))

def render_template(name,**parts):
 template=read_template(name)
 for key,value in parts.items():template=template.replace("{{"+key+"}}",value)
 if "{{" in template or "}}" in template:raise ValueError("Unfilled template placeholder: "+name)
 return template
def dedupe_catalog_cards(body):
    """Keep one card per href before locale/catalog enrichers append reviewed cards."""
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

def sort_d1_blog_index(body):
    """Keep the static English Blog index in the D1 published order."""
    ordered=[str(row.get("slug")) for row in BUILD_STATE.get("blogPosts",[])
             if isinstance(row,dict) and row.get("status")=="published"
             and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",str(row.get("slug","")))]
    if not ordered or len(ordered)!=len(set(ordered)):
        return body
    cards=list(re.finditer(r'<article class="news-card">[\s\S]*?</article>',body,re.I))
    if len(cards)!=len(ordered):
        return body
    parsed=[]
    for match in cards:
        links=re.findall(r'href=["\']/((?:[a-z0-9_-]+/)?blog/([a-z0-9]+(?:-[a-z0-9]+)*)/)["\']',match.group(0),re.I)
        slugs={slug for _,slug in links}
        if len(slugs)!=1:
            return body
        parsed.append((next(iter(slugs)),match.group(0)))
    if len(set(slug for slug,_ in parsed))!=len(parsed) or set(slug for slug,_ in parsed)!=set(ordered):
        return body
    by_slug=dict(parsed)
    separator=body[cards[0].end():cards[1].start()] if len(cards)>1 else ""
    replacement=separator.join(by_slug[slug] for slug in ordered)
    return body[:cards[0].start()]+replacement+body[cards[-1].end()]

def render_d1_blog_index(body):
    """Render every published D1 Blog row into the static English index."""
    posts=[row for row in BUILD_STATE.get("blogPosts",[])
           if isinstance(row,dict) and row.get("status")=="published"
           and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",str(row.get("slug","")))]
    if not posts:
        return body
    cards=[]
    for post in posts:
        slug=str(post["slug"])
        title=str(post.get("title") or "").strip()
        description=str(post.get("description") or "").strip()
        cover=str(post.get("cover") or "").strip()
        # Preserve an owner-edited D1 cover. If the row still contains the
        # known legacy source cover, use the already reviewed source image.
        try:
            from blog_editorial import cover_path
            if slug in BLOG_POSTS:
                baseline=str(BLOG_POSTS[slug].get("cover") or "")
                if baseline and not baseline.startswith("/"):
                    baseline="/media/ppt/"+baseline
                if cover==baseline:
                    cover=cover_path(slug)
        except (ImportError,KeyError):
            pass
        if len(title)<12 or len(description)<25 or not cover.startswith("/"):
            raise ValueError("Published D1 Blog row has incomplete index fields: "+slug)
        url="/blog/"+e(slug)+"/"
        category=e(str(post.get("group") or "Buyer Resources").upper())
        cards.append('<article class="news-card"><a class="news-card__image" href="'+url+'"><img src="'+e(cover)+'" alt="'+e(str(post.get("coverAlt") or title))+'" loading="lazy"></a><div class="news-card__info"><span class="news-card__category">'+category+'</span><h3><a href="'+url+'">'+e(title)+'</a></h3><p>'+e(description)+'</p><a class="news-card__read" href="'+url+'">Read Article →</a></div></article>')
    # D1 owns the published rows, while the surrounding page body may be
    # owner-edited and therefore may not keep the historical wrapper exactly.
    # Replace the known wrapper when present; otherwise replace any existing
    # card run or append a controlled grid without discarding owner content.
    pattern=re.compile(r'(<section class="section blog-listing"><div class="shell"><div class="blog-listing__grid">)[\s\S]*?(</div></div></section>)',re.I)
    updated,count=pattern.subn(lambda m:m.group(1)+''.join(cards)+m.group(2),body,count=1)
    if count==1:
        return updated

    existing=list(re.finditer(r'<article class="news-card">[\s\S]*?</article>',body,re.I))
    if existing:
        separator=body[existing[0].end():existing[1].start()] if len(existing)>1 else ""
        replacement=separator.join(cards)
        return body[:existing[0].start()]+replacement+body[existing[-1].end():]

    listing='<section class="section blog-listing"><div class="shell"><div class="blog-listing__grid">'+''.join(cards)+'</div></div></section>'
    main_close=re.search(r'</main>',body,re.I)
    if main_close:
        return body[:main_close.start()]+listing+body[main_close.start():]
    return body+listing

RAW=json.loads((ROOT/"data/products.json").read_text(encoding="utf-8"))
IMAGES=json.loads((ROOT/"data/excel-images.json").read_text(encoding="utf-8"))
CAT={
"Plastic Sports Water Bottles":("Sports Water Bottles","sports-water-bottles","/media/ppt/slide-059.webp","Lightweight reusable plastic bottles for daily hydration and active lifestyles."),
"Large Capacity Water Jugs":("Large Capacity Water Jugs","large-capacity-water-jugs","/media/ppt/slide-055.webp","Carry-friendly larger volume plastic water bottles for fitness, outdoor and everyday use."),
"Kids Plastic Water Bottles":("Kids Water Bottles","kids-water-bottles","/media/ppt/slide-030.webp","Colorful children's plastic straw and carrying-strap bottle designs."),
"Plastic Shaker Bottles":("Protein Shaker Bottles","plastic-shaker-bottles","/media/ppt/slide-094.webp","Plastic shaker cups for gym, fitness and sports nutrition buyers."),
"Spray Water Bottles":("Spray Water Bottles","spray-water-bottles","/media/ppt/slide-059.webp","Spray water bottles for promotional, outdoor and everyday drinkware projects. Confirm nozzle, trigger and materials by model."),
"Two-Way Drinking Cups":("Two-Way Drinking Cups","two-way-drinking-cups","/media/ppt/slide-055.webp","Dual-mode drinking cups for travel, retail and promotional collections. Confirm lid components and materials by exact model."),
"Titanium Vacuum Cups":("Titanium Vacuum Cups","titanium-vacuum-cups","/media/ppt/slide-094.webp","Titanium vacuum cups for insulated drinkware sourcing. Verify grade, purity, vacuum construction and test documents for each SKU.")
}
SERIES=collections.OrderedDict()
for i,p in enumerate(RAW):
 key=p["model"]
 if key not in SERIES:SERIES[key]={**p,"variants":[],"images":[]}
 obj=SERIES[key];obj["variants"].append(p)
 media=IMAGES.get(str(i+3))
 if media and media['sku']==key:obj["images"].append("/media/excel/row-%03d.webp"%(i+3))
for model,slide in [('501',91),('502',92),('507',93),('509',94),('510',95),('5247',96),('5248',96)]:
 if model in SERIES:SERIES[model]["images"].append("/media/ppt/slide-%03d.webp"%slide)
GALLERY_IMAGES=json.loads((ROOT/"data/verified-gallery.json").read_text(encoding="utf-8"))
for m,item in SERIES.items():
 if m in GALLERY_IMAGES:item["images"]=GALLERY_IMAGES[m]+item["images"]
 if m=="2100":item["images"]=GALLERY_IMAGES["2099"]+item["images"]
 item["images"]=list(dict.fromkeys(item["images"]))
from lo_catalog import add_products as add_lo_products
add_lo_products(SERIES)
from gallery_catalog import add_products as add_gallery_references
add_gallery_references(SERIES)
for row in BUILD_STATE.get("products",[]):
 model=str(row.get("model",""))
 override=row.get("content") or {}
 if model in SERIES and isinstance(override,dict):
  for field in ("name","description","capacity","material","colors","packing","dimensions","carton_quantity","carton_size"):
   if isinstance(override.get(field),str) and override[field].strip():
    SERIES[model][field]=override[field].strip()
    if field in ("capacity","material","colors","packing","dimensions","carton_quantity","carton_size"):
     for variant in SERIES[model]["variants"]:
      variant[field]=override[field].strip()
  img=override.get("image")
  if isinstance(img,str) and img.startswith(("/assets/","/media/")) and ".." not in img:
   if img.startswith("/media/product/"):
    SERIES[model]["images"]=[img]
   else:
    SERIES[model]["images"]=[img]+[old for old in SERIES[model]["images"] if old!=img]

from catalog_extensions import append_new_products
NEW_PRODUCT_COUNT=append_new_products(SERIES,BUILD_STATE.get("products",[]))
assert SERIES,("No product models loaded from the authoritative catalog",)
assert all(v["images"] for v in SERIES.values()),[(k,v["images"]) for k,v in SERIES.items() if not v["images"]]
def e(v):return html.escape(str(v or ""),quote=True)
def photo(src,alt,loading='lazy',aspect_ratio=None):
 from product_source_identity import GENERIC_ALT
 if src in GENERIC_ALT:alt=GENERIC_ALT[src]
 # Reserve card geometry in the shared renderer, not in generated HTML.
 allowed={'4/3':('4 / 3','1200','900'),'3/2':('3 / 2','1200','800'),'16/9':('16 / 9','1200','675')}
 sizing=(' style="aspect-ratio:'+allowed[aspect_ratio][0]+';" width="'+allowed[aspect_ratio][1]+'" height="'+allowed[aspect_ratio][2]+'"' if aspect_ratio in allowed else '')
 return f'<img src="{e(src)}" alt="{e(alt)}" loading="{loading}" decoding="async"{sizing}>' 
def write(path,content):
 out=ROOT/BUILD_OUTPUT_DIR/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(content,encoding="utf-8")
URLS={}
SITE_CONFIG=json.loads((ROOT/"deployment/site.config.json").read_text(encoding="utf-8"))
SITE_ORIGIN=SITE_CONFIG["site"]["origin"]
def build_url(path,title,content):
 # Canonical URL for all generated static routes on the already-live production hostname.
 route="/"+path[:-len("index.html")] if path.endswith("index.html") else "/"+path
 canonical=SITE_ORIGIN+route
 override=PAGE_OVERRIDES.get(route)
 if route.startswith("/products/"):
  model=route.strip("/").split("/")[-1]
  p=PRODUCT_OVERRIDES.get(model,{})
  if isinstance(p,dict):
   override={**(override or {}),"seo_title":p.get("seoTitle") or (override or {}).get("seo_title"),
             "meta_description":p.get("seoDescription") or (override or {}).get("meta_description")}
 if override:
  if override.get("seo_title"):
   content=re.sub(r"<title>.*?</title>","<title>"+e(str(override["seo_title"])[:90])+"</title>",content,count=1,flags=re.S)
  if override.get("meta_description"):
   content=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="'+e(str(override["meta_description"])[:240])+'">',content,count=1)
 if route=="/about/":
  from about_company_page import replace_head_if_original,baseline_body
  old=PAGE_OVERRIDES.get(route) or {}
  original_body=BODY_OVERRIDES.get(route)
  if not original_body or baseline_body(original_body,'en'):
   content=replace_head_if_original(content,'en',old.get('seo_title',''),old.get('meta_description',''))
 family="home" if route=="/" else "listing" if route=="/products/" or route.startswith("/collections/") else "content" if route.startswith(("/products/","/blog/")) else "static"
 marker='<main id="main-content">'
 if marker in content and "</main>" in content:
  start,tail=content.split(marker,1)
  main,end=tail.split("</main>",1)
  body_override=BODY_OVERRIDES.get(route)
  if isinstance(body_override,str) and len(body_override)>=100 and not re.search(
     r"<\s*(?:script|iframe|object|embed|form|style|link|base|meta|svg|math|template)\b|\bon[a-z-]+\s*=|\bsrcdoc\s*=|(?:javascript|vbscript|data)\s*:",
     body_override,re.I):
   main=body_override
  # Normalize the exact legacy English CMS Blog list section at the shared
  # render entry point. Never touch generated HTML or owner-rewritten titles.
  if route=="/blog/":
   from blog_listing_layout import single_blog_index_heading
   main=single_blog_index_heading(main,"en")
   main=sort_d1_blog_index(main)
   main=render_d1_blog_index(main)
  # Upgrade only exact, still-unedited original covers in English CMS-rendered
  # Blog bodies and cards, matching the same source boundary used by locales.
  if route.startswith("/blog/"):
   from blog_media_source import blog_cover_from_cms_source
   main=blog_cover_from_cms_source(main,route,"en")
   from blog_editorial import ensure_related_guides
   main=ensure_related_guides(route,main)
  if route=="/about/":
   from about_company_page import apply_body
   main=apply_body(main,'en')
  # Retain D1-edited body as the primary page, and append only distinct
  # source-checked supplements for selected company/quality pages.
  from editorial_support import for_route as reviewed_editorial_for_route
  if route!='/about/' or 'id="xuyi-about-company"' not in main:
   main+=reviewed_editorial_for_route(route,main)
  # Blog product links are now authored inside two different paragraphs
  # via blog_editorial.render_article; do not add the legacy auto callout.
  if route=='/why-us/':
   from why_us_source import augment as why_us_buyer_evidence
   main=why_us_buyer_evidence(main,'en',owner_override=bool(BODY_OVERRIDES.get(route)))
  # Owner-approved Blog content remains primary. Add a verified long-form
  # source supplement only while its exact baseline introduction survives.
  if route.startswith('/blog/'):
   from blog_editorial import owner_safe_depth
   main+=owner_safe_depth(route,main)
  # Render reviewed buyer guidance at the CMS/template stage, not by
  # rewriting output HTML. D1-owned modules always take precedence.
  if route.startswith(("/applications/","/features/")):
   from scripts.curated_application_feature_answers import render_buyer_evidence
   main+=render_buyer_evidence(route,"en",main)
  if route=="/":
   # Replace only the low-resolution generic homepage marketing photograph.
   # Catalog-SKU photos and the blog thumbnails are intentionally unchanged.
   from media_quality_guard import upgrade_home_visual
   main=upgrade_home_visual(main,"en")
   from home_bpa_source import add_home_bpa_note
   main=add_home_bpa_note(main,"en")
   from home_intro_source_photo import reviewed_home_intro_photo
   main=reviewed_home_intro_photo(main)
   from home_source_image_geometry import source_image_geometry
   main=source_image_geometry(main,route,"en")
  if route=="/products/" or route.startswith("/collections/"):
   main=dedupe_catalog_cards(main)
   from gallery_catalog import catalog_cards as gallery_cards
   main=gallery_cards(main,"en",route)
   from lo_catalog import catalog_cards
   main=catalog_cards(main,"en",route)
   from factory_catalog_locales import catalog_cards as factory_catalog_cards, _page_grid_bounds
   if _page_grid_bounds(main) is not None:
    main=factory_catalog_cards(main,"en",route)
  if route.startswith("/products/") and route!="/products/":
   from product_material_performance import inject
   product=next((obj for obj in SERIES.values() if "/products/"+obj["slug"]+"/"==route),None)
   if product is None:raise ValueError("No material source for product route: "+route)
   # Per-model factual sections only replace exact untouched source modules;
   # an English D1/CMS body override is the authoritative editor version.
   if not BODY_OVERRIDES.get(route):
    from sku_factual_sections import apply as verified_sku_sections
    main=verified_sku_sections(main,product,"en")
   main=inject(main,product,"en",route)
   from product_source_identity import source_product_identity
   # Never revise an English CMS-managed body after an editor replaces the
   # previously generated product template.
   if not BODY_OVERRIDES.get(route):
    main=source_product_identity(main,product,"en",collections.Counter(x["images"][0] for x in SERIES.values()),allow_unbaselined=bool(product.get("sourceDocument") and product.get("manualNew")))
   from sku_unique_openings import editor_intro
   main=editor_intro(main,product,"en")
   from g_series_material_options import render_g_material_options
   main+=render_g_material_options(route,'en',main)
  # D1's English homepage body predates the five-language logo carousel.
  # Restore the same six-logo section already present in the four reviewed
  # translations, regardless of whether D1 overrides the English template.
   if route=="/" and 'id="customer-brands"' not in main:
    from home_enhancements import customer_logo_section
    logos=customer_logo_section()
    if not logos:
     raise ValueError("XUYI homepage customer-logo section has no complete assets")
    news='<section class="news-section"'
    if news not in main:
     raise ValueError("XUYI homepage missing the news section insertion point")
    main=main.replace(news,logos+news,1)
  # Some published blog bodies also come from D1 and may predate their
  # source-reviewed reference section. Never erase the approved article.
  if route.startswith("/blog/"):
   if 'id="primary-sources"' not in main:
    from blog_editorial import render_primary_evidence
    slug=route.strip("/").split("/")[-1]
    sources_section=render_primary_evidence(slug)
    if sources_section:
     related_start='<section class="section section--soft blog-related">'
     if related_start in main:main=main.replace(related_start,sources_section+related_start,1)
     else:main+=sources_section
   # GEO evidence is rendered only from explicit, source-reviewed article
   # fields. Do not append the legacy heuristic block: it duplicated the
   # article and could cut numeric context in the middle of a sentence.
  # Capacity, oz-class, material options and model-specific comparison content
  # are rendered into product detail bodies before the page is written.
  from scripts.source_catalog_capacity_oz import enrich_catalog_body,source_body_enrichment
  main=enrich_catalog_body(main,"en",SERIES)
  if route.startswith('/products/') and route!='/products/':
   product=next((obj for obj in SERIES.values() if obj.get('slug')==route.strip('/').split('/')[-1]),None)
   if product:main=source_body_enrichment(main,'en',product)
  content=start+marker+render_template(family,CONTENT=main)+"</main>"+end
  if 'rel="canonical"' not in content:
   content=content.replace('</head>','<link rel="canonical" href="'+e(canonical)+'"><meta property="og:url" content="'+e(canonical)+'"></head>',1)
  # Keep social preview metadata aligned with the final D1-reviewed SEO values.
  # This is separate from the ignored legacy meta-keywords tag.
 for name,value in (
   ("og:title",re.search(r"<title>([^<]*)</title>",content,re.S)),
   ("og:description",re.search(r'<meta name="description" content="([^"]*)"',content))):
  if not value:continue
  tag='<meta property="'+name+'" content="'+value.group(1)+'">'
  if re.search(r'<meta property="'+name+'" content="[^"]*">',content):
   content=re.sub(r'<meta property="'+name+'" content="[^"]*">',lambda _:tag,content,count=1)
  else:content=content.replace("</head>",tag+"</head>",1)
 if route=="/":
  # Global, verified business entity identifiers; never invent test results,
  # product certification, reviews or production capacity for SEO/GEO.
  page_title=re.search(r"<title>([^<]*)</title>",content,re.S)
  page_desc=re.search(r'<meta name="description" content="([^"]*)"',content)
  graph={"@context":"https://schema.org","@graph":[
   {"@type":"Organization","@id":SITE_ORIGIN+"/#organization",
    "name":"XUYI Bottles","legalName":"台州市旭一家居用品有限公司",
    "url":SITE_ORIGIN+"/","address":{"@type":"PostalAddress","addressLocality":"Taizhou","addressRegion":"Zhejiang","addressCountry":"CN"}},
   {"@type":"WebSite","@id":SITE_ORIGIN+"/#website","url":SITE_ORIGIN+"/",
    "name":"XUYI Bottles","publisher":{"@id":SITE_ORIGIN+"/#organization"},
    "inLanguage":[lang["code"] for lang in approved_locales(BUILD_STATE)]},
   {"@type":"WebPage","@id":SITE_ORIGIN+"/#webpage","url":SITE_ORIGIN+"/",
    "name":html.unescape(page_title.group(1)) if page_title else "XUYI Bottles",
    "description":html.unescape(page_desc.group(1)) if page_desc else "",
    "inLanguage":"en","isPartOf":{"@id":SITE_ORIGIN+"/#website"}}]}
  from organization_source_schema import enrich_organization
  graph["@graph"]=[enrich_organization(node) for node in graph["@graph"]]
  schema='<script type="application/ld+json">'+json.dumps(graph,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")+'</script>'
  content=content.replace("</head>",schema+"</head>",1)
 if route=="/":
  content=content.replace("</head>",banner_tag(BUILD_STATE)+"</head>",1)
  slide=banner_slides(BUILD_STATE)[0]
  heading=e(slide["title"])+" <span>"+e(slide["highlight"])+"</span>"
  content=re.sub(r'(<h1\b[^>]*\bid="hero-title"[^>]*>).*?(</h1>)',
    lambda m:m.group(1)+heading+m.group(2),content,count=1,flags=re.S)
  content=re.sub(r'(<p\b[^>]*\bid="hero-description"[^>]*>).*?(</p>)',
    lambda m:m.group(1)+e(slide["description"])+m.group(2),content,count=1,flags=re.S)
  content=re.sub(r'(<a\b(?=[^>]*\bid="hero-cta")[^>]*>).*?(</a>)',
    lambda m:m.group(1)+e(slide["cta"])+m.group(2),content,count=1,flags=re.S)
  content=re.sub(r'(<img\b(?=[^>]*\bid="hero-image")[^>]*\balt=")[^"]+(")',
    lambda m:m.group(1)+e(slide["alt"])+m.group(2),content,count=1)
  content=re.sub(r'(<img\b(?=[^>]*\bid="hero-image")[^>]*\bsrc=")[^"]+(")',lambda m:m.group(1)+e(slide["img"])+m.group(2),content,count=1)
  content=re.sub(r'(<a\b(?=[^>]*\bid="hero-cta")[^>]*\bhref=")[^"]+(")',lambda m:m.group(1)+e(slide["link"])+m.group(2),content,count=1)
 from product_locale_seo import polish_product_head
 content=polish_product_head(content,"en",route)
 from image_alt_quality import polish_image_alt
 content=polish_image_alt(content,"en")
 from media_alt_render import apply_media_alts
 content=apply_media_alts(content,BUILD_STATE,"en")
 # Render source-verified component materials and retail capacity into
 # default SEO before writing the page. Owner D1 title edits win.
 if route.startswith('/products/') and route!='/products/':
  from scripts.source_catalog_capacity_oz import pre_render_verified_meta
  row=next((v for v in SERIES.values() if v['slug']==route.strip('/').split('/')[-1]),None)
  if row:content=pre_render_verified_meta(content,'en',row,BUILD_STATE)
  # Review content is a separate, explicitly published D1 field owner.
  # Source-render only after the possible English CMS body override.
  if row:
   from product_reviews_source import at_product_source
   content=at_product_source(content,row["model"],"en",BUILD_STATE)
 # Structured data and trust metadata are finalized after all D1 overrides.
 if route.startswith('/products/') and route!='/products/':
  from product_share_source import add_social_head
  product=next((x for x in SERIES.values() if x["slug"]==route.split("/")[2]),None)
  if product:content=add_social_head(content,product)
 # Search intent for these three URLs belongs to the source renderer, not
 # a post-build HTML rewrite. D1 owner-edited SEO is always authoritative.
 from search_intent_roles import render_search_intent
 content=render_search_intent(content,route,'en')
 # Source-owned Kids collection social preview; existing CMS edits take precedence.
 from product_share_source import add_kids_collection_preview
 content=add_kids_collection_preview(content,route)
 # Attach optional responsive variants during source rendering, not in dist.
 # User-selected CMS src and ALT values remain authoritative.
 from responsive_image_render import enhance_source_markup
 content=enhance_source_markup(content)
 if route.startswith('/products/') and route!='/products/':
  from product_seo_d1_source import apply_d1_product_seo
  content=apply_d1_product_seo(content,route.strip('/').split('/')[-1],'en',BUILD_STATE)
 from scripts.reviewed_editorial_images import apply_to_document as apply_reviewed_editorial_images
 content=apply_reviewed_editorial_images(content,route,'en')
 from scripts.reviewed_lowres_editorial_round2 import apply_to_document as apply_reviewed_lowres_images
 content=apply_reviewed_lowres_images(content,route,'en')
 from scripts.repair_mismatched_sports_category import apply_to_document as repair_sports_category_image
 content=repair_sports_category_image(content,route,'en')
 from scripts.repair_remaining_category_cards import apply_to_document as repair_remaining_category_images
 content=repair_remaining_category_images(content,route,'en')
 from scripts.apply_gpt_reviewed_shaker_hd import apply_to_document as apply_approved_product_images
 content=apply_approved_product_images(content,route,'en')
 from scripts.polish_priority_seo import apply_to_document as apply_priority_seo
 content=apply_priority_seo(content,route,'en')
 from scripts.curated_buyer_seo_round2 import apply_to_document as apply_curated_buyer_seo
 content=apply_curated_buyer_seo(content,route,'en')
 from scripts.buyer_journey_internal_links import apply_to_document as apply_buyer_journey_links
 content,_=apply_buyer_journey_links(content,route,'en')
 from responsive_image_render import promote_primary_blog_image
 if route.startswith('/blog/') and route!='/blog/':content=promote_primary_blog_image(content)
 content=enhance_source_markup(content, include_legacy=True)
 from seo_structured_components import add_at_render
 content=add_at_render(content,route,'en')
 from scripts.contextual_share_metadata import apply_to_document as apply_contextual_share_preview
 content,_=apply_contextual_share_preview(content,route,'en')
 from scripts.verified_trust_technical_seo import add_at_render as add_trust_technical_seo
 content=add_trust_technical_seo(content,route,'en')
 from scripts.product_hreflang import apply_to_document as apply_product_hreflang
 content=apply_product_hreflang(content,route,'en',BUILD_LANGUAGES)
 URLS[path]=title
 write(path,content)
ICONS={
"search":'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>',
"menu":'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
"mail":'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
"form":'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/><path d="m14 17 2 2 4-4"/></svg>',
"phone":'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h5l1 5-2 2a15 15 0 0 0 4 4l2-2 5 1v5l-2 3C9 19 5 15 3 6z"/></svg>',
"whatsapp":'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.4 3.6A11.6 11.6 0 0 0 2.6 17.7L1 23l5.4-1.6A11.6 11.6 0 0 0 20.4 3.6Z"/><path d="M8.1 7.1c-.4.2-1.5 1.5-1 3.4.7 2.9 3.6 5.7 6.2 6.5 1.6.5 3.3-.7 3.5-1.3l-2.4-1.4-1.2 1.1c-1.9-.7-3.2-2-4.1-4l1-1.2-1.4-2.9Z"/></svg>',
"top":'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 14 7-7 7 7"/></svg>',
"chevron":'<svg class="chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 9 7 7 7-7"/></svg>'
}
def category_links():
 nav={r.get("url"):r.get("label") for r in BUILD_STATE.get("navigation",[]) if isinstance(r,dict)}
 return [(nav.get("/collections/"+v[1]+"/") or v[0],"/collections/"+v[1]+"/") for v in CAT.values()]
# Navigation mirrors the target's information architecture, while retaining XUYI-only products.
# Both desktop and mobile reuse one category/menu data file.
# D1 site_navigation remains the runtime business source for labels and order.
MENU_DEFAULTS=json.loads((ROOT/"data/site-navigation-defaults.json").read_text(encoding="utf-8"))
if MENU_DEFAULTS.get("schemaVersion")!=1:raise ValueError("Unsupported navigation defaults")
PRODUCT_COLUMNS=[(group["heading"],group["image"],
                 [(link["label"],link["url"]) for link in group["links"]])
                for group in MENU_DEFAULTS["productColumns"]]
MINI_MENUS={name:[(link["label"],link["url"]) for link in links]
            for name,links in MENU_DEFAULTS["miniMenus"].items()}
if len(PRODUCT_COLUMNS)!=4:raise ValueError("Expected four XUYI mega-menu categories")
def header():
 navitems=[]
 defaults=["Home","Products","Capabilities","About","Why Us","Blog","FAQ","Contact Us"]
 top_urls={"Home":"/","Products":"/products/","Capabilities":"/capabilities/",
           "About":"/about/","Why Us":"/why-us/","Blog":"/blog/","FAQ":"/faq/","Contact Us":"/contact/"}
 nav_rows=BUILD_STATE.get("navigation",[])
 def custom_children(parent):
  """Keep new D1 child rows inside the parent's existing menu; no new columns."""
  rows=[row for row in nav_rows if isinstance(row,dict) and row.get("parent_id")==parent]
  rows.sort(key=lambda row:(int(row.get("sort_order",999)),str(row.get("id",""))))
  return rows
 def safe_extra(row):
  url=str(row.get("url") or "")
  if not (url.startswith("/") and not url.startswith("//") or
          url.startswith("https://") or url.startswith("mailto:") or url.startswith("tel:")):
   return ""
  if any(c in url for c in ("<",">",chr(34),chr(39),"\\","\n","\r")):return ""
  label=e(str(row.get("label") or "").strip()[:80])
  if not label:return ""
  blank=bool(row.get("new_window",row.get("newWindow",False)))
  return '<a href="'+e(url)+'"'+(' target="_blank" rel="noopener noreferrer"' if blank else '')+'>'+label+'</a>'
 by_url={x.get("url"):x for x in nav_rows if isinstance(x,dict)}
 labels={name:(by_url.get(url,{}).get("label") or name) for name,url in top_urls.items()}
 sorted_names=[name for name in defaults if top_urls[name] in by_url and not by_url[top_urls[name]].get("parent_id")]
 if sorted_names:
  sorted_names.sort(key=lambda name:(int(by_url[top_urls[name]].get("sort_order",999)),defaults.index(name)))
 else:sorted_names=defaults
 # FAQ was accidentally dropped when Quick Links was removed. Keep it present
 # even on older D1 navigation snapshots that do not yet contain an FAQ row.
 if "FAQ" not in sorted_names:sorted_names.append("FAQ")
 for name in defaults:
  if name=="Home":navitems.append('<a class="nav__link" href="/">Home</a>')
  elif name in ("About","Blog","FAQ","Contact Us"):
   uri={"About":"/about/","Blog":"/blog/","FAQ":"/faq/","Contact Us":"/contact/"}[name]
   navitems.append('<a class="nav__link" href="'+uri+'">'+name+'</a>')
  elif name=="Products":
   cols=[]
   for group,img,links in PRODUCT_COLUMNS:
    heading='<a class="mega__heading" href="'+e(links[0][1])+'">'+e(group)+'</a>'
    pic='<a class="mega__image" href="'+e(links[0][1])+'">'+photo(img,"XUYI "+group+" catalog photo")+'</a>'
    column='<div class="mega__column">'+heading+pic+'<div class="mega__links">'+''.join('<a href="'+e(uri)+'">'+e(by_url.get(uri,{}).get('label') or label)+'</a>' for label,uri in links)+'</div></div>'
    if group=="OEM & Wholesale":
     known_urls={u for _,_,items in PRODUCT_COLUMNS for _,u in items}
     additional="".join(safe_extra(row) for row in custom_children("products") if row.get("url") not in known_urls)
     if additional:column=column.replace("</div></div>","<div class=\"mega__links mega__links--custom\">"+additional+"</div></div></div>",1)
    cols.append(column)
   submenu='<div class="mega" id="menu-products"><div class="mega__grid">'+''.join(cols)+'</div></div>'
   navitems.append('<div class="nav__drop nav__drop--mega"><button class="nav__toggle" data-mega-toggle type="button" aria-expanded="false" aria-controls="menu-products">Products'+ICONS['chevron']+'</button>'+submenu+'</div>')
  else:
   items=''.join('<a href="'+e(uri)+'">'+e(by_url.get(uri,{}).get('label') or label)+'</a>' for label,uri in MINI_MENUS[name])
   known_urls={u for _,u in MINI_MENUS[name]}
   submenu_parent={"Capabilities":"capabilities","Why Us":"why-us"}[name]
   items+="".join(safe_extra(row) for row in custom_children(submenu_parent) if row.get("url") not in known_urls)
   menu_id='menu-'+name.lower().replace(' ','-')
   navitems.append('<div class="nav__drop nav__drop--mini"><button class="nav__toggle" data-mega-toggle type="button" aria-controls="'+menu_id+'" aria-expanded="false">'+name+ICONS['chevron']+'</button><div class="mini-menu" id="'+menu_id+'">'+items+'</div></div>')
 nav_parts=dict(zip(defaults,navitems))
 navitems=[]
 for key in sorted_names:
  markup=nav_parts[key]
  label=labels[key]
  if key in ("Products","Capabilities","Why Us"):
   markup=markup.replace(key+ICONS["chevron"],e(label)+ICONS["chevron"],1)
  else:markup=markup.replace(">"+key+"</a>",">"+e(label)+"</a>",1)
  navitems.append(markup)
 # All navigational targets are XUYI pages, no stainless steel or competitor-branded items.
 mobile_parts={}
 mobile_parts["Home"]='<a href="/">'+e(labels["Home"])+'</a>'
 groups=[]
 for group,img,links in PRODUCT_COLUMNS:
  item='<div class="mobile-nav__group"><div class="mobile-nav__group-title">'+photo(img,group+' plastic bottles')+'<strong>'+e(group)+'</strong></div>'
  item+=''.join('<a href="'+e(uri)+'">'+e(by_url.get(uri,{}).get("label") or label)+'</a>' for label,uri in links)+'</div>'
  if group=="OEM & Wholesale":
   known_urls={u for _,_,items in PRODUCT_COLUMNS for _,u in items}
   item+="".join(safe_extra(row) for row in custom_children("products") if row.get("url") not in known_urls)
  groups.append(item)
 mobile_parts["Products"]='<details><summary>'+e(labels["Products"])+'</summary>'+''.join(groups)+'</details>'
 for nav_name in ("Capabilities","Why Us"):
  submenu=''.join('<a href="'+e(uri)+'">'+e(by_url.get(uri,{}).get("label") or label)+'</a>' for label,uri in MINI_MENUS[nav_name])
  known_urls={u for _,u in MINI_MENUS[nav_name]}
  submenu+="".join(safe_extra(row) for row in custom_children({"Capabilities":"capabilities","Why Us":"why-us"}[nav_name]) if row.get("url") not in known_urls)
  mobile_parts[nav_name]='<details><summary>'+e(labels[nav_name])+'</summary>'+submenu+'</details>'
 for nav_name in ("About","Blog","FAQ","Contact Us"):
  mobile_parts[nav_name]='<a href="'+top_urls[nav_name]+'">'+e(labels[nav_name])+'</a>'
 mobile=''.join(mobile_parts[k] for k in sorted_names)
 # Let D1 append genuine, approved top-level links to both menus. The
 # existing four-column product group remains the XUYI design source.
 custom_top=sorted((r for r in nav_rows if isinstance(r,dict) and not r.get("parent_id")
     and r.get("url") not in top_urls.values()),
     key=lambda r:(int(r.get("sort_order",999)),str(r.get("id",""))))
 extra_top={}
 for item in custom_top:
  uri=str(item.get("url") or "")
  markup=safe_extra(item)
  if not markup:continue
  label=e(str(item.get("label") or "")[:80])
  extra_top[str(item.get("id"))]=(
    '<a class="nav__link"'+markup.removeprefix("<a"),
    markup)
 # Reorder all top-level items (native and extra) according to D1 sortOrder.
 combined=[]
 for name in sorted_names:
  item=by_url.get(top_urls[name],{})
  combined.append((int(item.get("sort_order",defaults.index(name)*10+10)),
                   defaults.index(name),nav_parts[name],mobile_parts[name]))
 for item in custom_top:
  pair=extra_top.get(str(item.get("id")))
  if pair:
   combined.append((int(item.get("sort_order",999)),100+len(combined),pair[0],pair[1]))
 combined.sort(key=lambda t:(t[0],t[1]))
 navitems=[a[2] for a in combined]
 mobile="".join(a[3] for a in combined)
 mobile+='<a href="/request-sample/">Request Sample</a><a href="/contact/#inquiry">Instant Quote →</a>'
 top='<div class="topbar"><div class="shell topbar__inner"><a href="/about/" aria-label="XUYI company">XUYI · Taizhou, China</a><a href="/request-sample/">Request Sample</a><a href="/contact/#inquiry">Contact</a></div></div>'
 logo='<a href="/" class="logo" aria-label="XUYI Bottles home">XUYI<small>BOTTLES</small></a>'
 identity=BRAND_CONFIG.get("identity") or {}
 if isinstance(identity.get("displayName"),str) and identity["displayName"].strip() and identity["displayName"].strip()!="XUYI Bottles":
  brand=e(identity["displayName"].strip()[:120])
  logo='<a href="/" class="logo" aria-label="'+brand+' home">'+brand+'</a>'
  top=top.replace("XUYI · Taizhou, China",brand+" · Taizhou, China",1)
 locale_options="".join('<option value="'+e(lang["code"])+'">'+e(lang["nativeName"])+'</option>'
                        for lang in approved_locales(BUILD_STATE))
 actions='<div class="header__actions"><select class="language-switch" data-language-switch aria-label="Choose language">'+locale_options+'</select><button class="icon-button" id="search-toggle" aria-label="Search products" aria-expanded="false" type="button">'+ICONS['search']+'</button><a class="button header__quote" href="/contact/#inquiry">Instant Quote</a><button class="icon-button menu-button" id="mobile-menu" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-navigation" type="button">'+ICONS['menu']+'<span class="menu-label">Menu</span></button></div>'
 search='<div id="search-panel" class="search-panel"><form class="shell search-panel__form" action="/products/" method="get"><input type="search" name="q" placeholder="Search product model or type…" aria-label="Search product models"><button class="button" type="submit">Search →</button></form></div>'
 from home_source_image_geometry import source_image_geometry
 return source_image_geometry(render_template("header",TOPBAR=top,LOGO=logo,NAV_DESKTOP=''.join(navitems),ACTIONS=actions,SEARCH=search,NAV_MOBILE=mobile),"/","en")
def whatsapp_display_number():
 contact=BRAND_CONFIG.get("contact") or {}
 digits=re.search(r"^https://wa\.me/([1-9][0-9]{7,14})$",str(contact.get("whatsappUrl") or ""))
 value=digits.group(1) if digits else "8615395897937"
 display=str(contact.get("phoneDisplay") or "").strip()
 if display and re.sub(r"\D","",display)==value and display.startswith("+"):
  return display
 if value.startswith("86") and len(value)==13:
  return "+86 "+value[2:5]+" "+value[5:9]+" "+value[9:]
 return "+"+value

def footer():
 links=''.join('<p><a href="'+uri+'">'+e(label)+'</a></p>' for label,uri in category_links())
 result=render_template("footer",PRODUCT_LINKS=links,WHATSAPP_NUMBER=e(whatsapp_display_number()))
 footer_config=BRAND_CONFIG.get("footer") or {}
 identity=BRAND_CONFIG.get("identity") or {}
 brand_name=str(identity.get("displayName","")).strip()
 if brand_name and brand_name!="XUYI Bottles":
  result=result.replace("XUYI<small>BOTTLES</small>",e(brand_name),1)
  result=result.replace("© 2026 XUYI Bottles", "© 2026 "+e(brand_name),1)
 if footer_config.get("about"):
  result=result.replace("Factory-backed plastic water bottles for wholesale, branding and OEM/ODM projects.",
                        e(str(footer_config["about"])[:1000]),1)
 contact=BRAND_CONFIG.get("contact") or {}
 if contact.get("email"):
  email=str(contact["email"]).strip()
  if re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+",email):
   result=result.replace("Janey@xuyibottles.com",e(email))
 if contact.get("whatsappUrl") and str(contact["whatsappUrl"]).startswith("https://wa.me/"):
  result=result.replace("https://wa.me/8615395897937",e(str(contact["whatsappUrl"])))
 return result
def page(title,description,body,canonical=None,blog_pager=False):
 # The release gate defaults to noindex until business approval. Once explicitly
 # enabled, all public locales inherit the same indexable head from this template.
 head=render_template("head",TITLE=e(title),DESCRIPTION=e(description)[:220],ASSET_VERSION=ASSET_VERSION)
 if blog_pager:
  # Blog-only shared source component; the English D1 runtime and all four
  # localized builds inherit this exact head. Never patch generated HTML.
  pager='<link rel="stylesheet" href="/assets/blog-pagination.css"><script defer src="/assets/blog-pagination.js"></script>'
  head=head.replace('</head>',pager+'</head>',1)
 if INDEXING_APPROVED:
  head=head.replace('<meta name="robots" content="noindex,nofollow">',
                    '<meta name="robots" content="index,follow">',1)
  rail=render_template("sidebar",ICON_FORM=ICONS["form"],ICON_MAIL=ICONS["mail"],ICON_WHATSAPP=ICONS["whatsapp"],ICON_TOP=ICONS["top"])
  return render_template("shell",HEAD=head,HEADER=header(),SIDEBAR=rail,BODY=body,FOOTER=footer())
def intro(crumb,title,subtitle=""):
 return render_template("page-intro",CRUMB=e(crumb),TITLE=e(title),SUBTITLE=e(subtitle))
def category_card(cat):
 n,slug,im,desc=cat
 category=next((key for key,value in CAT.items() if value[1]==slug),None)
 if category:
  product=next((item for item in SERIES.values() if item.get("category")==category and item.get("manualNew") and item.get("images")),None)
  if product:im=product["images"][0]
 return render_template("category-card",URL="/collections/"+e(slug)+"/",IMAGE=photo(im,n),TITLE=e(n))
def public_display_name(item):
 # The source lists model 2506 as 60ml; this is unverified and likely a catalog data error.
 if str(item.get("model"))=="2506":return "Plastic Sports Water Bottle — Model 2506"
 # Some original workbook variant labels contain Chinese suffixes. Preserve
 # model/slugs but make their English search snippets readable.
 return str(item["name"]).replace("透明款"," (Transparent Variant)")
def model_label(value):
 return str(value).replace("透明款"," (Transparent Variant)")

def product_card(item):
  img=item["images"][0]
  two_way=item.get("category")=="Two-Way Drinking Cups"
  if two_way:
   from factory_catalog_locales import _card_title
   title=_card_title(item,"en")
  else:
   # Manual/D1 product modules retain the owner's display name. The
   # catalog post-render pass applies B2B source titles only to default cards.
   title=public_display_name(item)
  model=model_label(item["model"])
  from scripts.source_catalog_capacity_oz import catalog_volume_numbers,volume_terms,verified_source_material
  numbers=catalog_volume_numbers(item)
  capacity=volume_terms(numbers,"en") if numbers else ""
  material=verified_source_material(item)
  procurement="wholesale B2B OEM factory manufacturer custom plastic material options"
  searchable=(title+" "+model+" "+str(item.get("capacity",""))+" "+capacity+" "+material+" "+procurement).lower()
  capacity_html='<span class="product-card__capacity">'+e(capacity)+'</span>' if capacity and not two_way else ""
  alt=title+" model "+model
  return render_template("product-card",
   CATEGORY=e(CAT[item["category"]][1]),SEARCH=e(searchable),
   URL="/products/"+e(item["slug"])+"/",
   IMAGE=photo(img,alt),MODEL=e(model),TITLE=e(title),CAPACITY=capacity_html)
def product_grid(items):return '<div class="grid grid--4 product-grid">'+''.join(product_card(x) for x in items)+'</div>'
def filters(with_categories=True):
 options='<option value="">All product categories</option>'+''.join('<option value="'+x[1]+'">'+e(x[0])+'</option>' for x in CAT.values())
 category='<select aria-label="Filter category" data-catalog-category>'+options+'</select>' if with_categories else ""
 return render_template("catalog-filter",CATEGORY_FILTER=category)
def pagination(count=None):
 if count is not None:
  from catalog_crawlable_pagination import navigation
  return navigation(count)
 return render_template("catalog-pagination")
def faq_html(items=None):
 arr=items or FAQS
 rows="".join("<details><summary>"+e(q)+"</summary><p>"+e(a)+"</p></details>" for q,a in arr)
 return render_template("faq-list",CONTENT=rows)
FAQS=[
("Can you customize bottle colors and logos?","We can review logo artwork, colors and packaging for each selected model. Available decoration methods and order requirements are confirmed during quotation."),
("What is your MOQ for wholesale orders?","Minimum order quantity depends on bottle model, stock availability and customization. Send us the products and estimated volume to get an accurate answer."),
("Do you offer samples before bulk production?","Sample availability, lead time and cost are confirmed according to the product and destination. Please include your model number and required custom work."),
("Which bottle materials can you supply?","PC, Tritan, PP and PETG options are available according to customer requirements. Ask about BPA-free options for a selected model and request documentation for your destination market."),
("Do you have your own factory?","XUYI operates its own manufacturing facility and may coordinate production through selected partner facilities for some products. We confirm project requirements and applicable quality controls."),
("How long does production and shipping take?","Production and shipping timelines depend on model, order quantity, materials, custom artwork and destination. We provide an order-specific timeline after reviewing requirements."),
("Can I send a product drawing or a similar product sample?","Yes, you can describe the target design and send artwork or specifications. Our team can evaluate what can be supplied or customized and whether tooling is needed."),
("Can we mix colors or different models in one order?","Possible combinations depend on the bottle series, packing process and order quantity. Include your requested color and model breakdown when asking for a quote."),
("Can you provide test reports for my export market?","Please specify the model, destination country and required standards. Any documents offered must match the actual product, material and valid test scope."),
("Are there online prices or a shopping cart?","No. This is a business-to-business quotation website. We quote based on model, quantity, customization and delivery terms.")
]
from blog_catalog_source import load_guides
BLOG_POSTS={post["slug"]:post for post in load_guides(ROOT)}
# D1 is the editable source of truth for published Blog bodies. The build
# snapshot may contain summary rows for the index and full rows for CMS-owned
# articles; when a full row is present, overlay the matching static guide so
# the default static build reflects the reviewed D1 content without changing
# its existing slug or route. Incomplete summary rows never erase the
# reviewed template fallback.
for _d1_post in BUILD_STATE.get("blogPosts",[]):
 if not isinstance(_d1_post,dict):continue
 _slug=str(_d1_post.get("slug") or "")
 if _slug in BLOG_POSTS and isinstance(_d1_post.get("sections"),list) and len(_d1_post["sections"])>=2:
  BLOG_POSTS[_slug]={**BLOG_POSTS[_slug],**_d1_post}
ARTICLES=[(post["slug"],post["title"],post["description"]) for post in reversed(list(BLOG_POSTS.values()))]


