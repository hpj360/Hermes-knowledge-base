/**
 * Hermes 知识库 Service Worker — 手写原生 SW（无 Workbox / 无 vite-plugin-pwa）
 *
 * 缓存策略：
 *   - 静态资源（JS/CSS/字体/HTML 导航）→ cache-first（CACHE_STATIC）
 *   - 配方详情 API /api/lab/recipes/* → stale-while-revalidate（CACHE_RECIPES）
 *   - 问答 API /api/ask → network-first（不缓存，离线降级 503 JSON）
 *   - 离线降级页 /offline.html（导航请求失败时返回）
 */
const CACHE_STATIC = "hermes-static-v1";
const CACHE_RECIPES = "hermes-recipes-v1";
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_STATIC).then((c) => c.addAll(["/", "/manifest.json", "/offline.html"]))
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => ![CACHE_STATIC, CACHE_RECIPES].includes(k))
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  // 问答 API：network-first，不缓存，离线降级 503 JSON
  if (url.pathname.startsWith("/api/ask")) {
    e.respondWith(
      fetch(e.request).catch(
        () =>
          new Response(JSON.stringify({ error: "offline" }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          })
      )
    );
    return;
  }

  // 配方 API：stale-while-revalidate
  if (url.pathname.startsWith("/api/lab/recipes/")) {
    e.respondWith(
      caches.open(CACHE_RECIPES).then(async (cache) => {
        const cached = await cache.match(e.request);
        const fetchPromise = fetch(e.request)
          .then((resp) => {
            if (resp.ok) cache.put(e.request, resp.clone());
            return resp;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // 静态资源：cache-first，离线时导航请求降级到 offline.html
  e.respondWith(
    caches.match(e.request).then((cached) =>
      cached ||
      fetch(e.request)
        .then((resp) => {
          if (
            resp.ok &&
            (e.request.url.includes("/assets/") ||
              e.request.url.endsWith(".css") ||
              e.request.url.endsWith(".js"))
          ) {
            const clone = resp.clone();
            caches.open(CACHE_STATIC).then((c) => c.put(e.request, clone));
          }
          return resp;
        })
        .catch(() =>
          e.request.mode === "navigate"
            ? caches.match(OFFLINE_URL).then((r) => r || caches.match("/"))
            : caches.match("/")
        )
    )
  );
});
