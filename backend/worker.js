/**
 * Techima comments API — Cloudflare Worker.
 * Public submissions are private/pending until an authenticated admin approves them.
 * Secrets: GITHUB_TOKEN, ADMIN_TOKEN, ADMIN_USERNAME, ADMIN_PASSWORD. Variables: PUBLIC_REPO, PRIVATE_REPO, ALLOWED_ORIGIN.
 */
const API = "https://api.github.com";
const MAX_BODY_BYTES = 12000;
function response(body, status, origin) {
  return new Response(JSON.stringify(body), { status, headers: {
    "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff", "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization", "Vary": "Origin"
  }});
}
function utf8ToBase64(value) {
  const bytes = new TextEncoder().encode(value); let binary = "";
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}
function base64ToUtf8(value) {
  const binary = atob(value.replace(/\n/g, ""));
  return new TextDecoder().decode(Uint8Array.from(binary, ch => ch.charCodeAt(0)));
}
async function githubRequest(env, path, init = {}) {
  const res = await fetch(API + path, { ...init, headers: {
    "Accept": "application/vnd.github+json", "Authorization": "Bearer " + env.GITHUB_TOKEN,
    "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Techima-Comments-Worker",
    ...(init.headers || {})
  }});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    console.error("GitHub API failure", res.status, path, data.message || "");
    const error = new Error("github_api_error"); error.status = res.status; throw error;
  }
  return data;
}
async function readRepoFile(env, repo, path) {
  const data = await githubRequest(env, "/repos/" + repo + "/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=main");
  return { data: JSON.parse(base64ToUtf8(data.content || "")), sha: data.sha };
}
async function writeRepoFile(env, repo, path, content, message, sha) {
  const body = { message, content: utf8ToBase64(content), branch: "main" };
  if (sha) body.sha = sha;
  return githubRequest(env, "/repos/" + repo + "/contents/" + path.split("/").map(encodeURIComponent).join("/"), {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  });
}
async function getPublicComments(env) {
  const res = await fetch("https://raw.githubusercontent.com/" + env.PUBLIC_REPO + "/main/comments.json", { headers: { "Cache-Control": "no-cache" } });
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
      await writeRepoFile(env, env.PUBLIC_REPO, path, JSON.stringify(items, null, 2) + "\n", "Approve Techima comment", current.sha);
      return;
    } catch (error) {
      if (attempt === 2 || (error.status && error.status !== 409 && error.status !== 422)) throw error;
    }
  }
}
async function ipHash(request) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip));
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
}
async function ensureSecurityTables(env) {
  if (!env.DB) throw new Error("security_database_not_configured");
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS comments_login_attempts (ip_hash TEXT PRIMARY KEY, failed_count INTEGER NOT NULL, window_started INTEGER NOT NULL, blocked_until INTEGER NOT NULL DEFAULT 0)").run();
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS comment_rate_limits (ip_hash TEXT PRIMARY KEY, window_started INTEGER NOT NULL, count INTEGER NOT NULL)").run();
}
async function loginBlockState(env, hash) {
  const row = await env.DB.prepare("SELECT blocked_until FROM comments_login_attempts WHERE ip_hash = ?").bind(hash).first();
  return row && Number(row.blocked_until) > Date.now() ? Number(row.blocked_until) : 0;
}
async function recordLoginFailure(env, hash) {
  const now = Date.now(), windowStart = now - 15 * 60 * 1000, blockedUntil = now + 5 * 60 * 60 * 1000;
  await env.DB.prepare("INSERT INTO comments_login_attempts (ip_hash, failed_count, window_started, blocked_until) VALUES (?, 1, ?, 0) ON CONFLICT(ip_hash) DO UPDATE SET failed_count = CASE WHEN comments_login_attempts.window_started <= ? THEN 1 ELSE comments_login_attempts.failed_count + 1 END, window_started = CASE WHEN comments_login_attempts.window_started <= ? THEN excluded.window_started ELSE comments_login_attempts.window_started END, blocked_until = CASE WHEN (CASE WHEN comments_login_attempts.window_started <= ? THEN 1 ELSE comments_login_attempts.failed_count + 1 END) >= 6 THEN ? ELSE comments_login_attempts.blocked_until END")
    .bind(hash, now, windowStart, windowStart, windowStart, blockedUntil).run();
  const row = await env.DB.prepare("SELECT failed_count, blocked_until FROM comments_login_attempts WHERE ip_hash = ?").bind(hash).first();
  return row || { failed_count: 1, blocked_until: 0 };
}
async function allowCommentSubmission(env, hash) {
  const now = Date.now(), windowStart = now - 10 * 60 * 1000;
  await env.DB.prepare("INSERT INTO comment_rate_limits (ip_hash, window_started, count) VALUES (?, ?, 1) ON CONFLICT(ip_hash) DO UPDATE SET count = CASE WHEN comment_rate_limits.window_started <= ? THEN 1 ELSE comment_rate_limits.count + 1 END, window_started = CASE WHEN comment_rate_limits.window_started <= ? THEN excluded.window_started ELSE comment_rate_limits.window_started END")
    .bind(hash, now, windowStart, windowStart).run();
  const row = await env.DB.prepare("SELECT count, window_started FROM comment_rate_limits WHERE ip_hash = ?").bind(hash).first();
  if (!row) throw new Error("rate_limit_unavailable");
  return { allowed: Number(row.count) <= 3, retryAfter: Math.max(1, Math.ceil((Number(row.window_started) + 10 * 60 * 1000 - now) / 1000)) };
}
function validEmail(value) {
  return typeof value === "string" && value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || !a || !b) return false;
  let diff = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i += 1) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}
function base64UrlEncode(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}
function base64UrlDecode(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(normalized + "=".repeat((4 - normalized.length % 4) % 4));
  return Uint8Array.from(binary, ch => ch.charCodeAt(0));
}
async function signSession(env, payload) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.ADMIN_TOKEN), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const encoded = base64UrlEncode(new TextEncoder().encode(JSON.stringify(payload)));
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(encoded));
  return encoded + "." + base64UrlEncode(new Uint8Array(signature));
}
async function verifySession(env, token) {
  try {
    const parts = token.split(".");
    if (parts.length !== 2 || !env.ADMIN_TOKEN) return false;
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.ADMIN_TOKEN), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
    const valid = await crypto.subtle.verify("HMAC", key, base64UrlDecode(parts[1]), new TextEncoder().encode(parts[0]));
    if (!valid) return false;
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(parts[0])));
    return payload && payload.exp > Date.now() && payload.u === env.ADMIN_USERNAME;
  } catch { return false; }
}
async function listPending(env) {
  let root;
  try { root = await githubRequest(env, "/repos/" + env.PRIVATE_REPO + "/contents/submissions?ref=main"); }
  catch (error) { if (error.status === 404) return []; throw error; }
  if (!Array.isArray(root)) return [];
  const publicItems = await getPublicComments(env);
  const publishedIds = new Set(publicItems.map(item => item.id));
  const months = root.filter(item => item.type === "dir").slice(-24);
  const pending = [];
  for (const month of months) {
    const files = await githubRequest(env, "/repos/" + env.PRIVATE_REPO + "/contents/" + month.path.split("/").map(encodeURIComponent).join("/") + "?ref=main");
    if (!Array.isArray(files)) continue;
    for (const file of files.filter(item => item.type === "file" && item.name.endsWith(".json"))) {
      try {
        const record = await githubRequest(env, "/repos/" + env.PRIVATE_REPO + "/contents/" + file.path.split("/").map(encodeURIComponent).join("/") + "?ref=main");
        const item = JSON.parse(base64ToUtf8(record.content || ""));
        if (!publishedIds.has(item.id) && item.status !== "rejected" && item.status !== "approved") {
          pending.push({ id: item.id, name: item.name, message: item.message, createdAt: item.createdAt, page: item.page || "/" });
        }
      } catch (_) {}
    }
  }
  return pending.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))).slice(0, 100);
}
async function findSubmission(env, id) {
  if (!/^[0-9a-f-]{36}$/i.test(id)) throw new Error("invalid_id");
  const root = await githubRequest(env, "/repos/" + env.PRIVATE_REPO + "/contents/submissions?ref=main");
  if (!Array.isArray(root)) throw new Error("submission_not_found");
  for (const month of root.filter(item => item.type === "dir").slice(-24)) {
    const path = month.path + "/" + id + ".json";
    try {
      const file = await githubRequest(env, "/repos/" + env.PRIVATE_REPO + "/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=main");
      return { path, sha: file.sha, record: JSON.parse(base64ToUtf8(file.content || "")) };
    } catch (_) {}
  }
  throw new Error("submission_not_found");
}
async function updateStatus(env, found, status) {
  const record = { ...found.record, status, moderatedAt: new Date().toISOString() };
  await writeRepoFile(env, env.PRIVATE_REPO, found.path, JSON.stringify(record, null, 2) + "\n", "Moderate Techima comment: " + status, found.sha);
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || "https://nmn-deb98.github.io";
    if (origin !== allowedOrigin) return new Response("Forbidden", { status: 403, headers: { "Cache-Control": "no-store" } });
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: {
      "Access-Control-Allow-Origin": allowedOrigin, "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Max-Age": "86400", "Vary": "Origin"
    }});
    if (!env.GITHUB_TOKEN || !env.PUBLIC_REPO || !env.PRIVATE_REPO) return response({ error: "service_not_configured" }, 503, allowedOrigin);
    const url = new URL(request.url);
    if (url.pathname === "/comments" && request.method === "GET") {
      try { return response({ comments: await getPublicComments(env) }, 200, allowedOrigin); }
      catch { return response({ error: "comments_unavailable" }, 503, allowedOrigin); }
    }
    if (url.pathname === "/admin/login" && request.method === "POST") {
      if (!env.ADMIN_USERNAME || !env.ADMIN_PASSWORD || !env.ADMIN_TOKEN) return response({ error: "admin_login_not_configured" }, 503, allowedOrigin);
      let hash;
      try {
        await ensureSecurityTables(env);
        hash = await ipHash(request);
        const blockedUntil = await loginBlockState(env, hash);
        if (blockedUntil) return response({ error: "login_blocked", retryAfter: Math.ceil((blockedUntil - Date.now()) / 1000) }, 429, allowedOrigin);
      } catch { return response({ error: "security_check_unavailable" }, 503, allowedOrigin); }
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > 2000) return response({ error: "payload_too_large" }, 413, allowedOrigin);
      let input; try { input = JSON.parse(raw); } catch { return response({ error: "invalid_json" }, 400, allowedOrigin); }
      if (!safeEqual(input && input.username, env.ADMIN_USERNAME) || !safeEqual(input && input.password, env.ADMIN_PASSWORD)) {
        try {
          const state = await recordLoginFailure(env, hash);
          if (Number(state.blocked_until) > Date.now()) return response({ error: "login_blocked", retryAfter: Math.ceil((Number(state.blocked_until) - Date.now()) / 1000) }, 429, allowedOrigin);
        } catch { return response({ error: "security_check_unavailable" }, 503, allowedOrigin); }
        return response({ error: "invalid_credentials" }, 401, allowedOrigin);
      }
      try { await env.DB.prepare("DELETE FROM comments_login_attempts WHERE ip_hash = ?").bind(hash).run(); }
      catch { return response({ error: "security_check_unavailable" }, 503, allowedOrigin); }
      const token = await signSession(env, { u: env.ADMIN_USERNAME, exp: Date.now() + 30 * 60 * 1000 });
      return response({ ok: true, token, expiresIn: 1800 }, 200, allowedOrigin);
    }
    if (url.pathname.startsWith("/admin/")) {
      const auth = request.headers.get("Authorization") || "";
      if (!await verifySession(env, auth.startsWith("Bearer ") ? auth.slice(7) : "")) {
        return response({ error: "unauthorized" }, 401, allowedOrigin);
      }
      if (url.pathname === "/admin/comments" && request.method === "GET") {
        try { return response({ comments: await listPending(env) }, 200, allowedOrigin); }
        catch { return response({ error: "admin_list_failed" }, 503, allowedOrigin); }
      }
      if (request.method !== "POST" || !["/admin/comments/approve", "/admin/comments/reject"].includes(url.pathname)) {
        return response({ error: "not_found" }, 404, allowedOrigin);
      }
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > 2000) return response({ error: "payload_too_large" }, 413, allowedOrigin);
      let input; try { input = JSON.parse(raw); } catch { return response({ error: "invalid_json" }, 400, allowedOrigin); }
      if (!input || typeof input.id !== "string") return response({ error: "invalid_id" }, 400, allowedOrigin);
      try {
        const found = await findSubmission(env, input.id);
        if (url.pathname.endsWith("/approve")) {
          if (!found.record.name || !found.record.message || !found.record.createdAt) return response({ error: "invalid_submission" }, 400, allowedOrigin);
          await appendPublicComment(env, { id: found.record.id, name: String(found.record.name).slice(0, 80), message: String(found.record.message).slice(0, 3000), createdAt: found.record.createdAt });
          await updateStatus(env, found, "approved");
          return response({ ok: true }, 200, allowedOrigin);
        }
        await updateStatus(env, found, "rejected");
        return response({ ok: true }, 200, allowedOrigin);
      } catch (error) {
        if (error.message === "invalid_id") return response({ error: "invalid_id" }, 400, allowedOrigin);
        return response({ error: "moderation_failed" }, 503, allowedOrigin);
      }
    }
    if (url.pathname !== "/comments") return response({ error: "not_found" }, 404, allowedOrigin);
    if (request.method !== "POST") return response({ error: "method_not_allowed" }, 405, allowedOrigin);
    const contentLength = Number(request.headers.get("Content-Length") || 0);
    if (contentLength > MAX_BODY_BYTES) return response({ error: "payload_too_large" }, 413, allowedOrigin);
    if (!(request.headers.get("Content-Type") || "").toLowerCase().includes("application/json")) return response({ error: "invalid_content_type" }, 415, allowedOrigin);
    const rawBody = await request.text();
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) return response({ error: "payload_too_large" }, 413, allowedOrigin);
    let input; try { input = JSON.parse(rawBody); } catch { return response({ error: "invalid_json" }, 400, allowedOrigin); }
    if (!input || typeof input !== "object" || Array.isArray(input)) return response({ error: "invalid_payload" }, 400, allowedOrigin);
    if (typeof input.website === "string" && input.website.trim()) return response({ ok: true }, 202, allowedOrigin);
    let rate;
    try {
      await ensureSecurityTables(env);
      rate = await allowCommentSubmission(env, await ipHash(request));
    } catch { return response({ error: "rate_limit_unavailable" }, 503, allowedOrigin); }
    if (!rate.allowed) return response({ error: "rate_limited", retryAfter: rate.retryAfter }, 429, allowedOrigin);
    const name = typeof input.name === "string" ? input.name.trim() : "";
    const email = typeof input.email === "string" ? input.email.trim().toLowerCase() : "";
    const message = typeof input.message === "string" ? input.message.trim() : "";
    if (name.length < 2 || name.length > 80) return response({ error: "invalid_name" }, 400, allowedOrigin);
    if (!validEmail(email)) return response({ error: "invalid_email" }, 400, allowedOrigin);
    if (message.length < 2 || message.length > 3000) return response({ error: "invalid_message" }, 400, allowedOrigin);
    const id = crypto.randomUUID(); const createdAt = new Date().toISOString();
    const privateRecord = { id, name, email, message, createdAt, page: typeof input.page === "string" && input.page.startsWith("/") ? input.page.slice(0, 160) : "/", status: "pending" };
    try {
      const privatePath = "submissions/" + createdAt.slice(0, 7) + "/" + id + ".json";
      await writeRepoFile(env, env.PRIVATE_REPO, privatePath, JSON.stringify(privateRecord, null, 2) + "\n", "Store pending private Techima comment submission", null);
      return response({ ok: true, pending: true }, 202, allowedOrigin);
    } catch { return response({ error: "submission_failed" }, 503, allowedOrigin); }
  }
};
