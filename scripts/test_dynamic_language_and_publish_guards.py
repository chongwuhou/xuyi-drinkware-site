#!/usr/bin/env python3
"""Static guardrails for the D1-configured language and Blog publish paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

settings = read("functions/_shared/site-settings.js")
scheduler = read("functions/_shared/publish-scheduler.js")
batch = read("functions/api/admin/blog-batch.js")
auth = read("functions/_shared/build-auth.js")
cms = read("functions/_shared/blog-cms.js")
snapshot = read("functions/api/build-snapshot.js")
admin = read("admin/index.html")
content_admin = read("assets/admin-content.js")
product_seo_admin = read("assets/admin-product-seo.js")

assert "export async function loadLanguageConfig" in settings
assert "export async function publishableLanguageCodes" in settings
assert "publicLanguages(languageConfig)" in snapshot
assert "configuredLocales(languageConfig)" in batch
assert "loadLanguageConfig(db)" in batch
assert '"/api/admin/blog-batch"' in auth
assert '"/api/admin/blog"' in auth
assert "/api/admin/blog-batch-20261111" not in auth
assert "if (await authorizeAdminRequest(request, env)) return true;" in auth
assert "locale IN ('es','pt','ru','tr')" not in scheduler
assert "prepared.length!==4" not in scheduler
assert "ORDER BY COALESCE(published_at,updated_at) DESC,slug ASC" in cms
assert "ORDER BY COALESCE(published_at,updated_at) DESC,slug ASC" in snapshot
runtime = read("functions/blog/[[path]].js")
assert 'runtimeMode=String(context.env.XUYI_BLOG_RUNTIME_MODE||"static").trim().toLowerCase()' in runtime
assert 'if(runtimeMode!=="dynamic")return context.next();' in runtime
assert "legacySortLocalizedBlogIndexByD1Order" not in cms
assert '<select id="product-seo-locale" required></select>' in admin
assert "五语言" not in admin and "101 个现有产品" not in admin
assert '["en","es","pt","ru","tr"]' not in content_admin
assert "已配置语种的图片 ALT" in content_admin
assert 'models.includes("2292")' not in product_seo_admin

print("XUYI_DYNAMIC_LANGUAGE_AND_SINGLE_BLOG_PUBLISH_GUARDS_PASS")


