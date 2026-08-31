import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./index.css";

const app = createApp(App);

app.config.errorHandler = (err, vm, info) => {
  console.error(`[Task Hub] ${info}:`, err);
};

app.use(router);
app.mount("#app");

// Register the worker on boot so an already-subscribed device keeps receiving
// pushes after an app update. Permission is never requested here — that has to
// come from a deliberate tap in Settings, because a prompt on first load is the
// fastest way to get told "no" permanently.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/taskhub-sw.js", { scope: "/taskhub/" })
      .catch((e) => console.warn("[Task Hub] service worker not registered:", e));
  });
}
