const { test, expect } = require("@playwright/test");
const path = require("node:path");
const artifact = name => path.join(__dirname, "../../artifacts", name);

async function openOverview(page) {
  await page.addInitScript(() => {
    sessionStorage.setItem("bookkeeping-session-v2", JSON.stringify({ access_token: "isolated-design-preview", user: { id: "design-preview", username: "我的账本" }, expires_at: new Date(Date.now() + 3600000).toISOString() }));
  });
  const now = new Date();
  const rows = [
    { id: "preview-1", type: "expense", category: "饮食", amount: 25, note: "午餐", createdAt: now.toISOString() },
    { id: "preview-2", type: "expense", category: "饮食", amount: 18, note: "咖啡", createdAt: now.toISOString() },
    { id: "preview-3", type: "expense", category: "出行", amount: 4, note: "地铁", createdAt: now.toISOString() },
    { id: "preview-4", type: "income", category: "兼职", amount: 300, note: "兼职收入", createdAt: now.toISOString() },
  ];
  await page.route("**/api/features", route => route.fulfill({ json: { text_ai: true, image_ai: false } }));
  await page.route("**/api/ledger", route => route.fulfill({ json: rows }));
  await page.goto("/#/");
  await expect(page.getByRole("heading", { name: "总览", exact: true })).toBeVisible();
}

test("overview removes the hero and presents real totals, recent records and clear navigation", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1080 });
  await openOverview(page);
  await expect(page.getByText("今天的钱，今天讲清楚", { exact: true })).toHaveCount(0);
  await expect(page.locator(".hero")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /查看今日支出/ })).toContainText("¥47.00");
  await expect(page.locator(".balance-card")).toContainText("¥253.00");
  await expect(page.getByRole("heading", { name: "最近记录", exact: true })).toBeVisible();
  await expect(page.locator(".recent-records li")).toHaveCount(4);
  await expect(page.getByRole("textbox", { name: "描述这次收支" })).toBeVisible();
  const composer = await page.locator(".ai-panel").boundingBox();
  expect(composer.y).toBeLessThan(450);
  await page.screenshot({ path: artifact("overview-apple-desktop.png"), fullPage: true });
  await page.getByRole("navigation", { name: "账本导航" }).getByRole("link", { name: "账单", exact: true }).click();
  await expect(page.getByRole("heading", { name: "我的账单", exact: true })).toBeVisible();
  await page.screenshot({ path: artifact("ledger-apple-desktop.png"), fullPage: true });
});

test("navigation and content remain usable on narrow screens and with reduced motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await openOverview(page);
  await expect(page.getByRole("navigation", { name: "账本导航" })).toBeVisible();
  await expect(page.getByRole("button", { name: "AI 分析", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: artifact("overview-apple-phone.png"), fullPage: true });
  await page.setViewportSize({ width: 320, height: 700 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByRole("link", { name: "API Key 设置", exact: true })).toBeVisible();
});
