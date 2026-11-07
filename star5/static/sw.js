/* Star5 Search service worker: makes the app installable and shows an offline page.
   It never caches pages or API answers: everything is private and behind the login. */
"use strict";
const SHARE_DB = "star5-share";
const SHARE_STORE = "inbox";
const OFFLINE = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Star5 Search</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;font:16px system-ui,sans-serif;
background:#05213a;color:#e9fffb;text-align:center;padding:24px;box-sizing:border-box}
button{margin-top:16px;font:inherit;padding:10px 18px;border-radius:10px;border:0;background:#5ee6f2;color:#05213a}</style>
</head><body><div><p><b>Star5 Search</b></p><p>Hors ligne · Offline · Sei offline</p>
<button onclick="location.reload()">↻</button></div></body></html>`;

function saveShare(data) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SHARE_DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(SHARE_STORE, {keyPath: "id", autoIncrement: true});
    request.onerror = () => reject(request.error || new Error("share database"));
    request.onsuccess = () => {
      const db = request.result, tx = db.transaction(SHARE_STORE, "readwrite");
      tx.objectStore(SHARE_STORE).add({...data, created: Date.now()});
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onabort = tx.onerror = () => { db.close(); reject(tx.error || new Error("share storage")); };
    };
  });
}

async function receiveShare(request) {
  const form = await request.formData();
  const allFiles = form.getAll("files").filter(value => typeof value !== "string" && value.size > 0);
  const files = allFiles.slice(0, 10);
  const data = {
    title: String(form.get("title") || "").slice(0, 4000),
    text: String(form.get("text") || "").slice(0, 4000),
    url: String(form.get("url") || "").slice(0, 4000),
    files,
    fileError: false,
    fileCount: allFiles.length,
  };
  try {
    await saveShare(data);
  } catch (error) {
    if (!files.length) throw error;
    await saveShare({...data, files: [], fileError: true});
  }
  return Response.redirect(new URL("/?shared=1", self.location.origin).href, 303);
}

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (url.origin === self.location.origin && url.pathname === "/share" && event.request.method === "POST") {
    event.respondWith(receiveShare(event.request).catch(error => {
      console.error("Could not save shared content", error);
      return new Response("Could not save shared content. Open Star5 Search and attach the content again.", {
        status: 507, headers: {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"},
      });
    }));
    return;
  }
  if (event.request.mode !== "navigate") return;
  event.respondWith(fetch(event.request).catch(() =>
    new Response(OFFLINE, {headers: {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}})));
});
