const { test, expect } = require("@playwright/test");
const path = require("node:path");
const artifact = name => path.join(__dirname, "../../artifacts", name);
const importFile = { format: "bookkeeping.v1", source: "历史人情账本", records: [
  { external_id: "gift-1", date: "2026-10-01", type: "expense", amount: "500.00", category: "人情", note: "随礼", counterparty: "张三", event: "婚礼" },
  { external_id: "gift-2", date: "2026-11-01", type: "income", amount: "300.00", category: "人情", note: "收到礼金", counterparty: "张三", event: "生日" }
] };

async function setup(page, options = {}) {
  await page.addInitScript(() => sessionStorage.setItem("bookkeeping-session-v2", JSON.stringify({ access_token: "isolated-workflow-test", user: { id: "workflow-test", username: "预览账号" }, expires_at: new Date(Date.now() + 3600000).toISOString() })));
  const state = { active: [
    { id: "expense-1", type: "expense", amount: 21, category: "饮食", note: "午餐外卖", createdAt: new Date().toISOString(), revokedAt: null },
    { id: "income-1", type: "income", amount: 50, category: "兼职", note: "兼职", createdAt: new Date().toISOString(), revokedAt: null },
  ], removed: [], deletes: 0, restores: 0, previews: 0, imports: 0, questions: [] };
  await page.route("**/api/features", route => route.fulfill({ json: { text_ai: true, image_ai: false } }));
  await page.route("**/api/ledger**", async route => {
    const request = route.request(), url = new URL(request.url()), pathname = url.pathname;
    if (pathname === "/api/ledger/import/template") return route.fulfill({ json: importFile });
    if (pathname === "/api/ledger/import") {
      const commit = url.searchParams.get("dry_run") === "false";
      if (commit) {
        state.imports++;
        state.active.push(...importFile.records.map((row, index) => ({ ...row, id: `import-${index}`, amount: Number(row.amount), createdAt: row.date + "T12:00:00+08:00" })));
      } else state.previews++;
      return route.fulfill({ json: { format: "bookkeeping.v1", source: "历史人情账本", dry_run: !commit, total_count: 2, new_count: 2,
        duplicate_count: 0, removed_count: 0, imported_count: commit ? 2 : 0, income: 300, expense: 500, preview: importFile.records } });
    }
    if (pathname === "/api/ledger/revoked") return route.fulfill({ json: state.removed });
    if (pathname.endsWith("/restore")) {
      state.restores++;
      if (options.failRestore) return route.fulfill({ status: 503, json: { detail: "恢复失败，请重试" } });
      const id = pathname.split("/").at(-2), record = state.removed.find(row => row.id === id);
      const restored = { ...record, revokedAt: null };
      state.removed = state.removed.filter(row => row.id !== id); state.active.push(restored);
      return route.fulfill({ json: { ok: true, record: restored } });
    }
    if (request.method() === "DELETE") {
      state.deletes++;
      if (options.failDelete) return route.fulfill({ status: 503, json: { detail: "删除失败，请重试" } });
      const id = pathname.split("/").at(-1), record = state.active.find(row => row.id === id);
      const removed = { ...record, revokedAt: new Date().toISOString() };
      state.active = state.active.filter(row => row.id !== id); state.removed.push(removed);
      return route.fulfill({ json: { ok: true, record: removed } });
    }
    return route.fulfill({ json: state.active });
  });
  await page.route("**/api/agent/query", async route => {
    state.questions.push(route.request().postDataJSON());
    return route.fulfill({ json: { agent: true, summary: "当前账本有两笔与张三的人情往来：付出礼金500元，收到300元。", query_count: 2, matched_count: 2,
      income: 300, expense: 500, balance: -200, truncated: false, limit_reached: false,
      steps: [{ round: 1, label: "张三 · 人情 · 今年", status: "ok", matched_count: 0 }, { round: 2, label: "张三 · 人情", status: "ok", matched_count: 2 }],
      records: importFile.records.map((row, index) => ({ ...row, id: `query-${index}`, createdAt: row.date + "T12:00:00+08:00" })) } });
  });
  await page.goto("/#/");
  await expect(page.getByRole("heading", { name: "最近记录", exact: true })).toBeVisible();
  return state;
}

test("recent records support confirmed deletion, immediate undo, and recovery after reload", async ({ page }) => {
  const state = await setup(page);
  const recent = page.getByRole("region", { name: "最近账单", exact: true });
  await recent.getByRole("button", { name: "删除账单：午餐外卖", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "删除这笔账单？" })).toBeVisible();
  await page.getByRole("button", { name: "取消", exact: true }).click();
  expect(state.deletes).toBe(0);
  await recent.getByRole("button", { name: "删除账单：午餐外卖", exact: true }).click();
  await page.getByRole("dialog").screenshot({ path: artifact("recent-record-delete.png") });
  await page.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(recent.getByText("午餐外卖", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /查看今日支出/ })).toContainText("¥0.00");
  await recent.getByRole("button", { name: "撤销删除", exact: true }).click();
  await expect(recent.getByText("午餐外卖", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /查看今日支出/ })).toContainText("¥21.00");
  await recent.getByRole("button", { name: "删除账单：午餐外卖", exact: true }).click();
  await page.getByRole("button", { name: "确认删除", exact: true }).click();
  await page.reload();
  await recent.getByRole("button", { name: "已删除", exact: true }).click();
  await expect(recent.getByRole("button", { name: "恢复账单：午餐外卖", exact: true })).toBeVisible();
  await recent.getByRole("button", { name: "恢复账单：午餐外卖", exact: true }).click();
  await recent.getByRole("button", { name: "返回记录", exact: true }).click();
  await expect(recent.getByText("午餐外卖", { exact: true })).toBeVisible();
  expect(state.active).toHaveLength(2); expect(state.removed).toHaveLength(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("failed deletion keeps the original record and totals", async ({ page }) => {
  await setup(page, { failDelete: true });
  const recent = page.getByRole("region", { name: "最近账单", exact: true });
  await recent.getByRole("button", { name: "删除账单：午餐外卖", exact: true }).click();
  await page.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("删除失败");
  await expect(page.getByRole("link", { name: /查看今日支出/ })).toContainText("¥21.00");
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(recent.getByText("午餐外卖", { exact: true })).toBeVisible();
});

test("JSON import previews relationship records before committing and refreshes the ledger", async ({ page }) => {
  const state = await setup(page);
  await page.getByRole("button", { name: "导入历史账单", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "导入历史账单", exact: true });
  await dialog.getByLabel("选择导入文件", { exact: true }).setInputFiles({ name: "history.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(importFile)) });
  await expect(dialog.getByRole("button", { name: "确认导入 2 笔", exact: true })).toBeEnabled();
  await expect(dialog.getByText("张三 · 婚礼", { exact: true })).toBeVisible();
  expect(state.previews).toBe(1); expect(state.imports).toBe(0);
  await dialog.screenshot({ path: artifact("ledger-import-preview.png") });
  await dialog.getByRole("button", { name: "确认导入 2 笔", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("status")).toContainText("已导入 2 笔账单");
  expect(state.imports).toBe(1);
  expect(state.active).toHaveLength(4);
});

test("agent query calls the server and displays the query loop and authoritative totals", async ({ page }) => {
  const state = await setup(page);
  const query = page.getByRole("region", { name: "账本查询", exact: true });
  await query.getByRole("textbox", { name: "查询账本问题" }).fill("我和张三有没有人情往来？");
  await query.getByRole("button", { name: "查询账本", exact: true }).click();
  await expect(query.getByText("当前账本有两笔与张三的人情往来：付出礼金500元，收到300元。", { exact: true })).toBeVisible();
  expect(state.questions).toEqual([{ question: "我和张三有没有人情往来？" }]);
  await query.locator("summary").click();
  await expect(query.getByText("找到 2 笔记录", { exact: true })).toBeVisible();
  await expect(query.getByText("¥500.00", { exact: true }).first()).toBeVisible();
  await query.screenshot({ path: artifact("ledger-agent-result.png") });
});
