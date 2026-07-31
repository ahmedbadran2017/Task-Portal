import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "./pages/Dashboard.vue";
import Board from "./pages/Board.vue";
import TicketList from "./pages/TicketList.vue";
import Settings from "./pages/Settings.vue";
import Teams from "./pages/Teams.vue";
import MyWork from "./pages/MyWork.vue";
import Requests from "./pages/Requests.vue";
import Command from "./pages/Command.vue";
import NotFound from "./pages/NotFound.vue";
import { isManager } from "./composables/useApi";

const routes = [
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", name: "dashboard", component: Dashboard },
  { path: "/board", name: "board", component: Board },
  { path: "/my", name: "my", component: MyWork },
  { path: "/requests", name: "requests", component: Requests },
  { path: "/tickets", name: "tickets", component: TicketList },
  // Management-only pages: the backend gates them too, but landing on a raw
  // permission error is a worse answer than sending people home.
  { path: "/teams", name: "teams", component: Teams, meta: { manager: true } },
  { path: "/command", name: "command", component: Command, meta: { manager: true } },
  { path: "/settings", name: "settings", component: Settings },
  { path: "/:pathMatch(.*)*", name: "not-found", component: NotFound },
];

const router = createRouter({
  // Served under /taskhub by Frappe's website_route_rules.
  history: createWebHistory("/taskhub"),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  if (to.meta?.manager && !isManager()) return { path: "/dashboard" };
  return true;
});

export default router;
