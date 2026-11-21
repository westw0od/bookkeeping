const { test, expect } = require("@playwright/test");
const path = require("node:path");
const artifact = name => path.join(__dirname, "../../artifacts", name);

async function previewSession(page, { failSave = false, empty = false } = {}) {
  const stored = [];
  const writes = [];
  let complete;
  const pending = new Promise(resolve => { complete = resolve; });
  await page.addInitScript(() => {
    sessionStorage.setItem("bookkeeping-session-v2", JSON.stringify({
      access_token: "isolated-ui-test-token", user: { id: "ui-preview", username: "预览账号" },
      expires_at: new Date(Date.now() + 3600000).toISOString()
    }));
  });
  await page.route("**/api/features", route => route.fulfill({ json: { text_ai: true, image_ai: false } }));
  await page.route("**/api/ledger", async route => {
    if (route.request().method() === "POST") {
      writes.push(route.request().postDataJSON());
      if (failSave) return route.fulfill({ status: 503, json: { detail: "服务器暂时不可用，请重试" } });
      stored.push(...route.request().postDataJSON());
      return route.fulfill({ json: stored });
    }
    return route.fulfill({ json: stored });
  });
  await page.route("**/api/agent/text", async route => {
    await pending;
    return route.fulfill({ json: { records: empty ? [] : [{ type: "expense", category: "饮食", amount: 25, note: "外卖", createdAt: new Date().toISOString() }],
      analysis: empty ? "未识别到明确的金额，请补充后再分析。" : "已从这次输入中识别出一笔外卖支出，请核对后记账。", confidence: 1 } });
  });
  await page.goto("/#/");
  await expect(page.getByRole("button", { name: "AI 分析", exact: true })).toBeVisible();
  return { writes, stored, complete };
}

test("AI draft sits under the input, can be corrected, and saves only on confirmation", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1050 });
  const state = await previewSession(page);
  const input = page.getByRole("textbox", { name: "描述这次收支" });
  const review = page.getByRole("region", { name: "AI 识别结果", exact: true });
  await input.fill("今天吃外卖花了25");
  await page.getByRole("button", { name: "AI 分析", exact: true }).click();
  await expect(review.getByText("正在整理这次输入…")).toBeVisible();
  expect(state.writes).toEqual([]);
  state.complete();
  await expect(review.getByRole("heading", { name: /待确认的账单/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "今日财报分析" })).toHaveCount(0);
  await expect(page.getByText(/今日剩余/)).toHaveCount(0);
  expect(await review.evaluate(node => node.closest(".ai-panel") !== null)).toBe(true);
  const inputBox = await input.boundingBox(), reviewBox = await review.boundingBox();
  const queryBox = await page.locator(".query-panel").boundingBox();
  expect(reviewBox.y).toBeGreaterThan(inputBox.y + inputBox.height);
  expect(queryBox.y).toBeGreaterThan(reviewBox.y + reviewBox.height);
  expect(state.writes).toEqual([]);
  await review.getByLabel("金额（元）", { exact: true }).fill("26.50");
  await review.getByLabel("备注", { exact: true }).fill("午餐外卖，含配送费");
  await expect(review.getByText("¥26.50", { exact: true })).toBeVisible();
  await page.locator(".ai-panel").screenshot({ path: artifact("web-ai-draft.png") });
  await review.getByRole("button", { name: "确认记账", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("1 笔记录已保存到账本");
  expect(state.writes).toHaveLength(1);
  expect(state.writes[0][0]).toMatchObject({ amount: 26.5, category: "饮食", note: "午餐外卖，含配送费" });
  await expect(input).toHaveValue("");
  await expect(review.getByRole("button", { name: "确认记账", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /查看今日支出/ })).toContainText("¥26.50");
});

test("failed confirmation retains the draft and cancellation never saves it", async ({ page }) => {
  const state = await previewSession(page, { failSave: true });
  await page.getByRole("textbox", { name: "描述这次收支" }).fill("今天吃外卖花了25");
  state.complete();
  await page.getByRole("button", { name: "AI 分析", exact: true }).click();
  const review = page.getByRole("region", { name: "AI 识别结果", exact: true });
  await expect(review.getByRole("button", { name: "确认记账", exact: true })).toBeVisible();
  await review.screenshot({ path: artifact("phone-ai-draft.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await review.getByRole("button", { name: "确认记账", exact: true }).click();
  await expect(review.getByRole("alert")).toContainText("服务器暂时不可用");
  await expect(review.getByLabel("金额（元）", { exact: true })).toHaveValue("25");
  expect(state.stored).toEqual([]);
  await review.getByRole("button", { name: "取消", exact: true }).click();
  await expect(review.getByRole("button", { name: "确认记账", exact: true })).toHaveCount(0);
  expect(state.writes).toHaveLength(1);
});

test("changing the original input invalidates the old draft and empty recognition has no confirm action", async ({ page }) => {
  const state = await previewSession(page);
  const input = page.getByRole("textbox", { name: "描述这次收支" });
  await input.fill("今天吃外卖花了25");
  state.complete();
  await page.getByRole("button", { name: "AI 分析", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认记账", exact: true })).toBeVisible();
  await input.fill("改成今天买书50元");
  await expect(page.getByRole("button", { name: "确认记账", exact: true })).toHaveCount(0);
  expect(state.writes).toEqual([]);
});

test("empty recognition explains missing information without allowing an empty save", async ({ page }) => {
  const state = await previewSession(page, { empty: true });
  await page.getByRole("textbox", { name: "描述这次收支" }).fill("今天很开心");
  state.complete();
  await page.getByRole("button", { name: "AI 分析", exact: true }).click();
  await expect(page.getByText("未识别到明确的金额，请补充后再分析。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "确认记账", exact: true })).toHaveCount(0);
  expect(state.writes).toEqual([]);
});
