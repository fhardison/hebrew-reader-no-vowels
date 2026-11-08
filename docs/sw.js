/*
 * Service worker for the Hebrew reader.
 *
 * Strategy: cache-first. Everything the reader needs is served from the
 * offline cache when present; anything else is fetched from the network and
 * saved for next time. Content only changes when the user presses "Update"
 * (see pwa.js), which downloads a fresh copy of every file into a new cache
 * and then deletes the old one.
 *
 * This file is static on purpose, so that a rebuild of the books never forces
 * the browser to reinstall the worker.
 */

const PREFIX = 'hebrew-reader-';
const SHELL = [
  './',
  'index.html',
  'pwa.js',
  'manifest.webmanifest',
  'icons/icon-192.png',
  'icons/icon-512.png',
];

// Newest cache by name (names end in a zero-padded timestamp).
async function newestCache() {
  const names = (await caches.keys()).filter((n) => n.startsWith(PREFIX)).sort();
  return caches.open(names.length ? names[names.length - 1] : PREFIX + '0000000000000');
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await newestCache();
    await cache.addAll(SHELL.map((u) => new Request(u, { cache: 'reload' })));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

function offlinePage() {
  const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Offline</title>
<style>body{font-family:Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px;font-size:1.2em}</style>
</head><body><h1>Not downloaded yet</h1>
<p>This book hasn't been saved for offline use. Reconnect to the internet, then open the
<a href="./">book list</a> and press <b>Download all</b>.</p></body></html>`;
  return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // The file list is how the app learns that a new version exists: always ask the network.
  if (url.pathname.endsWith('/files.json')) {
    event.respondWith(
      fetch(req, { cache: 'no-store' }).catch(() => caches.match(req, { ignoreSearch: true }))
    );
    return;
  }

  // The Update button asks for fresh copies with cache: 'reload'. Those must come
  // from the server, never from the offline cache, or an update would just
  // re-save the old files.
  // (A hard refresh of a page while offline still falls back to the saved copy.)
  if (req.cache === 'reload' || req.cache === 'no-store') {
    event.respondWith(fetch(req).catch(async (err) => {
      if (req.mode !== 'navigate') throw err;
      return (await caches.match(req, { ignoreSearch: true })) || offlinePage();
    }));
    return;
  }

  event.respondWith((async () => {
    // caches.match searches every cache, oldest first, so an update that is
    // still downloading never shadows the complete copy.
    const hit = await caches.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok) (await newestCache()).put(req, res.clone());
      return res;
    } catch (err) {
      if (req.mode === 'navigate') return offlinePage();
      throw err;
    }
  })());
});
