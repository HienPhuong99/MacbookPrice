/* Service Worker PWA offline cho Giá MacBook (đường dẫn tương đối cho subpath /MacbookPrice/) */
const APP_CACHE = 'macprice-app-v2';
const DATA_CACHE = 'macprice-data-v2';
const APP_ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/favicon.svg',
  './assets/apple-touch-icon.png',
  './assets/icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(APP_CACHE).then(cache => cache.addAll(APP_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  const keep = new Set([APP_CACHE, DATA_CACHE]);
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => !keep.has(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function withOfflineHeader(res) {
  const headers = new Headers(res.headers);
  headers.set('X-Offline-Cache', '1');
  const body = await res.arrayBuffer();
  return new Response(body, { status: res.status, statusText: res.statusText, headers });
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Dữ liệu JSON/summary: ưu tiên mạng, mất mạng thì trả bản lưu mới nhất (bỏ query ?_= khi khớp cache)
  if (/\/data\/(macbook\.json|summary\.txt|menu\.json)$/.test(url.pathname)) {
    const cacheKey = new Request(url.origin + url.pathname);
    event.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(DATA_CACHE).then(c => c.put(cacheKey, copy)).catch(() => {});
          }
          return res;
        })
        .catch(async () => {
          const hit = await caches.open(DATA_CACHE).then(c => c.match(cacheKey));
          return hit ? withOfflineHeader(hit) : new Response('{"error":"offline"}', {
            status: 503,
            headers: { 'Content-Type': 'application/json; charset=utf-8' },
          });
        })
    );
    return;
  }

  // Điều hướng HTML: network-first để không kẹt bản cũ trên iOS PWA, rơi về cache khi offline
  if (req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('/index.html')) {
    event.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(APP_CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
          }
          return res;
        })
        .catch(async () => {
          const cache = await caches.open(APP_CACHE);
          return (await cache.match('./index.html')) || (await cache.match('./'));
        })
    );
    return;
  }

  // Tài nguyên tĩnh (assets, manifest): cache-first, thiếu thì lấy mạng rồi lưu
  event.respondWith(
    caches.open(APP_CACHE).then(async cache => {
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
      return res;
    })
  );
});
