// Single reviewed Blog batch writer. D1 remains the only content authority.
// The endpoint is generic and follows the configured publish-ready locales.
// Existing D1 records are never overwritten by a batch rerun.
import { authorizedReviewedBlogBatchRequest } from "../../_shared/build-auth.js";
import { ensureBlogSchema, listBlogPosts, sortLocalizedBlogIndexByD1Order } from "../../_shared/blog-cms.js";
import { ensureTranslationSchema } from "../../_shared/translation.js";
import { bumpPublishRevision, loadLanguageConfig, publicLanguages } from "../../_shared/site-settings.js";
import { repairReviewedBlogSource } from "../../_shared/blog-source-repairs.js";

const reply = (body, status = 200) => Response.json(body, {
  status,
  headers: { "cache-control": "no-store", "x-robots-tag": "noindex,nofollow,noarchive" }
});
const count = (value, part) => String(value).split(part).length - 1;
const countPattern = (value, pattern) => String(value).match(pattern)?.length || 0;
const hasClass = (html, className) => new RegExp(`<[^>]+\\bclass="[^"]*\\b${className}\\b[^"]*"[^>]*>`, "i").test(String(html));
const unsafeHtml = /<\s*(?:script|iframe|object|embed|form|style|link|base|meta|svg|math|template)\b|\bon[a-z-]+\s*=|\bsrcdoc\s*=|(?:javascript|vbscript|data)\s*:/i;
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function configuredLocales(config) {
  return publicLanguages(config).filter(item => item.code !== config.sourceLocale).map(item => item.code);
}

function validatePayload(payload, locales) {
  if (!payload || !Array.isArray(payload.posts) || payload.posts.length < 1 || payload.posts.length > 12 ||
      !Array.isArray(payload.translations) || !Array.isArray(payload.indexCards)) {
    throw Error("A reviewed Blog batch must contain posts, translations and index cards.");
  }
  const expected = new Set();
  for (const item of payload.posts) {
    const slug = String(item?.slug || "");
    const post = item?.post;
    if (!slugPattern.test(slug) || expected.has(slug) || post?.slug !== slug) throw Error("Unexpected or duplicate reviewed article: " + slug);
    if (typeof post.title !== "string" || post.title.length < 12 ||
        typeof post.description !== "string" || post.description.length < 25 ||
        typeof post.intro !== "string" || post.intro.length < 50 ||
        !/^\/(?:assets\/(?:blog|editorial|curated-hd|products)|media\/(?:blog|ppt|excel))\/[a-z0-9_-]+\.webp$/.test(String(post.cover || "")) ||
        !Array.isArray(post.sections) || post.sections.length !== 7 || post.sections.some(section => String(section?.paragraph || "").length < 650) ||
        !Array.isArray(post.checklist) || post.checklist.length !== 10 ||
        !Array.isArray(post.faqs) || post.faqs.length !== 4 ||
        !Array.isArray(post.related) || post.related.length !== 3 ||
        !Array.isArray(post.product_notes) || post.product_notes.length !== 3 ||
        JSON.stringify(post).length > 100000) {
      throw Error("Reviewed article content failed validation: " + slug);
    }
    expected.add(slug);
  }
  const expectedCells = expected.size * locales.length;
  if (payload.translations.length !== expectedCells || payload.indexCards.length !== expectedCells) {
    throw Error("The batch must contain one reviewed article page and one index card for every configured publish-ready locale.");
  }

  const seenTranslations = new Set();
  for (const item of payload.translations) {
    const route = String(item?.route || "");
    const match = /^\/blog\/([a-z0-9-]+)\/$/.exec(route);
    const locale = String(item?.locale || "");
    const key = route + "|" + locale;
    const html = String(item?.mainHtml || "");
    const requiredPageMarkers = [
      '<section class="page-intro">',
      '<h1>',
      '<section class="section blog-editorial">',
      'class="blog-detail__cover"',
      'class="blog-editorial__body"',
      'class="blog-meta"',
      'class="blog-editorial__cta"'
    ];
    if (!match || !expected.has(match[1]) || !locales.includes(locale) || seenTranslations.has(key) ||
        String(item?.title || "").length < 12 || String(item?.description || "").length < 25 ||
        html.length < 5000 || html.length > 250000 || unsafeHtml.test(html) ||
        (!requiredPageMarkers.every(marker => marker.startsWith("class=") ? hasClass(html, marker.slice(7, -1)) : html.includes(marker))) ||
        count(html, 'id="primary-sources"') !== 1 || count(html, 'class="blog-editorial__product-link"') !== 3 ||
        count(html, 'class="blog-related__item"') !== 3 || count(html, 'class="blog-buyer-matrix"') !== 1 || count(html, "<details>") !== 4) {
      throw Error("Reviewed translation failed validation: " + key);
    }
    seenTranslations.add(key);
  }
  for (const slug of expected) for (const locale of locales) {
    if (!seenTranslations.has("/blog/" + slug + "/|" + locale)) throw Error("Missing reviewed translation: " + slug + "|" + locale);
  }

  const seenCards = new Set();
  for (const item of payload.indexCards) {
    const slug = String(item?.slug || "");
    const locale = String(item?.locale || "");
    const key = slug + "|" + locale;
    const html = String(item?.html || "");
    const hrefPattern = new RegExp('href="(?:/[^"]+)?/blog/' + slug + '/"', "g");
    if (!expected.has(slug) || !locales.includes(locale) || seenCards.has(key) || html.length < 100 || html.length > 10000 ||
        unsafeHtml.test(html) || !html.startsWith('<article class="news-card">') || !html.endsWith("</article>") || countPattern(html, hrefPattern) !== 3) {
      throw Error("Reviewed index card failed validation: " + key);
    }
    seenCards.add(key);
  }
  for (const slug of expected) for (const locale of locales) {
    if (!seenCards.has(slug + "|" + locale)) throw Error("Missing reviewed index card: " + slug + "|" + locale);
  }
  return [...expected];
}

function contentForTranslation(item) {
  return JSON.stringify({ title: item.title, description: item.description, mainHtml: item.mainHtml });
}

export async function onRequestPost(context) {
  if (!(await authorizedReviewedBlogBatchRequest(context.request, context.env))) return reply({ error: "Unauthorized reviewed batch request" }, 401);
  const db = context.env.XUYI_DB;
  if (!db) return reply({ error: "XUYI_DB binding missing" }, 503);
  let payload;
  try { payload = await context.request.json(); } catch { return reply({ error: "Invalid JSON" }, 400); }

  try {
    await ensureBlogSchema(db);
    await ensureTranslationSchema(db);
    if (payload?.action === "repair-reviewed-source") {
      return reply(await repairReviewedBlogSource(db));
    }
    const languageConfig = await loadLanguageConfig(db);
    const locales = configuredLocales(languageConfig);
    const slugs = validatePayload(payload, locales);
    const now = new Date().toISOString();

    // Preflight conflicts before any write. A rerun is idempotent only when
    // the current D1 record is byte-for-byte the same reviewed record.
    const newPostStatements = [];
    for (const item of payload.posts) {
      const content = JSON.stringify(item.post);
      const existing = await db.prepare("SELECT status,content_json FROM xuyi_blog_posts WHERE slug=?").bind(item.slug).first();
      if (existing && existing.status !== "published") {
        return reply({ error: "Existing D1 article was changed; batch preserved the owner edit: " + item.slug }, 409);
      }
      if (!existing) newPostStatements.push(db.prepare("INSERT INTO xuyi_blog_posts(slug,status,content_json,published_at) VALUES(?,'published',?,?)").bind(item.slug, content, item.publishedAt || now));
      else if (existing.content_json !== content) return reply({ error: "Existing D1 article was changed; batch preserved the owner edit: " + item.slug }, 409);
    }

    const newTranslationStatements = [];
    for (const item of payload.translations) {
      const resource = "page:" + item.route;
      const translated = contentForTranslation(item);
      const existing = await db.prepare("SELECT translated_json FROM xuyi_translation_overrides WHERE resource_id=? AND locale=?").bind(resource, item.locale).first();
      if (existing && existing.translated_json !== translated) {
        return reply({ error: "Existing D1 translation was changed; batch preserved the owner edit: " + resource + "|" + item.locale }, 409);
      }
      if (!existing) newTranslationStatements.push(db.prepare("INSERT INTO xuyi_translation_overrides(resource_id,locale,translated_json,reviewed_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(resource_id,locale) DO NOTHING").bind(resource, item.locale, translated));
    }
    const insertResults = (newPostStatements.length || newTranslationStatements.length)
      ? await db.batch([...newPostStatements, ...newTranslationStatements]) : [];
    const postsInserted = insertResults.slice(0, newPostStatements.length).reduce((sum, row) => sum + Number(row?.meta?.changes || 0), 0);
    const translationsInserted = insertResults.slice(newPostStatements.length).reduce((sum, row) => sum + Number(row?.meta?.changes || 0), 0);

    const d1Order = (await listBlogPosts(db, "published")).map(post => post.slug);
    if (!d1Order.length || new Set(d1Order).size !== d1Order.length || slugs.some(slug => !d1Order.includes(slug))) {
      return reply({ error: "D1 published Blog order is incomplete or duplicated" }, 409);
    }

    const indexCards = new Map(payload.indexCards.map(item => [item.locale + "|" + item.slug, item.html]));
    const orderStatements = [];
    for (const locale of locales) {
      const row = await db.prepare("SELECT translated_json FROM xuyi_translation_overrides WHERE resource_id='page:/blog/' AND locale=?").bind(locale).first();
      if (!row?.translated_json) return reply({ error: "Localized Blog index override missing: " + locale }, 409);
      let index; try { index = JSON.parse(row.translated_json); } catch { return reply({ error: "Localized Blog index JSON invalid: " + locale }, 409); }
      const replacements = new Map(slugs.map(slug => [slug, indexCards.get(locale + "|" + slug)]));
      if ([...replacements.values()].some(value => !value)) return reply({ error: "Localized Blog index card missing: " + locale }, 409);
      const ordered = sortLocalizedBlogIndexByD1Order(String(index.mainHtml || ""), d1Order, replacements);
      if (ordered !== index.mainHtml) {
        orderStatements.push(db.prepare("UPDATE xuyi_translation_overrides SET translated_json=?,reviewed_at=CURRENT_TIMESTAMP WHERE resource_id='page:/blog/' AND locale=? AND translated_json=?").bind(JSON.stringify({ ...index, mainHtml: ordered }), locale, row.translated_json));
      }
    }
    const orderResults = orderStatements.length ? await db.batch(orderStatements) : [];
    if (orderResults.some(row => Number(row?.meta?.changes || 0) !== 1)) return reply({ error: "Localized Blog index changed during the conditional D1-order update" }, 409);

    for (const locale of locales) {
      const row = await db.prepare("SELECT translated_json FROM xuyi_translation_overrides WHERE resource_id='page:/blog/' AND locale=?").bind(locale).first();
      let index; try { index = JSON.parse(row?.translated_json || "{}"); } catch { return reply({ error: "Final localized Blog index JSON invalid: " + locale }, 409); }
      if (sortLocalizedBlogIndexByD1Order(String(index.mainHtml || ""), d1Order) !== index.mainHtml) return reply({ error: "Localized Blog index does not match D1 order: " + locale }, 409);
      for (const slug of slugs) {
        const detail = await db.prepare("SELECT translated_json FROM xuyi_translation_overrides WHERE resource_id=? AND locale=?").bind("page:/blog/" + slug + "/", locale).first();
        let detailJson; try { detailJson = JSON.parse(detail?.translated_json || "{}"); } catch { return reply({ error: "Final article translation JSON invalid: " + slug + "|" + locale }, 409); }
        const body = String(detailJson.mainHtml || "");
        if (body.length < 5000 || count(body, 'class="blog-section"') !== 7 || count(body, 'class="blog-editorial__product-link"') !== 3 || count(body, 'class="blog-related__item"') !== 3 || count(body, 'class="blog-buyer-matrix"') !== 1 || count(body, "<details>") !== 4) return reply({ error: "Final article translation is incomplete: " + slug + "|" + locale }, 409);
      }
    }

    const revision = await bumpPublishRevision(db);
    return reply({ success: true, postsInserted, translationsInserted, indexCardsAdded: payload.indexCards.length, localizedIndexesReordered: orderStatements.length, publishRevision: revision.revision, publishedSlugs: slugs, indexOrderVerified: locales, d1PublishedCount: d1Order.length });
  } catch (error) {
    return reply({ error: "D1 batch operation failed: " + String(error?.message || "unknown error").slice(0, 240) }, 500);
  }
}

