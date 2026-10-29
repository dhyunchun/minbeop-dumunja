// 앱 화면을 기기에 저장해 두어 오프라인에서도 열리게 한다.
// 온라인이면 항상 새 버전을 먼저 받아오고(network-first), 실패하면 저장본을 쓴다.
const CACHE = "dumunja-__BUILD__";
const SHELL = ["./", "index.html", "firebase.js", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const cacheable = sameOrigin || url.hostname === "www.gstatic.com" || url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com");
  if (!cacheable) return; // Firebase 로그인·저장 요청은 그대로 통과
  e.respondWith(
    fetch(req).then((res) => {
      if (res && (res.ok || res.type === "opaque")) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((m) => m || (req.mode === "navigate" ? caches.match("index.html") : Response.error())))
  );
});
