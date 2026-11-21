import { ref } from "vue";
import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

export const currentUser = ref(null);
export const globalError = ref("");
export const serverAddress = ref("");
let accessToken = "";
const native = Capacitor.isNativePlatform();
const sessionKey = "bookkeeping-session-v2";

export async function initSession() {
  serverAddress.value = native
    ? ((await Preferences.get({ key: "bookkeeping-server" })).value || import.meta.env.VITE_DEFAULT_SERVER_URL || "http://127.0.0.1:8000")
    : "";
  try {
    const raw = native ? (await Preferences.get({ key: sessionKey })).value : sessionStorage.getItem(sessionKey);
    const saved = raw ? JSON.parse(raw) : null;
    if (saved && Date.parse(saved.expires_at) > Date.now()) {
      accessToken = saved.access_token;
      currentUser.value = saved.user;
    } else {
      await clearSession();
    }
  } catch {
    await clearSession();
  }
  // Legacy unowned localStorage is left untouched for manual migration.
  // The authenticated app never reads it or treats it as a user's ledger.
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let body = options.body;
  if (body && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`${serverAddress.value}${path}`, {
      ...options, body, headers, signal: options.signal || AbortSignal.timeout(70000)
    });
  } catch {
    throw new Error("无法连接服务器。请检查网络和服务器地址；本次操作未确认保存，请重试。");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !["/api/auth/login", "/api/auth/register"].includes(path)) {
      await clearSession();
      location.hash = "#/login";
    }
    const detail = typeof data.detail === "string" ? data.detail
      : response.status === 422 ? "输入格式不正确，请检查金额、小数位和必填项" : "操作失败，请重试";
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function authenticate(action, username, password) {
  const result = await api(`/api/auth/${action}`, { method: "POST", body: { username, password } });
  accessToken = result.access_token;
  currentUser.value = result.user;
  const raw = JSON.stringify(result);
  if (native) await Preferences.set({ key: sessionKey, value: raw });
  else sessionStorage.setItem(sessionKey, raw);
  globalError.value = "";
}

export async function clearSession() {
  accessToken = "";
  currentUser.value = null;
  globalError.value = "";
  sessionStorage.removeItem(sessionKey);
  if (native) await Preferences.remove({ key: sessionKey });
}

export async function logout() {
  // Keep the session if revocation fails, so a network error cannot imply logout succeeded.
  await api("/api/auth/logout", { method: "POST" });
  await clearSession();
}

export async function setServerAddress(value) {
  const url = new URL(value.trim());
  const local = /^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$/.test(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && local)) {
    throw new Error("上线服务器请使用 HTTPS；本机或局域网测试可使用 HTTP");
  }
  if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
    throw new Error("请仅填写服务器地址和端口，例如 https://ledger.example.com");
  }
  if (currentUser.value) await logout();
  else await clearSession();
  serverAddress.value = url.origin;
  await Preferences.set({ key: "bookkeeping-server", value: url.origin });
}

export async function loadLedgerSafely() {
  try {
    const data = await api("/api/ledger");
    globalError.value = "";
    return data;
  } catch (error) {
    globalError.value = error.message;
    return null;
  }
}
