/* Task Hub service worker.
 *
 * Lives at the site root rather than under /taskhub/ because the website route
 * rule `/taskhub/<path:app_path>` would answer with the SPA's HTML instead of
 * this file. Registered with an explicit scope of /taskhub/ so it never
 * intercepts the ERPNext desk.
 *
 * Deliberately has no fetch handler: the hub is a live view of shared data, and
 * a cached board showing yesterday's tickets is worse than an honest error.
 */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "Task Hub";
  const options = {
    body: data.body || "",
    icon: "/assets/task_hub/icon-192.png",
    badge: "/assets/task_hub/icon-192.png",
    // Same tag replaces an earlier notification for the same ticket instead of
    // stacking five of them on the lock screen.
    tag: data.tag || "task-hub",
    renotify: true,
    data: { url: data.url || "/taskhub" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/taskhub";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((list) => {
        // Reuse an open hub window rather than piling up tabs; only fall back
        // to a new one when the app isn't already running.
        for (const client of list) {
          if (client.url.includes("/taskhub") && "focus" in client) {
            client.navigate(target).catch(() => {});
            return client.focus();
          }
        }
        return self.clients.openWindow(target);
      })
  );
});
