const CACHE_NAME = "polutelias-v1";

self.addEventListener("install", event => {
    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener("push", function(event) {
    let data = {};

    if (event.data) {
        data = event.data.json();
    }

    event.waitUntil(
        self.registration.showNotification(data.title || "Polutelias 💈", {
            body: data.body || "Νέα ειδοποίηση",
            icon: "/static/icon-192.png",
            badge: "/static/icon-192.png"
        })
    );
});
