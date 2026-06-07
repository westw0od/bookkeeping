import { createTransaction, expenseCategories, incomeCategories, groupByCategory, totalAmount } from "./storage";

const expenseKeywords = [
  ["饮食", ["吃饭", "午餐", "晚餐", "早餐", "咖啡", "奶茶", "外卖", "餐", "饭"]],
  ["购物", ["买衣服", "衣服", "购物", "鞋", "包", "超市", "商品"]],
  ["娱乐", ["电影", "唱歌", "娱乐", "游戏", "演出", "会员"]],
  ["出行", ["打车", "地铁", "公交", "车费", "出租", "滴滴"]],
  ["旅游", ["旅游", "酒店", "机票", "景区", "门票"]],
  ["教育", ["课程", "书", "培训", "学习", "学费"]],
  ["医疗", ["医院", "药", "看病", "体检", "医疗"]],
  ["人情", ["红包", "礼金", "请客", "份子钱", "随礼", "人情"]],
  ["水电", ["水费", "电费", "燃气", "煤气", "物业", "宽带", "网费", "水电"]]
];

const incomeKeywords = [
  ["工资", ["工资", "薪资", "到账"]],
  ["补贴", ["补贴", "报销"]],
  ["兼职", ["兼职", "外快"]],
  ["人情", ["红包", "转账", "礼金", "人情"]],
  ["幸运", ["中奖", "抽奖", "幸运"]],
  ["奖金", ["奖金", "绩效", "奖励"]],
  ["投资", ["投资", "分红", "收益", "利息"]]
];

export async function analyzeTextExpense(text) {
  try {
    const response = await fetch("/api/agent/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (response.ok) {
      const data = await response.json();
      return normalizeAiResult(data);
    }
  } catch {
    // Fall back to local parsing when the backend model endpoint is not available.
  }
  return analyzeTextLocally(text);
}

export async function analyzeImageBill(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/agent/receipt", { method: "POST", body });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "图片分析失败");
  }
  const data = await response.json();
  const record = createTransaction({
    type: data.type,
    category: normalizeCategory(data.type, data.category),
    amount: data.amount,
    note: data.note || data.title || "图片账单",
    createdAt: dateToIso(data.occurred_at)
  });
  return buildReport([record], data.reason || "已根据图片内容生成记账记录。", data.confidence);
}

function analyzeTextLocally(text) {
  const segments = text
    .split(/[，。；;、\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  const records = [];
  for (const segment of segments) {
    const amount = extractAmount(segment);
    if (!amount) continue;
    const type = detectType(segment);
    const category = detectCategory(segment, type);
    records.push(createTransaction({ type, category, amount, note: segment }));
  }
  return buildReport(records, "本地规则已完成初步识别；接入大模型后可获得更准确的商家、类别和异常判断。");
}

function normalizeAiResult(data) {
  const records = (data.records || []).map((record) =>
    createTransaction({
      type: record.type,
      category: normalizeCategory(record.type, record.category),
      amount: record.amount,
      note: record.note || record.source || "",
      createdAt: record.createdAt || record.time || new Date().toISOString()
    })
  );
  return buildReport(records, data.analysis || data.summary || "AI 已生成结构化记账结果。", data.confidence);
}

function buildReport(records, advice, confidence = 0.75) {
  const incomeRecords = records.filter((record) => record.type === "income");
  const expenseRecords = records.filter((record) => record.type === "expense");
  const incomeTotal = totalAmount(incomeRecords);
  const expenseTotal = totalAmount(expenseRecords);
  const expenseByCategory = groupByCategory(expenseRecords);
  const incomeByCategory = groupByCategory(incomeRecords);
  const abnormal = expenseRecords.find((record) => record.amount >= Math.max(500, expenseTotal * 0.65));

  return {
    records,
    incomeTotal,
    expenseTotal,
    balance: incomeTotal - expenseTotal,
    incomeByCategory,
    expenseByCategory,
    ratios: Object.fromEntries(
      Object.entries(expenseByCategory).map(([key, value]) => [key, expenseTotal ? Math.round((value / expenseTotal) * 100) : 0])
    ),
    abnormal: abnormal ? `${abnormal.category} ${abnormal.amount} 元占比较高，建议确认是否为必要消费。` : "未发现明显异常消费。",
    advice,
    confidence
  };
}

function extractAmount(text) {
  const match = text.match(/(\d+(?:\.\d+)?)\s*(元|块|￥|¥)?/);
  return match ? Number(match[1]) : 0;
}

function detectType(text) {
  return /收入|到账|工资|兼职|奖金|补贴|红包|分红|收益|转账/.test(text) && !/花|买|支出|付款|消费/.test(text)
    ? "income"
    : "expense";
}

function detectCategory(text, type) {
  const groups = type === "income" ? incomeKeywords : expenseKeywords;
  for (const [category, words] of groups) {
    if (words.some((word) => text.includes(word))) return category;
  }
  return "其他";
}

function normalizeCategory(type, category) {
  const list = type === "income" ? incomeCategories : expenseCategories;
  return list.includes(category) ? category : "其他";
}

function dateToIso(dateText) {
  if (!dateText) return new Date().toISOString();
  const date = new Date(`${dateText}T12:00:00`);
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
}
