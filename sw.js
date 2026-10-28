/* تکیما — service worker
   فقط برای سرعت: فایل‌های ثابت (استایل، اسکریپت، فونت، تصویر) بعد از اولین بازدید از حافظهٔ خود دستگاه خوانده می‌شوند.
   صفحه‌ها همیشه اول از اینترنت گرفته می‌شوند تا مطلب تازه دیده شود؛ اگر اینترنت کند یا قطع بود، نسخهٔ ذخیره‌شده نشان داده می‌شود.
   با هر تغییر در فایل‌های ثابت، عدد VERSION را عوض کنید. */
const VERSION = "eff3488d61";
const STATIC = "techima-static-" + VERSION;
const PAGES = "techima-pages-" + VERSION;
const BASE = new URL("./", self.location).pathname; // e.g. /Techima.github.io/
const PRECACHE = ["assets/css/style.css", "assets/js/main.js", "assets/js/comments.js", "assets/fonts/Vazirmatn-Variable.woff2", "favicon.png"];
const SKIP = ["admin-comments", "/nimacrm", "/Comment", "/backend", "comments.json", "sitemap.xml", "robots.txt", "sw.js"];
const PAGE_WAIT_MS = 3500;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC).then((c) => Promise.all(PRECACHE.map((p) => c.add(BASE + p).catch(() => {})))).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("techima-") && k !== STATIC && k !== PAGES).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function skipped(url) { return SKIP.some((s) => url.pathname.indexOf(s) !== -1); }
function isStatic(url) { return /\.(?:css|js|woff2?|png|jpe?g|webp|avif|svg|ico|gif)$/i.test(url.pathname); }
function cacheable(res) { return res && res.status === 200 && res.type === "basic"; }

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC);
  const cached = await cache.match(request);
  const network = fetch(request).then((res) => { if (cacheable(res)) cache.put(request, res.clone()); return res; });
  if (cached) { network.catch(() => {}); return cached; }
  return network;
}

async function networkFirstWithTimeout(request) {
  const cache = await caches.open(PAGES);
  const cached = await cache.match(request);
  const network = fetch(request).then((res) => { if (cacheable(res)) cache.put(request, res.clone()); return res; });
  if (!cached) return network.catch(() => cache.match(BASE) .then((r) => r || Response.error()));
  return Promise.race([
    network.catch(() => cached),
    new Promise((resolve) => setTimeout(() => resolve(cached), PAGE_WAIT_MS))
  ]);
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.indexOf(BASE) !== 0 || skipped(url)) return;
  if (req.mode === "navigate") { event.respondWith(networkFirstWithTimeout(req)); return; }
  if (isStatic(url)) event.respondWith(staleWhileRevalidate(req));
});
