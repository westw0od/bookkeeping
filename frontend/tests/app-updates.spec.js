const { test, expect } = require('@playwright/test');
const path = require('node:path');

async function setup(page, options = {}) {
  await page.addInitScript(({ options }) => {
    const session = JSON.stringify({ access_token: 'update-fixture-token', user: { id: 'update-fixture', username: '更新预览' }, expires_at: new Date(Date.now() + 3600000).toISOString() });
    const preferences = { 'bookkeeping-server': 'https://updates.example.test', 'bookkeeping-session-v2': session };
    window.androidBridge = {};
    window.updateCalls = { downloads: [], installs: 0, cancelled: 0 };
    window.Capacitor = {
      PluginHeaders: [
        { name: 'Preferences', methods: ['get', 'set', 'remove'].map(name => ({ name, rtype: 'promise' })) },
        { name: 'AppUpdater', methods: [
          ...['getInfo', 'download', 'install', 'cancelDownload'].map(name => ({ name, rtype: 'promise' })),
          { name: 'addListener', rtype: 'callback' }, { name: 'removeListener', rtype: 'callback' },
        ] },
      ],
      nativePromise: async (plugin, method, data) => {
        if (plugin === 'Preferences') {
          if (method === 'get') return { value: preferences[data.key] || null };
          if (method === 'set') preferences[data.key] = data.value;
          if (method === 'remove') delete preferences[data.key];
          return {};
        }
        if (method === 'getInfo') return { versionCode: 7, versionName: '2.4.0', sdkInt: options.sdk || 35, applicationId: 'com.westw0od.bookkeeping' };
        if (method === 'download') {
          window.updateCalls.downloads.push(data);
          return new Promise((resolve, reject) => {
            window.finishUpdateDownload = () => resolve({ ready: true });
            window.failUpdateDownload = () => reject(new Error('更新包校验失败，请重新下载'));
            window.cancelUpdateDownload = () => reject(Object.assign(new Error('已取消下载'), { code: 'CANCELLED' }));
          });
        }
        if (method === 'cancelDownload') { window.updateCalls.cancelled++; window.cancelUpdateDownload(); return {}; }
        if (method === 'install') {
          window.updateCalls.installs++;
          return { status: options.permission && window.updateCalls.installs === 1 ? 'permission_required' : 'installer_opened' };
        }
        return {};
      },
      nativeCallback: (plugin, method, data, callback) => {
        if (method === 'addListener') window.emitUpdateProgress = callback;
        return 'fixture-listener';
      },
    };
  }, { options });
  await page.route('https://updates.example.test/**', route => {
    const url = new URL(route.request().url());
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-methods': '*', 'access-control-allow-headers': '*' };
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers });
    if (url.pathname === '/api/app/releases/latest') {
      if (options.offline) return route.fulfill({ status: 503, headers, json: { detail: 'unavailable' } });
      const hash = 'a'.repeat(64), code = options.current ? 7 : 8;
      const manifest = { schema_version: 1, application_id: options.wrongApp ? 'different.app' : 'com.westw0od.bookkeeping', version_code: code,
        version_name: options.current ? '2.4.0' : '2.4.1', sha256: hash, size_bytes: 4000000, min_sdk: 23,
        notes: ['优化记账体验', '增加应用内更新'], download_path: `/downloads/android/${code}/${hash}.apk` };
      if (options.externalPath) manifest.download_path = 'https://other.example/app.apk';
      return route.fulfill({ headers, json: manifest });
    }
    const data = url.pathname === '/api/features' ? { text_ai: true, image_ai: false } : [];
    return route.fulfill({ headers, json: data });
  });
  await page.goto('/#/account');
}

test('launch check shows notes, progress, Android permission and installer without losing session', async ({ page }) => {
  await setup(page, { permission: true });
  const dialog = page.getByRole('dialog', { name: '发现新版本' });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('2.4.1');
  await dialog.getByRole('button', { name: '立即更新', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.updateCalls.downloads.length)).toBe(1);
  await page.evaluate(() => window.emitUpdateProgress({ percent: 42 }));
  await expect(dialog.getByRole('progressbar')).toHaveAttribute('value', '42');
  await page.screenshot({ path: path.join(__dirname, '../../artifacts/app-update-progress.png'), fullPage: true });
  await page.evaluate(() => window.finishUpdateDownload());
  await expect(dialog).toContainText('请在系统设置中允许');
  await dialog.getByRole('button', { name: '继续安装', exact: true }).click();
  await expect(dialog).toContainText('已打开系统安装界面');
  expect(await page.evaluate(() => window.updateCalls.downloads[0].serverUrl)).toBe('https://updates.example.test');
  await dialog.getByRole('button', { name: '稍后再说' }).click();
  await expect(page.getByText('当前账号：')).toContainText('更新预览');
});

test('download cancellation and validation failure can retry without installing', async ({ page }) => {
  await setup(page);
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: '立即更新', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.updateCalls.downloads.length)).toBe(1);
  await dialog.getByRole('button', { name: '取消下载' }).click();
  await expect(dialog.getByRole('alert')).toHaveText('已取消下载');
  await dialog.getByRole('button', { name: '重新下载' }).click();
  await expect.poll(() => page.evaluate(() => window.updateCalls.downloads.length)).toBe(2);
  await page.evaluate(() => window.failUpdateDownload());
  await expect(dialog.getByRole('alert')).toContainText('校验失败');
  expect(await page.evaluate(() => window.updateCalls.installs)).toBe(0);
});

for (const [name, options, message] of [
  ['current version', { current: true }, '已是最新版本'],
  ['offline server', { offline: true }, '暂时无法获取更新'],
  ['wrong application', { wrongApp: true }, '更新信息不正确'],
  ['external download path', { externalPath: true }, '更新信息不正确'],
]) {
  test(`manual check handles ${name}`, async ({ page }) => {
    await setup(page, options);
    await page.getByRole('button', { name: '检查更新', exact: true }).click();
    await expect(page.getByRole('status')).toContainText(message);
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(await page.evaluate(() => window.updateCalls.downloads.length)).toBe(0);
  });
}

test('update requiring newer Android cannot be downloaded', async ({ page }) => {
  await setup(page, { sdk: 22 });
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('当前 Android 系统不支持此更新');
  await expect(dialog.getByRole('button', { name: '立即更新', exact: true })).toBeDisabled();
});
