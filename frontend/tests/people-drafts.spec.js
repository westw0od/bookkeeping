const { test, expect } = require('@playwright/test');
const path = require('node:path');
const artifact = name => path.join(__dirname, '../../artifacts', name);
async function setup(page) {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('bookkeeping-session-v2')) sessionStorage.setItem('bookkeeping-session-v2', JSON.stringify({ access_token: 'isolated-people-preview', user: { id: 'people-alice', username: '预览账号' }, expires_at: new Date(Date.now() + 3600000).toISOString() }));
  });
  const state = { rows: [
    { id: 'gift-a', type: 'expense', category: '人情', amount: 500, counterparty: '张三', event: '婚礼', note: '参加婚礼', createdAt: new Date().toISOString() },
    { id: 'gift-b', type: 'income', category: '人情', amount: 300, counterparty: '张三', event: '生日', note: '收到礼金', createdAt: '2026-10-01T12:00:00+08:00' },
    { id: 'gift-c', type: 'expense', category: '人情', amount: 100, counterparty: '李四', event: '乔迁', note: '', createdAt: '2026-09-01T12:00:00+08:00' },
    { id: 'gift-d', type: 'expense', category: '人情', amount: 50, counterparty: '', event: '', note: '旧账备注', createdAt: '2026-08-01T12:00:00+08:00' },
  ], writes: [], edits: [], failEdit: false, failSave: false };
  await page.route('**/api/features', r => r.fulfill({ json: { text_ai: true, image_ai: false } }));
  await page.route('**/api/ledger', r => {
    if (r.request().method() === 'POST') {
      state.writes.push(r.request().postDataJSON());
      if (state.failSave) return r.fulfill({ status: 503, json: { detail: '测试保存暂时失败' } });
      for (const row of r.request().postDataJSON()) if (!state.rows.some(saved => saved.id === row.id)) state.rows.push(row);
    }
    return r.fulfill({ json: state.rows });
  });
  await page.route('**/api/ledger/*', r => {
    if (r.request().method() !== 'PUT') return r.fulfill({ json: [] });
    const body = r.request().postDataJSON(); state.edits.push(body);
    if (state.failEdit) return r.fulfill({ status: 409, json: { detail: '账单已在其他页面修改，你的草稿已保留' } });
    const id = new URL(r.request().url()).pathname.split('/').at(-1);
    const row = { ...state.rows.find(row => row.id === id), ...body.changes, id, amount: Number(body.changes.amount) };
    state.rows = state.rows.map(existing => existing.id === id ? row : existing);
    return r.fulfill({ json: { ok: true, record: row } });
  });
  await page.route('**/api/agent/text', r => r.fulfill({ json: { records: [{ type: 'expense', category: '人情', amount: 200, note: '随礼', counterparty: '王五', event: '婚礼', createdAt: new Date().toISOString() }], analysis: '请核对这次人情支出。' } }));
  await page.goto('/#/');
  return state;
}

test('AI input and corrected draft survive navigation/reload without auto posting', async ({ page }) => {
  const state = await setup(page);
  await page.getByLabel('描述这次收支').fill('王五婚礼随礼200');
  await page.reload();
  await expect(page.getByLabel('描述这次收支')).toHaveValue('王五婚礼随礼200');
  await page.getByRole('button', { name: 'AI 分析', exact: true }).click();
  const review = page.getByRole('region', { name: 'AI 识别结果' });
  await expect(review.getByLabel('往来人', { exact: true })).toHaveValue('王五');
  await review.getByLabel('金额（元）', { exact: true }).fill('220.50');
  const beforeId = await page.evaluate(() => JSON.parse(localStorage.getItem('bookkeeping-drafts-v1:web:people-alice')).entries['home-ai'].data.report.records[0].id);
  await page.getByRole('link', { name: '人情', exact: true }).click();
  await page.getByRole('link', { name: '总览', exact: true }).click();
  await page.reload();
  await expect(review.getByLabel('金额（元）', { exact: true })).toHaveValue('220.5');
  expect(state.writes).toHaveLength(0);
  const afterId = await page.evaluate(() => JSON.parse(localStorage.getItem('bookkeeping-drafts-v1:web:people-alice')).entries['home-ai'].data.report.records[0].id);
  expect(afterId).toBe(beforeId);
  await review.getByRole('button', { name: '确认记账', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('1 笔记录已保存');
  expect(state.writes).toHaveLength(1);
  expect(state.writes[0][0]).toMatchObject({ id: beforeId, amount: 220.5, counterparty: '王五', event: '婚礼' });
  expect(await page.evaluate(() => localStorage.getItem('bookkeeping-drafts-v1:web:people-alice'))).toBeNull();
});

test('people directory totals, direction filter, and unassigned historical records', async ({ page }) => {
  await setup(page);
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.getByRole('link', { name: '人情', exact: true }).click();
  await page.locator('.people-list button').filter({ hasText: '张三' }).click();
  const detail = page.getByRole('region', { name: '往来详情', exact: true });
  await expect(detail.locator('.person-totals')).toContainText('¥500.00');
  await expect(detail.locator('.person-totals')).toContainText('-¥200.00');
  await expect(detail.locator('.gift-timeline li')).toHaveCount(2);
  await expect(detail).toContainText('不代表欠款');
  await page.screenshot({ path: artifact('people-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: artifact('people-phone.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel('筛选往来方向').selectOption('income');
  await expect(detail.locator('.gift-timeline li')).toHaveCount(1);
  await expect(detail.locator('.gift-timeline')).toContainText('生日');
  await page.getByLabel('搜索往来人').fill('未填写');
  await expect(detail.getByRole('heading', { name: '未填写往来人', exact: true })).toBeVisible();
  await expect(detail.locator('.gift-timeline')).toContainText('旧账备注');
});

test('entry edit draft survives reload and failure, updates existing row only on success', async ({ page }) => {
  const state = await setup(page);
  await page.getByRole('button', { name: '编辑账单：张三 · 婚礼', exact: true }).click();
  let editor = page.getByRole('dialog', { name: '编辑账单', exact: true });
  await editor.getByLabel('金额', { exact: true }).fill('666.66');
  await editor.getByLabel('事由', { exact: true }).fill('新婚祝福');
  await editor.getByRole('button', { name: '保存草稿并关闭', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: /草稿/ }).first().click();
  await page.getByRole('button', { name: /^继续草稿：编辑 · 张三/ }).click();
  editor = page.getByRole('dialog', { name: '编辑账单', exact: true });
  await expect(editor.getByLabel('金额', { exact: true })).toHaveValue('666.66');
  state.failEdit = true;
  await editor.getByRole('button', { name: '保存修改', exact: true }).click();
  await expect(editor.getByRole('alert')).toContainText('草稿已保留');
  await editor.screenshot({ path: artifact('edit-draft-phone.png') });
  expect(state.rows[0].amount).toBe(500);
  state.failEdit = false;
  await editor.getByRole('button', { name: '保存修改', exact: true }).click();
  await expect(editor).toHaveCount(0);
  await expect(page.getByRole('region', { name: '最近账单' })).toContainText('¥666.66');
  expect(state.rows).toHaveLength(4); expect(state.writes).toHaveLength(0);
  expect(await page.evaluate(() => localStorage.getItem('bookkeeping-drafts-v1:web:people-alice'))).toBeNull();
});

test('drafts are isolated by account and are restored when the original user returns', async ({ page }) => {
  await setup(page);
  await page.getByLabel('描述这次收支').fill('仅属于Alice的待确认信息');
  const switchUser = async id => {
    await page.evaluate(id => { const data = JSON.parse(sessionStorage.getItem('bookkeeping-session-v2')); data.user = { id, username: id }; sessionStorage.setItem('bookkeeping-session-v2', JSON.stringify(data)); }, id);
    await page.reload();
  };
  await switchUser('people-bob');
  await expect(page.getByLabel('描述这次收支')).toHaveValue('');
  await page.getByRole('button', { name: /草稿/ }).first().click();
  await expect(page.getByRole('dialog', { name: '我的草稿' })).toContainText('没有待处理的草稿');
  await page.getByRole('button', { name: '关闭草稿列表' }).click();
  await switchUser('people-alice');
  await expect(page.getByLabel('描述这次收支')).toHaveValue('仅属于Alice的待确认信息');
});

test('manual entry resumes from the draft menu after reload and saves exactly once', async ({ page }) => {
  const state = await setup(page);
  await page.getByRole('link', { name: /查看今日支出/ }).click();
  await page.getByRole('button', { name: /人情/ }).getByText('记一笔', { exact: true }).click();
  const editor = page.getByRole('dialog', { name: '记一笔', exact: true });
  await editor.getByLabel('金额', { exact: true }).fill('88.88');
  await editor.getByLabel('往来人', { exact: true }).fill('赵六');
  await editor.getByLabel('事由', { exact: true }).fill('生日');
  await page.reload();
  await page.getByRole('button', { name: /草稿/ }).first().click();
  await page.getByRole('button', { name: /^继续草稿：新增 · 赵六/ }).click();
  await expect(editor.getByLabel('金额', { exact: true })).toHaveValue('88.88');
  await expect(editor.getByLabel('事由', { exact: true })).toHaveValue('生日');
  state.failSave = true;
  await editor.getByRole('button', { name: '确认', exact: true }).click();
  await expect(editor.getByRole('alert')).toContainText('测试保存暂时失败');
  state.failSave = false;
  await editor.getByRole('button', { name: '确认', exact: true }).click();
  await expect(editor).toHaveCount(0);
  expect(state.writes).toHaveLength(2);
  expect(state.writes[0][0].id).toBe(state.writes[1][0].id);
  expect(state.rows).toHaveLength(5);
});

test('deleting the active AI draft clears the composer and never writes the ledger', async ({ page }) => {
  const state = await setup(page);
  await page.getByLabel('描述这次收支').fill('待删除的输入');
  await page.getByRole('button', { name: /^我的草稿/ }).click();
  await page.getByRole('button', { name: '删除草稿：待删除的输入', exact: true }).click();
  await page.getByRole('button', { name: '关闭草稿列表' }).click();
  await expect(page.getByLabel('描述这次收支')).toHaveValue('');
  expect(state.writes).toHaveLength(0);
});

test('unavailable browser storage gives an honest warning and preserves the current input', async ({ page }) => {
  await setup(page);
  await page.evaluate(() => {
    const set = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) { if (key.startsWith('bookkeeping-drafts-')) throw new DOMException('Quota exceeded', 'QuotaExceededError'); return set.call(this, key, value); };
  });
  await page.getByLabel('描述这次收支').fill('本地存储失败也不要丢掉输入');
  await expect(page.getByRole('alert')).toContainText('无法保存草稿');
  await expect(page.getByLabel('描述这次收支')).toHaveValue('本地存储失败也不要丢掉输入');
  await expect(page.getByText('草稿已自动保存在此设备', { exact: true })).toHaveCount(0);
});
