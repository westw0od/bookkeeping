import { createRouter, createWebHashHistory } from "vue-router";
import { currentUser } from "../services/api";
import LoginPage from "../pages/LoginPage.vue";
import AccountPage from "../pages/AccountPage.vue";
import KeysPage from "../pages/KeysPage.vue";
import Home from "../pages/Home.vue";
import LedgerPage from "../pages/LedgerPage.vue";
import BalancePage from "../pages/BalancePage.vue";
import PeoplePage from "../pages/PeoplePage.vue";
import TransactionsPage from "../pages/TransactionsPage.vue";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/login", component: LoginPage },
    { path: "/account", component: AccountPage },
    { path: "/keys", component: KeysPage },
    { path: "/", name: "home", component: Home },
    { path: "/people", component: PeoplePage },
    { path: "/ledger", component: TransactionsPage },
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

router.beforeEach((to) => {
  if (!currentUser.value && to.path !== "/login") return "/login";
  if (currentUser.value && to.path === "/login") return "/";
});
export default router;
