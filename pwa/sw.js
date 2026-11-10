// Service worker za PWA verziju Finana.
//
// Namjerno NE sprema podatke ni stranice u cache: Streamlit radi preko žive
// websocket veze, pa „offline” verzija ionako ne bi mogla ništa prikazati — a
// financijski podaci ne smiju ostati zapisani na uređaju. Jedino što se čuva je
// mala stranica „Nema veze”, koja se pokaže umjesto bijelog ekrana bez mreže.

const CACHE = "finan-v1";
const OFFLINE = "./offline.html";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.add(OFFLINE)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ključevi) => Promise.all(
        ključevi.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  // Samo otvaranje stranice ima rezervu; sve ostalo ide izravno na mrežu.
  if (e.request.mode !== "navigate") return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(OFFLINE))
  );
});
