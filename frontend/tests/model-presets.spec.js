const { test, expect } = require('@playwright/test');

test('school model groups, image capability and editing without resending the secret', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('bookkeeping-session-v2', JSON.stringify({
    access_token: 'fixture', user: { id: 'model-fixture', username: '模型预览' },
    expires_at: new Date(Date.now() + 3600000).toISOString(),
  })));
  let saved = { id: 'fixture-key', label: '学校 AI', provider: 'sdu', model: 'SDU-AI/DeepSeek-V4-Flash',
    vision_model: null, masked_key: '••••••••1234', is_default: true };
  const edits = [];
  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url());
    if (request.method() === 'PATCH') {
      edits.push(request.postDataJSON());
      saved = { ...saved, ...request.postDataJSON() };
      return route.fulfill({ json: saved });
    }
    return route.fulfill({ json: url.pathname === '/api/keys' ? [saved] : [] });
  });
  await page.goto('/#/keys');
  await page.getByRole('button', { name: '修改模型', exact: true }).click();
  const select = page.getByLabel('选择文字模型', { exact: true });
  await expect(select.locator('optgroup')).toHaveCount(3);
  await expect(select.locator('option')).toHaveCount(19); // local + 17 additions + custom
  await expect(page.getByLabel('API Key', { exact: true })).toHaveCount(0);
  await select.selectOption('Ali-dashscope/Qwen3.6-Plus');
  await page.getByText('模型与备注', { exact: false }).click();
  await expect(page.getByLabel('图片模型（可选）', { exact: true })).toHaveValue('Ali-dashscope/Qwen3.6-Plus');
  await select.selectOption('ByteDance-volcengine/DeepSeek-V4.1-Flash');
  await expect(page.getByLabel('图片模型（可选）', { exact: true })).toHaveValue('');
  await page.getByRole('button', { name: '保存修改', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(edits[0]).toEqual({ label: '学校 AI', model: 'ByteDance-volcengine/DeepSeek-V4.1-Flash', vision_model: null });
  await page.reload();
  await expect(page.locator('.active-details')).toContainText('ByteDance-volcengine/DeepSeek-V4.1-Flash');
  await page.getByRole('button', { name: '修改模型', exact: true }).click();
  await select.selectOption('custom');
  await expect(page.getByLabel('文字模型', { exact: true })).toBeVisible();
  await page.getByLabel('文字模型', { exact: true }).fill('SDU-AI/custom-example');
  await page.screenshot({ path: '../artifacts/models-phone.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await expect(page.locator('.active-details')).toContainText('ByteDance-volcengine/DeepSeek-V4.1-Flash');
});
