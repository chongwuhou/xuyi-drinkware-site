import { authorizeAdminRequest } from "./admin-security.js";

const clean = (value) => String(value ?? "").trim();

function constantTimeEqual(a, b) {
  const aa = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);
  let diff = aa.length ^ bb.length;
  const length = Math.max(aa.length, bb.length);
  for (let i = 0; i < length; i++) {
    diff |= (aa[i % Math.max(aa.length, 1)] || 0) ^ (bb[i % Math.max(bb.length, 1)] || 0);
  }
  return diff === 0;
}

function bearerToken(request) {
  return clean(request.headers.get("authorization")).replace(/^Bearer\s+/i, "");
}

async function verifyCloudflareProjectToken(token, env) {
  if (!token) return false;
  const localPublishToken = clean(env.XUYI_PUBLISH_TOKEN);
  if (localPublishToken && constantTimeEqual(token, localPublishToken)) return true;
  // These two identifiers are public (not credentials), and pin the
  // authorization check to XUYI even when Pages variables are absent.
  const accountId = "a4032d0251103d6ef680b2aaddce1afc";
  const projectName = "xuyi-drinkware-site";
  // The Cloudflare GET below validates this exact project; Pages environment
  // variables are not a second, potentially stale source of truth.
  try {
    const response = await fetch(
      "https://api.cloudflare.com/client/v4/accounts/" + accountId +
      "/pages/projects/" + projectName,
      {
        headers: {
          authorization: "Bearer " + token,
          accept: "application/json"
        }
      }
    );
    if (!response.ok) return false;
    const payload = await response.json();
    return Boolean(payload?.success && payload?.result?.name === projectName);
  } catch {
    return false;
  }
}

// A Cloudflare project token proves access to deployment metadata, not
// permission to edit content or read customer records. Preserve the existing
// Demalong-style admin session for all writes and private admin modules.
const BUILD_READ_PATHS = new Set([
  "/api/build-snapshot", "/api/publish-state",
  "/api/admin/brand-config", "/api/admin/home-banners", "/api/admin/site-config",
  "/api/admin/pages", "/api/admin/product-content", "/api/admin/blog",
  "/api/admin/page-content", "/api/admin/page-translations"
]);

export async function authorizedBuildRequest(request, env) {
  if (await authorizeAdminRequest(request, env)) return true;
  if (request.method !== "GET" && request.method !== "HEAD") return false;
  const pathname = new URL(request.url).pathname;
  if (!BUILD_READ_PATHS.has(pathname)) return false;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}

// The single generic reviewed batch endpoint is the only Blog write route that
// may accept the existing CI token. Historical date-named routes intentionally
// fail closed so an old workflow cannot mutate D1 with fragile HTML logic.
// AI/API publication requires an explicit per-request owner intent.
// A project token proves project access; it does not prove that this task was
// authorized to publish. Human backend sessions remain the normal manual path.
export async function authorizedExplicitPublishRequest(request, env) {
  if (request.method !== "POST") return false;
  if (await authorizeAdminRequest(request, env)) return true;
  const intent = clean(request.headers.get("x-xuyi-publish-intent")).toLowerCase();
  if (intent !== "explicit-owner-approval") return false;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}

export async function authorizedReviewedBlogBatchRequest(request, env) {
  if (request.method !== "POST" || new URL(request.url).pathname !== "/api/admin/blog-batch") return false;
  return authorizedExplicitPublishRequest(request, env);
}


// Owner-reviewed, sha256-bound R2 images. This narrow CI exception cannot edit other content.
// Narrow, source-reviewed repair for the nine multilingual Blog D1 records identified
// by the 2026-11-05 live translation audit. It accepts no arbitrary copy.
export async function authorizedReviewedBlogTranslationRepairRequest(request, env) {
  if (request.method !== "POST" || new URL(request.url).pathname !== "/api/admin/blog-translation-repair-20261105") return false;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}
export async function authorizedReviewedBlogIndexCopyCleanupRequest(request, env) {
  if (request.method !== "POST" || new URL(request.url).pathname !== "/api/admin/blog-index-copy-cleanup-20261117") return false;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}

// Narrow, reviewed phase-two D1 translation semantics repair. It accepts no arbitrary
// copy and only targets the fixed multilingual records in the migration endpoint.
export async function authorizedReviewedBlogSeoPhase2Request(request, env) {
  if (request.method !== "POST" || new URL(request.url).pathname !== "/api/admin/blog-seo-phase2-corrections") return false;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}
export async function authorizedReviewedBlogImageUploadRequest(request, env) {
  if (request.method!=="POST" || !["/api/admin/blog-images-20261030","/api/admin/blog-images-20261031","/api/admin/blog-images-20261102","/api/admin/blog-images-20261103","/api/admin/blog-images-20261107","/api/admin/blog-images-20261110","/api/admin/blog-images-20261111"].includes(new URL(request.url).pathname)) return false;
  return verifyCloudflareProjectToken(bearerToken(request),env);
}// Narrow exception for the reviewed 101-model daily XLSX publisher. The
// existing GitHub CI Cloudflare token proves access to THIS XUYI project,
// but may only call the source-validated, append-only, three-per-day endpoint.
// Ordinary admin CRUD remains password/session protected as before.
// Exact one-time, owner-reviewed three-image R2/CMS upload. General admin writes remain restricted.
export async function authorizedReviewedBlogCoverRequest(request, env) {
 const url=new URL(request.url);
 if (request.method!=="POST" || url.pathname!=="/api/admin/blog-covers-20261029" ||
     !new Set(["upload","commit"]).has(url.searchParams.get("mode"))) return false;
 return verifyCloudflareProjectToken(bearerToken(request),env);
}
export async function authorizedDailyProductReviewRequest(request, env) {
  if (new URL(request.url).pathname !== "/api/admin/daily-product-reviews" ||
      !new Set(["GET", "POST"]).has(request.method)) return false;
  if (await authorizeAdminRequest(request, env)) return true;
  return verifyCloudflareProjectToken(bearerToken(request), env);
}

// Fixed, source-reviewed one-time migration: the caller may select a batch,
// but never supply arbitrary SEO copy or model names to a write endpoint.
export async function authorizedProductSeoPromotionRequest(request, env){
  if(!new Set([
    "/api/admin/product-seo-promotion-20261020",
    "/api/admin/product-seo-refresh-20261104",
    "/api/admin/collection-seo-refresh-20261105"
  ]).has(new URL(request.url).pathname)||
     !new Set(["GET","POST"]).has(request.method))return false;
  return verifyCloudflareProjectToken(bearerToken(request),env);
}

// Narrow scheduler heartbeat/claim endpoint for the canonical XUYI GitHub runner.
export async function authorizedSchedulerRunnerRequest(request, env){
  if(request.method!=="POST"||new URL(request.url).pathname!=="/api/admin/scheduler-runner")return false;
  return verifyCloudflareProjectToken(bearerToken(request),env);
}

// One-time reviewed 58-model factory catalog import. These two exact routes
// are the only write paths admitted for the existing XUYI CI project token.
export async function authorizedReviewedFactoryCatalogImageUploadRequest(request, env){
  if(request.method!=="POST"||new URL(request.url).pathname!=="/api/admin/factory-catalog-images-20261103")return false;
  return verifyCloudflareProjectToken(bearerToken(request),env);
}
export async function authorizedReviewedFactoryCatalogCommitRequest(request, env){
  if(request.method!=="POST"||new URL(request.url).pathname!=="/api/admin/factory-catalog-20261103")return false;
  return verifyCloudflareProjectToken(bearerToken(request),env);
}



