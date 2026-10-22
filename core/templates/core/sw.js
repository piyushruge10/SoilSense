{% load static %}
const VERSION = "v1";
const PAGES = `pages-${VERSION}`;
const ASSETS = `assets-${VERSION}`;
const DATA = `data-${VERSION}`;
const OFFLINE_URL = "{% url 'offline' %}";
const SENSOR_API = "{% url 'sensor-data' %}";
const CACHEABLE_PAGES = ["{% url 'dashboard' %}", "{% url 'plants' %}", "{% url 'settings' %}"];
const PRECACHE = [
  OFFLINE_URL,
  "{% static 'core/styles.css' %}",
  "{% static 'core/icons/icon-192.png' %}",
];
const NAV_TIMEOUT = 6000;

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(ASSETS).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => ![PAGES, ASSETS, DATA].includes(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const isCacheablePage = url => CACHEABLE_PAGES.includes(url.pathname);

async function cachePage(key, response) {
  // Never cache redirects (e.g. to the login page) or errors.
  if (response.ok && !response.redirected && isCacheablePage(new URL(key))) {
    const cache = await caches.open(PAGES);
    await cache.put(key, response.clone());
  }
}

async function offlineResponse() {
  return (await caches.match(OFFLINE_URL)) ||
    new Response("You are offline. Connect to the internet to open this page.", {status: 503});
}

async function handleNavigation(request) {
  const url = new URL(request.url);
  const cacheable = request.method === "GET" && isCacheablePage(url);
  const network = fetch(request).then(async response => {
    if (cacheable) await cachePage(request.url, response.clone());
    return response;
  });

  if (!cacheable) return network.catch(offlineResponse);

  const cache = await caches.open(PAGES);
  const cached = (await cache.match(request.url)) ||
    (await cache.match(request.url, {ignoreSearch: true}));
  if (!cached) return network.catch(offlineResponse);

  // Saved copy exists: use it if offline or if the server is slow to wake up.
  const timeout = new Promise(resolve => setTimeout(() => resolve(cached), NAV_TIMEOUT));
  return Promise.race([network.catch(() => cached), timeout]);
}

async function handleSensorApi(request) {
  const cache = await caches.open(DATA);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request.url, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request.url);
    if (!cached) {
      return new Response(JSON.stringify({error: "offline"}), {
        status: 503, headers: {"Content-Type": "application/json"},
      });
    }
    const data = await cached.json();
    data.connected = false;
    data.error = "You are offline. Showing the last saved readings.";
    return new Response(JSON.stringify(data), {headers: {"Content-Type": "application/json"}});
  }
}

async function handleAsset(request) {
  const cache = await caches.open(ASSETS);
  const cached = await cache.match(request);
  const refresh = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  });
  return cached || refresh;
}

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(request));
    return;
  }
  if (request.method !== "GET") return;

  if (url.pathname === SENSOR_API && url.searchParams.get("format") !== "csv") {
    event.respondWith(handleSensorApi(request));
  } else if (url.pathname.startsWith("/static/")) {
    event.respondWith(handleAsset(request));
  }
});

self.addEventListener("message", event => {
  const message = event.data || {};
  if (message.type === "clear-caches") {
    event.waitUntil(Promise.all([caches.delete(PAGES), caches.delete(DATA)]));
  } else if (message.type === "warm") {
    event.waitUntil(Promise.all(
      (message.urls || []).map(async path => {
        try {
          const key = new URL(path, self.location.origin).href;
          const response = await fetch(key, {credentials: "same-origin"});
          await cachePage(key, response);
        } catch (error) { /* offline: ignore */ }
      })
    ));
  }
});
