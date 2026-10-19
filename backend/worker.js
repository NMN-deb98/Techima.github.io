/**
 * Techima comments API — Cloudflare Worker
 * Required variables: PUBLIC_REPO, PRIVATE_REPO, ALLOWED_ORIGIN.
 * Required secret: GITHUB_TOKEN (Contents read/write access to only those two repositories).
 * Email is written only to PRIVATE_REPO; the public repo contains display fields only.
 */
const API = "https://api.github.com";
const MAX_BODY_BYTES = 12000;

function response(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Vary": "Origin"
    }
  });
}
function utf8ToBase64(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}
function base64ToUtf8(value) {
  const binary = atob(value.replace(/\n/g, ""));
  return new TextDecoder().decode(Uint8Array.from(binary, ch => ch.charCodeAt(0)));
}
async function githubRequest(env, path, init = {}) {
  const res = await fetch(API + path, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + env.GITHUB_TOKEN,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "Techima-Comments-Worker",
      ...(init.headers || {})
    }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    console.error("GitHub API failure", res.status, path, data.message || "");
    const error = new Error("github_api_error");
    error.status = res.status;
    throw error;
  }
  return data;
}
async function writeRepoFile(env, repo, path, content, message, sha) {
  const body = { message, content: utf8ToBase64(content), branch: "main" };
  if (sha) body.sha = sha;
  return githubRequest(env, "/repos/" + repo + "/contents/" + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}
async function getPublicComments(env) {
  const res = await fetch("https://raw.githubusercontent.com/" + env.PUBLIC_REPO + "/main/comments.json", {
    headers: { "Cache-Control": "no-cache" }
  });
  if (!res.ok) throw new Error("comments_unavailable");
  const items = await res.json();
  if (!Array.isArray(items)) throw new Error("comments_invalid");
  return items;
}
async function appendPublicComment(env, comment) {
  const path = "comments.json";
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const current = await githubRequest(env, "/repos/" + env.PUBLIC_REPO + "/contents/" + path + "?ref=main");
    const items = JSON.parse(base64ToUtf8(current.content || ""));
    if (!Array.isArray(items)) throw new Error("comments_invalid");
    if (items.some(item => item.id === comment.id)) return;
    items.unshift(comment);
    try {
      await writeRepoFile(env, env.PUBLIC_REPO, path, JSON.stringify(items, null, 2) + "\n",
        "Add public Techima comment", current.sha);
      return;
    } catch (error) {
      if (attempt === 2 || (error.status && error.status !== 409 && error.status !== 422)) throw error;
    }
  }
}
function validEmail(value) {
  return typeof value === "string" && value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || "https://nmn-deb98.github.io";
    if (origin !== allowedOrigin) return new Response("Forbidden", { status: 403, headers: { "Cache-Control": "no-store" } });
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: {
        "Access-Control-Allow-Origin": allowedOrigin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin"
      }});
    }
    if (!env.GITHUB_TOKEN || !env.PUBLIC_REPO || !env.PRIVATE_REPO) return response({ error: "service_not_configured" }, 503, allowedOrigin);
    if (url.pathname !== "/comments") return response({ error: "not_found" }, 404, allowedOrigin);
    if (request.method === "GET") {
      try { return response({ comments: await getPublicComments(env) }, 200, allowedOrigin); }
      catch { return response({ error: "comments_unavailable" }, 503, allowedOrigin); }
    }
    if (request.method !== "POST") return response({ error: "method_not_allowed" }, 405, allowedOrigin);
    const contentLength = Number(request.headers.get("Content-Length") || 0);
    if (contentLength > MAX_BODY_BYTES) return response({ error: "payload_too_large" }, 413, allowedOrigin);
    if (!(request.headers.get("Content-Type") || "").toLowerCase().includes("application/json")) {
      return response({ error: "invalid_content_type" }, 415, allowedOrigin);
    }
    let rawBody;
    try { rawBody = await request.text(); } catch { return response({ error: "invalid_json" }, 400, allowedOrigin); }
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) return response({ error: "payload_too_large" }, 413, allowedOrigin);
    let input;
    try { input = JSON.parse(rawBody); } catch { return response({ error: "invalid_json" }, 400, allowedOrigin); }
    if (!input || typeof input !== "object" || Array.isArray(input)) return response({ error: "invalid_payload" }, 400, allowedOrigin);
    if (env.COMMENT_RATE_LIMIT_KV) {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const key = "comment-rate:" + ip;
      const now = Date.now();
      try {
        let state = await env.COMMENT_RATE_LIMIT_KV.get(key, "json");
        if (!state || state.resetAt <= now) state = { count: 0, resetAt: now + 900000 };
        if (state.count >= 5) return response({ error: "rate_limited", retryAfter: Math.ceil((state.resetAt - now) / 1000) }, 429, allowedOrigin);
        state.count += 1;
        await env.COMMENT_RATE_LIMIT_KV.put(key, JSON.stringify(state), { expirationTtl: 900 });
      } catch { return response({ error: "rate_limit_unavailable" }, 503, allowedOrigin); }
    }
    if (typeof input.website === "string" && input.website.trim()) return response({ ok: true }, 202, allowedOrigin);
    const name = typeof input.name === "string" ? input.name.trim() : "";
    const email = typeof input.email === "string" ? input.email.trim().toLowerCase() : "";
    const message = typeof input.message === "string" ? input.message.trim() : "";
    if (name.length < 2 || name.length > 80) return response({ error: "invalid_name" }, 400, allowedOrigin);
    if (!validEmail(email)) return response({ error: "invalid_email" }, 400, allowedOrigin);
    if (message.length < 2 || message.length > 3000) return response({ error: "invalid_message" }, 400, allowedOrigin);
    const id = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const privateRecord = {
      id, name, email, message, createdAt,
      page: typeof input.page === "string" && input.page.startsWith("/") ? input.page.slice(0, 160) : "/"
    };
    const publicRecord = { id, name, message, createdAt };
    try {
      const privatePath = "submissions/" + createdAt.slice(0, 7) + "/" + id + ".json";
      await writeRepoFile(env, env.PRIVATE_REPO, privatePath, JSON.stringify({ ...privateRecord, status: "pending" }, null, 2) + "\n",
        "Store pending private Techima comment submission", null);
      // Never publish automatically; publication requires a separate owner approval step.
      return response({ ok: true, pending: true }, 202, allowedOrigin);
    } catch {
      return response({ error: "submission_failed" }, 503, allowedOrigin);
    }
  }
};
