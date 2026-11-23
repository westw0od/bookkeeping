<template>
  <Teleport to="body">
    <div v-if="state.visible && state.release" class="modal-mask update-mask" @click.self="dismissUpdate" @keydown="keys">
      <section ref="dialog" class="modal-card update-dialog" role="dialog" aria-modal="true" aria-labelledby="update-title" tabindex="-1">
        <div class="update-icon"><Download :size="27" :stroke-width="1.6" /></div>
        <p class="eyebrow">App Update</p><h2 id="update-title">发现新版本</h2>
        <p class="update-version">{{ state.current?.versionName }} <ArrowRight :size="13" /> <strong>{{ state.release.version_name }}</strong><span>{{ (state.release.size_bytes / 1024 / 1024).toFixed(1) }} MB</span></p>
        <ul class="update-notes"><li v-for="note in state.release.notes" :key="note">{{ note }}</li></ul>
        <div v-if="state.phase === 'downloading'" class="update-progress" role="status">
          <div><span>正在下载并校验</span><strong>{{ state.percent }}%</strong></div>
          <progress :value="state.percent" max="100" aria-label="更新下载进度" />
        </div>
        <p v-if="state.phase === 'permission'" class="update-hint" role="status">请在系统设置中允许此应用安装更新，返回后点击“继续安装”。</p>
        <p v-else-if="state.phase === 'installer'" class="update-hint" role="status">已打开系统安装界面，请确认更新。若取消了安装，可以再次打开。</p>
        <p v-else class="update-hint">覆盖更新会保留登录信息和本地草稿，账单仍保存在服务器。</p>
        <p v-if="!compatible" class="error-text">当前 Android 系统不支持此更新。</p>
        <p v-if="state.error" class="error-text" role="alert">{{ state.error }}</p>
        <div class="modal-actions">
          <button v-if="state.phase === 'downloading'" class="secondary-btn" @click="cancelUpdateDownload">取消下载</button>
          <button v-else class="secondary-btn" @click="dismissUpdate">稍后再说</button>
          <button v-if="['downloaded', 'permission', 'installer'].includes(state.phase)" class="primary-btn" :disabled="state.installing" @click="installUpdate">{{ state.phase === 'installer' ? '重新打开安装器' : '继续安装' }}</button>
          <button v-else class="primary-btn" :disabled="state.phase === 'downloading' || !compatible" @click="downloadUpdate">{{ state.phase === 'downloading' ? '下载中…' : state.error ? '重新下载' : '立即更新' }}</button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { ArrowRight, Download } from '@lucide/vue';
import { updateState as state, dismissUpdate, downloadUpdate, cancelUpdateDownload, installUpdate } from '../services/appUpdates';
const dialog = ref(null);
const compatible = computed(() => !state.release || state.current?.sdkInt >= state.release.min_sdk);
let previousFocus;
watch(() => state.visible, async visible => {
  if (visible) { previousFocus = document.activeElement; await nextTick(); dialog.value?.focus(); }
  else previousFocus?.focus?.();
});
function keys(event) {
  if (event.key === 'Escape') dismissUpdate();
  if (event.key !== 'Tab') return;
  const buttons = [...dialog.value.querySelectorAll('button:not(:disabled)')];
  if (!buttons.length) return;
  if (event.shiftKey && (document.activeElement === buttons[0] || document.activeElement === dialog.value)) { event.preventDefault(); buttons.at(-1).focus(); }
  else if (!event.shiftKey && document.activeElement === buttons.at(-1)) { event.preventDefault(); buttons[0].focus(); }
}
onUnmounted(() => previousFocus?.focus?.());
</script>
