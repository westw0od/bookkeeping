const { test, expect } = require('@playwright/test');
const path = require('node:path');
const artifact = name => path.join(__dirname, '../../artifacts', name);
async function setup(page) {
  await page.addInitScript(() => sessionStorage.setItem('bookkeeping-session-v2', JSON.stringify({ access_token: 'category-preview', user: { id: 'category-preview', username: '分类预览' }, expires_at: new Date(Date.now() + 3600000).toISOString() })));
  const row = (id, category, amount, type = 'expense', day = '2026-11-21') => ({ id, category, amount, type, note: id, createdAt: day + 'T12:00:00+08:00' });
  const rows = [row('午餐', '饮食', 200), row('打车', '出行', 100), row('零头一', '饮食', 0.1), row('零头二', '饮食', 0.2), row('昨天吃饭', '饮食', 50, 'expense', '2026-11-20'), row('工资', '工资', 1000, 'income'), row('兼职', '兼职', 200, 'income'), row('上月购物', '购物', 999, 'expense', '2026-10-31')];
  await page.route('**/api/ledger', r => r.fulfill({ json: rows }));
  await page.route('**/api/features', r => r.fulfill({ json: { text_ai: true, image_ai: false } }));
  await page.goto('/#/ledger');
  await page.getByLabel('查看月份', { exact: true }).fill('2026-11');
}

test('month/day categories separate income and expense, sort major categories, and sum cents', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1080 });
  await setup(page);
  const expenses = page.getByRole('region', { name: '支出分类统计', exact: true });
  const income = page.getByRole('region', { name: '收入分类统计', exact: true });
  await expect(expenses.locator('.category-overview > strong')).toHaveText('¥350.30');
  await expect(income.locator('.category-overview > strong')).toHaveText('¥1,200.00');
  await expect(expenses.locator('.category-ranking li').first()).toContainText('饮食');
  await expect(expenses.getByRole('button', { name: '查看饮食支出明细' })).toContainText('71.5%');
  await expect(income.getByRole('button', { name: '查看工资收入明细' })).toContainText('83.3%');
  await expect(expenses.getByRole('button', { name: '查看购物支出明细' })).toHaveCount(0);
  await page.screenshot({ path: artifact('category-month-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: '按日', exact: true }).click();
  await page.getByLabel('查看日期', { exact: true }).fill('2026-11-21');
  await expect(expenses.locator('.category-overview > strong')).toHaveText('¥300.30');
  await expect(expenses.getByRole('button', { name: '查看饮食支出明细' })).toContainText('66.7%');
  await expect(page.getByRole('region', { name: '全部账单' }).locator('.transaction-list li')).toHaveCount(6);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: artifact('category-day-phone.png'), fullPage: true });
});

test('category drilldown retains overview totals, clears when period changes, and handles empty days', async ({ page }) => {
  await setup(page);
  const expense = page.getByRole('region', { name: '支出分类统计' });
  const ledger = page.getByRole('region', { name: '全部账单' });
  await expense.getByRole('button', { name: '查看饮食支出明细' }).click();
  await expect(ledger.locator('.transaction-list li')).toHaveCount(4);
  await expect(expense.locator('.category-overview > strong')).toHaveText('¥350.30');
  await expect(ledger).toContainText('¥250.30');
  await page.getByRole('button', { name: '按日', exact: true }).click();
  await page.getByLabel('查看日期').fill('2026-11-21');
  await expect(page.getByRole('button', { name: '显示全部分类' })).toHaveCount(0);
  await page.getByLabel('查看日期').fill('2026-11-01');
  await expect(expense).toContainText('这个范围还没有支出记录');
  await expect(ledger.locator('.transaction-list li')).toHaveCount(0);
  await page.getByRole('button', { name: '全部日期', exact: true }).click();
  await expect(expense.locator('.category-overview > strong')).toHaveText('¥1,349.30');
});

test('statistics page supports month/day classification and links to matching ledger details', async ({ page }) => {
  await setup(page);
  await page.getByRole('link', { name: '统计', exact: true }).click();
  await page.getByRole('button', { name: '按月', exact: true }).click();
  await page.getByLabel('查看月份').fill('2026-11');
  const expense = page.getByRole('region', { name: '支出分类统计' });
  await expect(expense.locator('.category-overview > strong')).toHaveText('¥350.30');
  await expense.getByRole('button', { name: '查看饮食支出明细' }).click();
  await expect(page.getByRole('heading', { name: '我的账单' })).toBeVisible();
  await expect(page.getByLabel('查看月份')).toHaveValue('2026-11');
  await expect(page.getByRole('region', { name: '全部账单' }).locator('.transaction-list li')).toHaveCount(4);
  await expect(page.getByRole('region', { name: '全部账单' })).toContainText('饮食支出');
});

test('recent records collapse independently, persist per user, and expand without losing records', async ({ page }) => {
  await setup(page);
  await page.getByRole('link', { name: '总览', exact: true }).click();
  const recent = page.getByRole('region', { name: '最近账单' });
  const toggle = recent.getByRole('button', { name: '最近记录', exact: true });
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(recent.locator('.recent-records')).toBeHidden();
  await page.reload();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await expect(recent.locator('.recent-records')).toBeVisible();
  await expect(recent.locator('.recent-records li')).toHaveCount(5);
});
