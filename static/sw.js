// OTT Service Worker - offline support
const CACHE = "ott-v1";
const ASSETS = ["/", "/static/css/style.css", "/static/js/app.js", "/static/icon.svg"];

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener("fetch", (e) => {
    e.respondWith(
        caches.match(e.request).then(r => r || fetch(e.request).catch(() => caches.match("/")))
    );
});
