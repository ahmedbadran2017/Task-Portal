import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "./pages/Dashboard.vue";
import Board from "./pages/Board.vue";
import TicketList from "./pages/TicketList.vue";
import Settings from "./pages/Settings.vue";
import Teams from "./pages/Teams.vue";
import MyWork from "./pages/MyWork.vue";

const routes = [
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", name: "dashboard", component: Dashboard },
  { path: "/board", name: "board", component: Board },
  { path: "/my", name: "my", component: MyWork },
  { path: "/tickets", name: "tickets", component: TicketList },
  { path: "/teams", name: "teams", component: Teams },
  { path: "/settings", name: "settings", component: Settings },
];

const router = createRouter({
  // Served under /taskhub by Frappe's website_route_rules.
  history: createWebHistory("/taskhub"),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
