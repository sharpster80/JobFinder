self.addEventListener("push", function(event) {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || "JobFinder", {
      body: data.body || "New job match!",
      icon: "/icon.png",
      data: { url: data.url },
    })
  );
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  if (event.notification.data?.url) {
    clients.openWindow(event.notification.data.url);
  }
});
