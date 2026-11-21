import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
import { initSession } from "./services/api";

initSession().then(() => createApp(App).use(router).mount("#app"));
