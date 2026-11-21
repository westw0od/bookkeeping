import { computed, ref, watch } from "vue";
import { currentUser, serverAddress } from "./api";

const entries = ref({});
export const draftError = ref("");
const keyFor = id => `bookkeeping-drafts-v1:${serverAddress.value || 'web'}:${id}`;
function read(id) {
  if (!id) return {};
  try {
    const data = JSON.parse(localStorage.getItem(keyFor(id)) || "{}");
    return data.version === 1 && data.entries && typeof data.entries === "object" && !Array.isArray(data.entries) ? data.entries : {};
  } catch { return {}; }
}
watch(() => currentUser.value?.id, id => { entries.value = read(id); draftError.value = ""; }, { immediate: true, flush: "sync" });
window.addEventListener("storage", event => {
  if (currentUser.value && event.key === keyFor(currentUser.value.id)) entries.value = read(currentUser.value.id);
});
export const savedDrafts = computed(() => Object.entries(entries.value).map(([slot, item]) => ({ slot, ...item })).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
export function readDraft(slot) { return entries.value[slot] || null; }
export function saveDraft(slot, data, { kind, title, path }, owner = currentUser.value?.id) {
  if (!owner) return false;
  const next = { ...read(owner), [slot]: { data, kind, title, path, updatedAt: new Date().toISOString() } };
  return persist(owner, next);
}
export function deleteDraft(slot, owner = currentUser.value?.id) {
  if (!owner) return false;
  const next = { ...read(owner) }; delete next[slot];
  return persist(owner, next);
}
function persist(owner, next) {
  try {
    if (Object.keys(next).length) localStorage.setItem(keyFor(owner), JSON.stringify({ version: 1, entries: next }));
    else localStorage.removeItem(keyFor(owner));
    if (owner === currentUser.value?.id) { entries.value = next; draftError.value = ""; }
    return true;
  } catch {
    draftError.value = "此设备暂时无法保存草稿，请保留页面，避免关闭或刷新。";
    return false;
  }
}
