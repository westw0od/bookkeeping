import { ref, shallowRef, watch } from "vue";
import { currentUser } from "./api";
export const editorRequest = shallowRef(null);
export const ledgerRevision = ref(0);
export function openEntryEditor(record = null, defaults = {}) {
  editorRequest.value = { record: record ? JSON.parse(JSON.stringify(record)) : null, defaults, key: record?.id || "new-entry" };
}
watch(() => currentUser.value?.id, () => { editorRequest.value = null; }, { flush: "sync" });
