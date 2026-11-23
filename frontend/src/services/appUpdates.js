import { reactive } from 'vue';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { serverAddress } from './api';

const updater = registerPlugin('AppUpdater');
export const updateState = reactive({
  supported: Capacitor.getPlatform() === 'android', current: null, release: null,
  checking: false, installing: false, visible: false, phase: 'idle', percent: 0, error: '', message: '',
});
let started = false;
let checkedAtLeastOnce = false;
let progressListener;
let releaseOrigin = '';

function origin() {
  const url = new URL(serverAddress.value);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('应用更新需要有效的 HTTPS 服务器地址');
  }
  return url.origin;
}

function validateRelease(value) {
  const current = updateState.current;
  if (value.schema_version !== 1 || value.application_id !== current.applicationId || !Number.isSafeInteger(value.version_code) || value.version_code <= 0 ||
      !Number.isSafeInteger(value.size_bytes) || value.size_bytes <= 0 || value.size_bytes > 100 * 1024 * 1024 ||
      !/^[a-f0-9]{64}$/.test(value.sha256) || !/^\d+\.\d+\.\d+(?:[.-][A-Za-z0-9]+)*$/.test(value.version_name) ||
      !Number.isInteger(value.min_sdk) || value.min_sdk < 23 || !Array.isArray(value.notes) ||
      !value.notes.length || value.notes.length > 20 || !value.notes.every(note => typeof note === 'string' && note.length <= 1000) ||
      value.download_path !== `/downloads/android/${value.version_code}/${value.sha256}.apk`) {
    throw new Error('服务器返回的更新信息不正确，请稍后重试');
  }
  return value;
}

export async function checkForUpdates(manual = true) {
  if (!updateState.supported || updateState.checking || updateState.phase === 'downloading') return;
  checkedAtLeastOnce = true;
  updateState.checking = true;
  updateState.error = ''; updateState.message = '';
  try {
    updateState.current = await updater.getInfo();
    const selected = origin();
    const response = await fetch(`${selected}/api/app/releases/latest`, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
    if (response.status === 404) throw new Error('服务器尚未发布应用更新');
    if (!response.ok) throw new Error('暂时无法获取更新，请稍后重试');
    const release = validateRelease(await response.json());
    if (selected !== origin()) return;
    if (release.version_code <= updateState.current.versionCode) {
      updateState.release = null;
      updateState.message = '已是最新版本';
      return;
    }
    updateState.release = release;
    releaseOrigin = selected;
    updateState.phase = 'available';
    updateState.percent = 0;
    updateState.visible = true;
  } catch (error) {
    if (manual) updateState.message = error.message?.includes('服务器') || error.message?.includes('更新')
      ? error.message : '无法检查更新，请检查网络后重试';
  } finally { updateState.checking = false; }
}

export function startUpdateChecks() {
  if (!updateState.supported || started) return;
  started = true;
  // Only check on launch; no timers or foreground network loop are required.
  setTimeout(() => { if (!checkedAtLeastOnce) checkForUpdates(false); }, 1500);
}

export function showAvailableUpdate() { if (updateState.release) updateState.visible = true; }
export function dismissUpdate() { if (updateState.phase !== 'downloading') updateState.visible = false; }

export async function downloadUpdate() {
  if (!updateState.release || updateState.phase === 'downloading') return;
  updateState.error = ''; updateState.phase = 'downloading'; updateState.percent = 0;
  try {
    if (origin() !== releaseOrigin) throw new Error('服务器地址已更换，请重新检查更新');
    progressListener = await updater.addListener('downloadProgress', value => {
      updateState.percent = Math.max(0, Math.min(100, Number(value.percent) || 0));
    });
    const release = updateState.release;
    await updater.download({ serverUrl: releaseOrigin, versionCode: release.version_code, sha256: release.sha256, sizeBytes: release.size_bytes });
    updateState.phase = 'downloaded';
    await installUpdate();
  } catch (error) {
    updateState.phase = 'available';
    updateState.error = error.message || '下载失败，请重试';
  } finally {
    try { await progressListener?.remove(); } catch { /* Progress listener cleanup must not hide the result. */ }
    progressListener = null;
  }
}

export async function cancelUpdateDownload() {
  try { await updater.cancelDownload(); }
  catch { updateState.error = '暂时无法取消，请稍后重试'; }
}

export async function installUpdate() {
  if (updateState.installing) return;
  updateState.installing = true;
  updateState.error = '';
  try {
    const result = await updater.install();
    updateState.phase = result.status === 'permission_required' ? 'permission' : 'installer';
  } catch (error) {
    updateState.error = error.message || '无法打开安装界面，请重试';
    updateState.phase = error.code === 'INVALID_PACKAGE' ? 'available' : 'downloaded';
  } finally { updateState.installing = false; }
}
