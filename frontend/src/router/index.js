import { createRouter, createWebHistory } from "vue-router";
import Home from "../pages/Home.vue";
import LedgerPage from "../pages/LedgerPage.vue";
import BalancePage from "../pages/BalancePage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: Home },
    {
      path: "/expense",
      name: "expense",
      component: LedgerPage,
      props: { type: "expense" }
    },
    {
      path: "/income",
      name: "income",
      component: LedgerPage,
      props: { type: "income" }
    },
    {
      path: "/balance",
      name: "balance",
      component: BalancePage
    }
  ]
});

export default router;
