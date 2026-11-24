// XUYI Blog CMS extends Demalong's D1-backed page-editor and revision approach.
// Match the separately reviewed static Blog sources on D1-backed live routes.
import EDITORIAL_EVIDENCE from "../../data/editorial-evidence.json" with {type:"json"};
import BUYER_PATHWAYS from "../../data/blog-buyer-pathways.json" with {type:"json"};
import BLOG_FEATURE_PATHWAYS from "../../data/blog-feature-pathways.json" with {type:"json"};
import BUYER_MATRICES from "../../data/blog-buyer-decision-tables.json" with {type:"json"};
import BLOG_DEPTH from "../../data/blog-depth-evidence-en.json" with {type:"json"};
import DEEP_PART1 from "../../data/blog-deep-research-part1.json" with {type:"json"};
import DEEP_PART2 from "../../data/blog-deep-research-part2.json" with {type:"json"};
import DEEP_PART3 from "../../data/blog-deep-research-part3.json" with {type:"json"};
import SOURCE_BLOG_GUIDES from "../../data/blog-guides.json" with {type:"json"};
import INLINE_PART1 from "../../data/blog-inline-edits-reviewed-part1.json" with {type:"json"};
import INLINE_PART2 from "../../data/blog-inline-edits-reviewed-part2.json" with {type:"json"};
import SITE_CONFIG from "../../deployment/site.config.json" with {type:"json"};
const REVIEWED_INLINE={...INLINE_PART1,...INLINE_PART2};
const SITE_ORIGIN=SITE_CONFIG.site.origin;
const SOURCE_GUIDE_BY_SLUG=Object.fromEntries(SOURCE_BLOG_GUIDES.map(p=>[p.slug,p]));
/** Genuine paragraph-level editorial links, conditional on unchanged D1
 * intro, section heading and paragraph. Owner changes take priority.
 */
export function reviewedBlogParagraphNote(post,section,index){
 const source=SOURCE_GUIDE_BY_SLUG[post?.slug],reviewed=REVIEWED_INLINE[post?.slug];
 if(!source||!reviewed||post?.intro!==source.intro
    ||!Array.isArray(post?.sections)||post.sections.length!==source.sections.length
    ||section?.heading!==source.sections[index]?.heading
    ||section?.paragraph!==source.sections[index]?.paragraph)return "";
 const item=reviewed.find(n=>n.section===index);
 if(!item)return "";
 const writing=item.text?.en;
 if(typeof writing!=="string"||writing.split("{model}").length!==2||!/^[0-9]+$/.test(item.sku))
    throw Error("Invalid reviewed model annotation "+post.slug);
 const [before,after]=writing.split("{model}");
 const link='<a class="blog-editorial__product-link" href="/products/'+esc(item.sku)+'/">model '+esc(item.sku)+'</a>';
 return ' <span class="blog-editorial__product-note" data-editorial-model="'+esc(item.sku)+'">'+esc(before)+link+esc(after)+'</span>';
}
export function reviewedBlogRelatedAtEnd(post){
 // Original legacy D1 rows were imported without the manually reviewed
 // related-guide selections; use the reviewed editorial source ONLY while
 // the published article body remains unchanged. Later owner-picked related
 // slugs take priority. An explicit relatedReading=false suppresses this.
 const source=SOURCE_GUIDE_BY_SLUG[post?.slug];
 if(post?.relatedReading===false)return "";
 const chosen=Array.isArray(post?.related)?post.related:[];
 const pristine=Boolean(source)&&post.intro===source.intro &&
   Array.isArray(post.sections)&&post.sections.length===source.sections.length &&
   post.sections.every((s,i)=>s.heading===source.sections[i].heading&&s.paragraph===source.sections[i].paragraph);
 const selected=chosen.length?chosen:(pristine?source.related:[]);
 const used=new Set(),items=[];
 for(const slug of selected){
  if(typeof slug!=="string"||slug===post.slug||used.has(slug))continue;
  const info=SOURCE_GUIDE_BY_SLUG[slug];
  if(!info)continue;
  items.push(info);used.add(slug);
  if(items.length===3)break;
 }
 if(!items.length)return "";
 let out='<section class="section section--soft blog-related"><div class="shell"><div class="section__head"><div><span class="eyebrow">CONTINUE READING</span><h2 class="section__title">Related Buying Guides</h2></div></div><div class="blog-related__grid">';
 for(const info of items)
  out+='<article class="blog-related__item"><a href="/blog/'+esc(info.slug)+'/"><strong>'+esc(info.title)+'</strong></a><p>'+esc(info.description)+'</p></article>';
 return out+'</div></div></section>';
}
const ORIGINAL_GUIDE_INTROS=Object.fromEntries(SOURCE_BLOG_GUIDES.map(post=>[post.slug,post.intro]));
const DEEP_ENTRIES={...BLOG_DEPTH.articles,...DEEP_PART1.articles,...DEEP_PART2.articles,...DEEP_PART3.articles};

export function renderDepthEvidence(post){
 const row=DEEP_ENTRIES[post?.slug];
 // Any D1 editor update to the article intro overrides this stock source
 // expansion. An explicit false also wins and survives normalized CMS saves.
 const original=row?.baselineIntro??ORIGINAL_GUIDE_INTROS[post?.slug];
 if(!row||!original||post?.depthEvidence===false||String(post?.intro||"").trim()!==original)return "";
 let out='<section class="blog-deep-dive" id="source-reviewed-deep-dive"><h2>'+esc(row.title||'Material sourcing: detailed buyer decisions')+'</h2>';
 for(const section of row.sections)
  out+='<section class="blog-deep-dive__section"><h3>'+esc(section.heading)+'</h3><p>'+esc(section.paragraph)+'</p></section>';
 if(Array.isArray(row.sources)&&row.sources.length){
  out+='<nav class="blog-deep-dive__sources" aria-label="Official research references"><h3>Research references from official authorities</h3><ul>';
  for(const source of row.sources){
   if(!/^https:\/\/(?:www\.fda\.gov|www\.cpsc\.gov|www\.iso\.org|www\.ftc\.gov|www\.ista\.org|www\.eastman\.com|support\.gs1\.org|food\.ec\.europa\.eu|eur-lex\.europa\.eu|echa\.europa\.eu|iccwbo\.org|www\.uspto\.gov|www\.uspto\.gov|www\.pantone\.com|health\.clevelandclinic\.org)\//.test(source.url))continue;
   out+='<li><a href="'+esc(source.url)+'" rel="noopener noreferrer" target="_blank">'+esc(source.label)+' ↗</a></li>';
  }
  out+='</ul><p>These independent educational sources are not certificates of any XUYI product, material or factory.</p></nav>';
 }
 return out+'</section>';
}
export function renderBuyerDecisionTable(post){
 const entry=post?.buyerDecisionTable===false?null:
             (post?.buyerDecisionTable && typeof post.buyerDecisionTable==="object"?
               post.buyerDecisionTable:BUYER_MATRICES.articles[post?.slug]);
 if(!entry)return "";
 const head=entry.head,rows=entry.rows;
 if(!Array.isArray(head)||head.length!==3||!Array.isArray(rows)||rows.length<4)return "";
 if(rows.some(row=>!Array.isArray(row)||row.length!==3))return "";
 const safeLinks=(Array.isArray(entry.links)?entry.links:[]).filter(([label,url])=>
   typeof label==="string"&&typeof url==="string"&&/^\/(?!\/)[A-Za-z0-9/_#-]+$/.test(url));
 let body='<section class="blog-buyer-matrix" id="buyer-decision-table"><h2>'+esc(entry.title)+'</h2><p>'+esc(entry.intro)+'</p><div class="blog-buyer-matrix__scroll"><table><thead><tr>';
 body+=head.map(value=>'<th scope="col">'+esc(value)+'</th>').join('');
 body+='</tr></thead><tbody>';
 for(const cells of rows)
  body+='<tr><th scope="row">'+esc(cells[0])+'</th>'+cells.slice(1).map(value=>'<td>'+esc(value)+'</td>').join('')+'</tr>';
 body+='</tbody></table></div><p class="blog-buyer-matrix__note">Buyer decision criteria, not XUYI certification, published MOQ or guaranteed delivery times. Verify the exact model and market requirements.</p>';
 body+='<nav class="blog-buyer-matrix__links" aria-label="Relevant product and collection references">';
 body+=safeLinks.map(([label,url])=>'<a href="'+esc(url)+'">'+esc(label)+' →</a>').join('');
 return body+'</nav></section>';
}

export const esc = value => String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
/** CMS body paragraphs are plain text with optional trusted local links.
 * Editors persist [Model 2095](/products/2095/) in D1. Escape all text
 * first, then turn only reviewed local product-link syntax into <a> tags.
 */
export function renderEditableParagraph(value){
  return esc(value).replace(/\[([^\]\n]{2,100})\]\(\/products\/([a-zA-Z0-9_-]{2,80})\/\)/g,
    (_,label,slug)=>'<a class="blog-editorial__product-link" href="/products/'+slug+'/">'+label+'</a>');
}
function dedupeSectionParagraphs(sections){
 const seen=new Set();
 return (Array.isArray(sections)?sections:[]).map(section=>{
  const parts=String(section?.paragraph??'').trim().split(/\n\s*\n/).map(x=>x.trim()).filter(Boolean);
  const kept=[];
  for(const part of parts){
   const key=part.replace(/\s+/g,' ').trim().toLocaleLowerCase();
   if(key.length>=80&&seen.has(key))continue;
   if(key)seen.add(key);
   kept.push(part);
  }
  return {...section,paragraph:kept.join('\n\n')};
 });
}
function verifiedEvidence(post){
 const evidence=EDITORIAL_EVIDENCE[post?.slug];
 if(!evidence)return "";
 const sourceLinks=evidence.sources.filter(s=>
  /^https:\/\/(?:www\.fda\.gov|support\.gs1\.org|food\.ec\.europa\.eu|eur-lex\.europa\.eu|www\.iso\.org|www\.eastman\.com|www\.uspto\.gov|www\.pantone\.com|health\.clevelandclinic\.org)\//.test(s.url))
  .map(s=>'<li><a href="'+esc(s.url)+'" target="_blank" rel="noopener noreferrer">'+esc(s.label)+' ↗</a></li>').join("");
 if(sourceLinks.length===0)return "";
 return '<section class="blog-evidence" id="primary-sources" aria-labelledby="primary-sources-heading"><span class="eyebrow">SOURCE-CHECKED BUYER NOTES</span><h2 id="primary-sources-heading">'+esc(evidence.title)+'</h2><p>'+esc(evidence.insight)+'</p><p><strong>Practical next step:</strong> '+esc(evidence.next_step)+'</p><h3>Primary references</h3><ul>'+sourceLinks+'</ul><p class="blog-evidence__caveat">External regulations and standards are independent references, not product certification or proof of testing by XUYI. Confirm applicability and the latest rules for the exact product, destination and transaction date.</p></section>';
}
function contentModifiedDate(post){
 const value=String(post?.updated||"").slice(0,10);
 if(renderDepthEvidence(post)&&value<"2026-10-14")return "2026-10-14";
 return EDITORIAL_EVIDENCE[post?.slug] && value<"2026-10-10"?"2026-10-10":value;
}
function actualPublishedDate(post){
 const raw=String(post?.published_at||post?.updated||"").slice(0,10);
 return /^\d{4}-\d{2}-\d{2}$/.test(raw)?raw:"";
}
export async function ensureBlogSchema(db){
 await db.prepare("CREATE TABLE IF NOT EXISTS xuyi_blog_posts (slug TEXT PRIMARY KEY,status TEXT NOT NULL DEFAULT 'draft',content_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,published_at TEXT)").run();
 await db.prepare("CREATE INDEX IF NOT EXISTS idx_xuyi_blog_status ON xuyi_blog_posts(status,updated_at)").run();
 await db.prepare("CREATE TABLE IF NOT EXISTS xuyi_blog_drafts (slug TEXT PRIMARY KEY,draft_json TEXT NOT NULL,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)").run();
}
const str=(x,max=300)=>String(x??'').trim().slice(0,max);
const slugOk=x=>/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(x)&&x.length<=120;
const IMAGE=/^(\/media\/(?:ppt\/slide-\d{3}\.webp|excel\/row-\d{3}\.webp|group\/[a-z0-9-]+\.webp|blog\/[a-z0-9_-]+\.(?:webp|png|jpg|jpeg))|\/assets\/[a-zA-Z0-9/_-]+\.(?:webp|png|jpg|jpeg))$/;
function normalizeBuyerDecisionTable(raw){
 if(raw===false)return false; // Explicit CMS editorial suppression.
 if(raw==null)return undefined; // Fall back to reviewed source for untouched posts.
 if(typeof raw!=="object"||Array.isArray(raw))throw Error("Invalid buyer table");
 const title=str(raw.title,180),intro=str(raw.intro,900);
 const head=(Array.isArray(raw.head)?raw.head:[]).map(v=>str(v,100));
 const rows=(Array.isArray(raw.rows)?raw.rows:[]).slice(0,10)
   .map(row=>Array.isArray(row)?row.map(v=>str(v,500)):[]);
 const links=(Array.isArray(raw.links)?raw.links:[]).slice(0,5)
   .map(pair=>Array.isArray(pair)?[str(pair[0],120),str(pair[1],180)]:[]);
 if(title.length<10||intro.length<35||head.length!==3||head.some(v=>v.length<3)
    ||rows.length<4||rows.some(row=>row.length!==3||row.some(v=>v.length<2))
    ||links.some(([label,url])=>!label||!/^\/(?!\/)[a-zA-Z0-9/_#-]+$/.test(url)))
  throw Error("Buyer decision table needs 3 headings, 4+ valid rows and local links");
 return {title,intro,head,rows,links};
}
export function normalizeBlogPost(raw){
 const slug=str(raw?.slug,140).toLowerCase();if(!slugOk(slug))throw Error('Invalid slug.');
 const title=str(raw?.title,125),description=str(raw?.description,250),intro=str(raw?.intro,2000);
 if(title.length<12||description.length<25||intro.length<50)throw Error('Title, description and introduction must be substantive.');
 const cover=str(raw?.cover,220);if(!IMAGE.test(cover))throw Error('Use a local XUYI image path.');
  const coverAlt=str(raw?.coverAlt,240)||title;
 const items=raw?.sections;
 if(!Array.isArray(items)||items.length<2||items.length>24)throw Error('Please write 2–24 article sections.');
 const sections=items.map(s=>({heading:str(s?.heading,140),paragraph:str(s?.paragraph,4200)}));
 if(sections.some(s=>s.heading.length<5||s.paragraph.length<60))throw Error('Each section needs a heading and paragraph.');
 const faqs=(Array.isArray(raw?.faqs)?raw.faqs:[]).slice(0,12).map(q=>({question:str(q?.question,220),answer:str(q?.answer,1500)}));
 if(faqs.some(x=>!x.question||!x.answer))throw Error('FAQ questions and answers must be complete.');
 const checklist=(Array.isArray(raw?.checklist)?raw.checklist:[]).slice(0,16).map(v=>str(v,300)).filter(Boolean);
 const related=(Array.isArray(raw?.related)?raw.related:[]).slice(0,5).map(x=>str(x,120)).filter(slugOk).filter(x=>x!==slug);
 const group=str(raw?.group,70)||'Buyer Resources',updated=new Date().toISOString().slice(0,10);
 const primary_keyword=str(raw?.primary_keyword,110),secondary_keywords=(Array.isArray(raw?.secondary_keywords)?raw.secondary_keywords:[]).slice(0,12).map(v=>str(v,110)).filter(Boolean);
 const buyerDecisionTable=normalizeBuyerDecisionTable(raw?.buyerDecisionTable);
 return {slug,title,description,intro,cover,coverAlt,sections,faqs,checklist,related,group,category:'Buyer Resources',primary_keyword,secondary_keywords,updated,
  ...(buyerDecisionTable!==undefined?{buyerDecisionTable}:{}),
  ...(raw?.depthEvidence===false?{depthEvidence:false}:{}),
  ...(raw?.relatedReading===false?{relatedReading:false}:{}),
  ...(vettedBlogPerson(raw)?{authorPerson:{...vettedBlogPerson(raw),verified:true}}:{})};
}
export async function listBlogPosts(db,status=''){
 await ensureBlogSchema(db);
  const st=status?db.prepare('SELECT * FROM xuyi_blog_posts WHERE status=? ORDER BY COALESCE(published_at,updated_at) DESC,slug ASC').bind(status):db.prepare('SELECT * FROM xuyi_blog_posts ORDER BY COALESCE(published_at,updated_at) DESC,slug ASC');
 const rows=(await st.all()).results||[];
 const saved=(await db.prepare('SELECT slug FROM xuyi_blog_drafts').all()).results||[];
 const hasDraft=new Set(saved.map(x=>x.slug));
 return rows.map(row=>{
  let post={};try{post=JSON.parse(row.content_json)}catch{}
  return {...post,slug:row.slug,status:row.status,updated_at:row.updated_at,published_at:row.published_at,has_draft:hasDraft.has(row.slug)};
 });
}
export async function findBlogPost(db,slug){
 await ensureBlogSchema(db);
 const row=await db.prepare('SELECT * FROM xuyi_blog_posts WHERE slug=?').bind(slug).first();
 if(!row)return null;
 let post;try{post=JSON.parse(row.content_json)}catch{return null}
 return {...post,status:row.status,updated_at:row.updated_at,published_at:row.published_at};
}
export async function findEditableBlogPost(db,slug){
 const post=await findBlogPost(db,slug);
 if(!post)return null;
 const draft=await db.prepare('SELECT draft_json FROM xuyi_blog_drafts WHERE slug=?').bind(slug).first();
 if(!draft)return post;
 try{return {...JSON.parse(draft.draft_json),status:post.status,isDraftVersion:true,slug,published_at:post.published_at}}
 catch{return post}
}
function vettedBlogPerson(post){
 const person=post?.authorPerson;
 if(!person||person.verified!==true)return null;
 const name=str(person.name,100),jobTitle=str(person.jobTitle,120),url=str(person.url,300);
 if(name.length<2||jobTitle.length<3)return null;
 if(!/^https:\/\/(?:xuyibottles\.com\/[a-z0-9/_-]+\/|(?:www\.)?linkedin\.com\/in\/[a-z0-9_-]+\/?)$/i.test(url))
   return null;
 return {"@type":"Person",name,jobTitle,url};
}
// New editorial product annotations are fields of the CMS article itself,
// not a frozen three-model fallback. Removing/editing notes in D1 takes precedence.
function reviewedProductNotes(post,sectionIndex){
 if(post?.product_notes===false||!Array.isArray(post?.product_notes))return "";
 const notes=post.product_notes.filter(x=>Number(x?.section)===sectionIndex).slice(0,5);
 const used=new Set();
 let out="";
 for(const note of notes){
  const sku=String(note?.sku||"");
  if(!/^[A-Za-z0-9][A-Za-z0-9-]{1,23}$/.test(sku)||used.has(sku))continue;
  const pattern=str(note?.text?.en,1000);
  const label=str(note?.label?.en,180);
  if(pattern.split("{product}").length!==2||label.length<3)continue;
  used.add(sku);
  const href="/products/"+sku+"/";
  const link='<a class="blog-editorial__product-link" href="'+href+'">'+esc(label)+'</a>';
  const parts=pattern.split("{product}");
  out+=' <span class="blog-editorial__product-note" data-editorial-model="'+sku+'">'+esc(parts[0])+link+esc(parts[1])+'</span>';
 }
 return out;
}
export function blogHtml(post){
 const renderedSections=dedupeSectionParagraphs(post.sections);
 let body='<section class="page-intro"><div class="shell"><div class="breadcrumb"><a href="/">Home</a> / <a href="/blog/">Blog</a> / Buying Guide</div><span class="eyebrow">XUYI · PLASTIC DRINKWARE</span><h1>'+esc(post.title)+'</h1><p>'+esc(post.description)+'</p></div></section>';
 body+='<section class="section blog-editorial"><div class="shell"><div class="blog-detail__cover"><img src="'+esc(post.cover)+'" alt="'+esc(post.coverAlt||post.title)+'" width="1200" height="800" loading="eager"></div><div class="blog-editorial__layout"><aside class="blog-editorial__aside"><div class="blog-toc"><span class="eyebrow">IN THIS GUIDE</span><nav aria-label="Article sections">';
 for(let i=0;i<post.sections.length;i++)body+='<a href="#article-section-'+i+'">'+esc(post.sections[i].heading)+'</a>';
 const published=actualPublishedDate(post),modified=contentModifiedDate(post);
 const timeline=(published?'<time datetime="'+esc(published)+'">Published '+esc(published)+'</time>':'')+
   (modified&&modified>published?' · <time datetime="'+esc(modified)+'">Reviewed '+esc(modified)+'</time>':'');
 const person=vettedBlogPerson(post);
 const byline='<p class="blog-author-byline"><a rel="author" href="'+esc(person?.url||'/about/')+'">'+
   (person?'By '+esc(person.name)+' · '+esc(person.jobTitle):
     'By XUYI Bottles · Product Sourcing Editorial Team')+'</a></p>';
 body+='</nav><a class="blog-toc__quote" href="/contact/#inquiry">Discuss your project →</a></div></aside><article class="article blog-editorial__body"><div class="blog-meta"><span>BUYER RESOURCES</span><span>'+timeline+'</span></div>'+byline+'<p class="blog-lede">'+esc(post.intro)+'</p>';
 if(post.checklist?.length){body+='<div class="blog-takeaway"><strong>Before requesting a quote</strong><ul>';for(const tip of post.checklist.slice(0,3))body+='<li>'+esc(tip)+'</li>';body+='</ul></div>'}
 renderedSections.forEach((section,i)=>{const sourceSection=post.sections[i];body+='<section class="blog-section" id="article-section-'+i+'"><h2>'+esc(section.heading)+'</h2><p>'+renderEditableParagraph(section.paragraph)+reviewedBlogParagraphNote(post,sourceSection,i)+reviewedProductNotes(post,i)+'</p></section>'});
 body+=verifiedEvidence(post);
 body+=renderBuyerDecisionTable(post);
 body+=renderDepthEvidence(post);
 if(post.checklist?.length){body+='<section class="blog-checklist"><h2>Buyer checklist</h2><ul>';for(const tip of post.checklist)body+='<li>'+esc(tip)+'</li>';body+='</ul></section>'}
 const visibleFaqs=Array.isArray(post.faqs)?post.faqs.filter(q=>String(q?.question||'').trim()&&String(q?.answer||'').trim()):[];
 if(visibleFaqs.length){body+='<section class="blog-faq"><h2>Frequently asked questions</h2>';for(const q of visibleFaqs)body+='<details><summary>'+esc(q.question)+'</summary><p>'+esc(q.answer)+'</p></details>';body+='</section>'}
 body+='<div class="blog-editorial__cta"><h2>Need a quote for a specific model?</h2><p>Send the model, expected order quantity, logo requirements and destination market. XUYI can review confirmed material and customization options.</p><a class="button" href="/contact/#inquiry">Request a Plastic Bottle Quote →</a></div>';
 // The live EN article comes from D1, unlike reviewed translated static
 // articles. Derive the extra reader link from the same shared 9-post map
 // used by the static build; never overwrite any stored D1 article content.
 const destination=BUYER_PATHWAYS[post.slug];
 if(destination){
  const allowed={
   "collections/sports-water-bottles":"Compare plastic sports water bottles",
   "collections/kids-water-bottles":"Browse children's bottle models",
   "capabilities/custom-water-bottle":"Review custom plastic bottle options",
   "request-sample":"Plan a product sample request",
   "features/straw-lid":"Explore straw-lid bottle designs",
   "capabilities/oem-odm":"Compare OEM and ODM services"
  };
  if(!Object.hasOwn(allowed,destination))throw Error("Unknown editorial link target");
  body+='<section class="seo-next-buyer"><h2>Continue your sourcing research</h2><p>View this related product or buying guide: <a href="/'+esc(destination)+'/">'+esc(allowed[destination])+' →</a></p></section>';
 }
 // Place the D1 editor-selected related reading INSIDE the article end.
 if(post.relatedReading===false)body+='<!-- XUYI_OWNER_RELATED_READING_DISABLED -->';
 body+=reviewedBlogRelatedAtEnd(post);
 body+='</article></div></div></section>';
 // D1 replaces the built English article's <main>, so this must share the
 // same source mapping as the static five-language builder. Append *outside*
 // the article, retaining the original approved page layout and D1 content.
 const features=BLOG_FEATURE_PATHWAYS["blog/"+post.slug]||[];
 if(features.length){
  const labels={
   "applications/everyday-hydration":"Everyday hydration applications",
   "applications/kids-school":"Kids and school bottle applications",
   "applications/outdoor-travel":"Outdoor and travel applications",
   "applications/promotional-gifts":"Promotional gift bottle applications",
   "features/large-capacity":"Large-capacity bottle designs",
   "features/carry-handle":"Carry-handle bottle options",
   "features/gradient-colors":"Gradient-color bottle options",
   "features/straw-lid":"Straw-lid bottle options",
   "blog/bulk-water-bottles-for-school-student-programs":"School and student-program bottle buying guide",
   "blog/corporate-wellness-water-bottle-bulk-sourcing":"Corporate wellness bottle sourcing guide",
   "blog/parks-recreation-water-bottle-bulk-procurement":"Parks and recreation bottle procurement guide"
  };
  let links="";
  for(const target of features){
   if(!Object.hasOwn(labels,target))throw Error("Unexpected curated feature pathway");
   links+='<a href="/'+esc(target)+'/">'+esc(labels[target])+' →</a>';
  }
  body+='<section class="section buyer-pathways" aria-label="Explore related buyer resources"><div class="shell"><h2>Explore related buyer resources</h2><p>Compare relevant use cases, procurement guidance and bottle features before selecting a model.</p><div class="buyer-pathways__links">'+links+'</div></div></section>';
 }
 return body;
}
/**
 * Rebuild the order of localized CMS Blog cards from the exact D1 list order.
 * Card HTML is owner/localizer content: keep each complete article block
 * byte-for-byte and change only its position. No batch slug or date is hardcoded.
 */
function blogGridRange(source){
 const open='<div class="blog-listing__grid">',start=source.indexOf(open);
 if(start<0)throw Error("Localized Blog grid is missing");
 const token=/<\/?div\b[^>]*>/gi;token.lastIndex=start+open.length;
 let depth=1,match;
 while((match=token.exec(source))){
  if(/^<div\b/i.test(match[0])&&!/\/\s*>$/.test(match[0]))depth++;
  else if(/^<\/div\b/i.test(match[0]))depth--;
  if(depth===0)return {start,openEnd:start+open.length,closeStart:match.index,closeEnd:token.lastIndex};
 }
 throw Error("Localized Blog grid is not balanced");
}

// Recover leaf cards from both valid HTML and the historical malformed records
// where wrapper articles were added without matching closing tags. A card's
// own first closing tag is sufficient because real cards do not contain
// nested article elements; wrapper openings are discarded when another card
// opening appears before that first close.
function balancedBlogCards(inner){
 const open=/<article\b[^>]*class=["'][^"']*\bnews-card\b[^"']*["'][^>]*>/gi;
 const openings=[...inner.matchAll(open)].map(match=>({start:match.index,tagEnd:match.index+match[0].length}));
 const records=[],leaves=[];
 for(const item of openings){
  const close=/<\/article\b[^>]*>/i.exec(inner.slice(item.tagEnd));
  if(!close)continue;
  const candidate={start:item.start,end:item.tagEnd+close.index+close[0].length};
  records.push(candidate);
  const next=openings.find(nextItem=>nextItem.start>item.start);
  if(!next||next.start>=candidate.end)leaves.push(candidate);
 }
 if(!leaves.length)throw Error("Localized Blog cards could not be recovered");
 return {records,leaves:leaves.sort((a,b)=>a.start-b.start)};
}

function cardSlug(block){
 const hrefs=[...String(block).matchAll(/href="\/(?:[a-z]{2}\/)?blog\/([a-z0-9]+(?:-[a-z0-9]+)*)\//g)].map(x=>x[1]);
 if(hrefs.length!==3||new Set(hrefs).size!==1)throw Error("Localized Blog card identity or link count is invalid");
 return hrefs[0];
}

export function sortLocalizedBlogIndexByD1Order(currentHtml,d1OrderedSlugs,replacements=new Map()){
 const source=String(currentHtml??"");
 if(!Array.isArray(d1OrderedSlugs)||!d1OrderedSlugs.length)throw Error("D1 published Blog order is required");
 const expected=d1OrderedSlugs.map(value=>String(value??""));
 if(expected.some(slug=>!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug))||new Set(expected).size!==expected.length)
  throw Error("D1 published Blog order contains an invalid or duplicate slug");
 const grid=blogGridRange(source),parsed=balancedBlogCards(source.slice(grid.openEnd,grid.closeStart));
  if(parsed.leaves.length>expected.length||(!replacements.size&&parsed.leaves.length!==expected.length))throw Error("Localized Blog card count differs from D1 published count");
 const bySlug=new Map(),actual=[];
 for(const item of parsed.leaves){
  const block=source.slice(grid.openEnd+item.start,grid.openEnd+item.end),slug=cardSlug(block);
  if(bySlug.has(slug))throw Error("Duplicate localized Blog card: "+slug);
  bySlug.set(slug,replacements.get(slug)||block);actual.push(slug);
 }
 for(const [slug,block] of replacements){
  if(!expected.includes(slug))throw Error("Replacement is not in D1 published Blog order: "+slug);
  bySlug.set(slug,block);
 }
  for(const slug of expected)if(!bySlug.has(slug)&&!replacements.has(slug))throw Error("D1 published Blog article has no localized card: "+slug);
 const cards=expected.map(slug=>bySlug.get(slug));
 const nested=parsed.records.length!==parsed.leaves.length;
 if(!nested&&replacements.size===0&&actual.every((slug,index)=>slug===expected[index]))return source;
 return source.slice(0,grid.openEnd)+cards.join("\n")+source.slice(grid.closeStart);
}

export function blogCard(post){
 const url='/blog/'+post.slug+'/';
 return '<article class="news-card"><a href="'+url+'" class="news-card__image"><img src="'+esc(post.cover)+'" alt="'+esc(post.coverAlt||post.title)+'" width="1200" height="800" loading="lazy"></a><div class="news-card__info"><span class="news-card__category">'+esc((post.group||'Buyer Resources').toUpperCase())+'</span><h3><a href="'+url+'">'+esc(post.title)+'</a></h3><p>'+esc(post.description)+'</p><a class="news-card__read" href="'+url+'">Read Article →</a></div></article>';
}
export function composePage(template,body,post,route){
 if(!template.includes('<main id="main-content">'))throw Error('Blog page template missing');
 let html=template.replace(/<main id="main-content">[\s\S]*?<\/main>/,'<main id="main-content">'+body+'</main>');
 if(post){
  const url=SITE_ORIGIN+route;
  html=html.replace(/<title>[\s\S]*?<\/title>/,'<title>'+esc(post.title)+'</title>');
  html=html.replace(/<meta name="description" content="[^"]*">/,'<meta name="description" content="'+esc(post.description)+'">');
  html=html.replace(/<link rel="canonical" href="[^"]*">/,'<link rel="canonical" href="'+esc(url)+'">');
  html=html.replace(/<meta property="og:url" content="[^"]*">/,'<meta property="og:url" content="'+esc(url)+'">');
  const social=[['og:title',post.title],['og:description',post.description]];
  for(const [key,value] of social){
   const tag='<meta property="'+key+'" content="'+esc(value)+'">';
   const match=new RegExp('<meta property="'+key+'" content="[^"]*">');
   html=match.test(html)?html.replace(match,tag):html.replace('</head>',tag+'</head>');
  }
  // If the owner changes a D1 article cover, do not reuse dimensions of
  // the old immutable static shell's image (they may be incorrect).
  const oldOg=html.match(/<meta property="og:image" content="([^"]*)">/);
  const newOgUrl=SITE_ORIGIN+post.cover;
  if(!oldOg || oldOg[1]!==newOgUrl)
   html=html.replace(/<meta property="og:image:(?:width|height)" content="\d+">/g,'');
  html=html.replace(/<meta property="og:image" content="[^"]*">/,'');
  html=html.replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/g,'');
  const graph={'@context':'https://schema.org','@type':'BlogPosting',headline:post.title,description:post.description,inLanguage:'en',dateModified:contentModifiedDate(post),mainEntityOfPage:url,author:vettedBlogPerson(post)||{'@type':'Organization',name:'XUYI Bottles',url:SITE_ORIGIN+'/about/'},publisher:{'@type':'Organization',name:'XUYI Bottles'},image:[SITE_ORIGIN+post.cover]};
  if(actualPublishedDate(post))graph.datePublished=actualPublishedDate(post);
  if(EDITORIAL_EVIDENCE[post.slug])graph.citation=EDITORIAL_EVIDENCE[post.slug].sources
    .filter(s=>/^https:\/\/(?:www\.fda\.gov|support\.gs1\.org|food\.ec\.europa\.eu|eur-lex\.europa\.eu|www\.iso\.org|www\.eastman\.com|www\.uspto\.gov|www\.pantone\.com|health\.clevelandclinic\.org)\//.test(s.url))
    .map(s=>({'@type':'CreativeWork',name:s.label,url:s.url}));
  const safe=JSON.stringify(graph).replace(/</g,'\\u003c');
  // Only the actual visible CMS FAQs are marked up; no Google-rich-result promise.
  const validFaqs=Array.isArray(post.faqs)?post.faqs.filter(q=>
    typeof q?.question==="string"&&q.question.trim()&&typeof q?.answer==="string"&&q.answer.trim()):[];
  const faqMarkup=validFaqs.length
   ?'<script type="application/ld+json">'+JSON.stringify({
       '@context':'https://schema.org','@type':'FAQPage',inLanguage:'en',url,
       mainEntity:validFaqs.map(q=>({'@type':'Question',name:q.question,
         acceptedAnswer:{'@type':'Answer',text:q.answer}}))
     }).replace(/</g,'\\u003c')+'</script>':'';
  html=html.replace('</head>','<meta property="og:image" content="'+esc(SITE_ORIGIN+post.cover)+'"><script type="application/ld+json">'+safe+'</script>'+faqMarkup+'</head>');
 }
 return html;
}



