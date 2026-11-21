import { api } from "./api";
import { createTransaction, expenseCategories, incomeCategories, groupByCategory, totalAmount } from "./storage";

export async function analyzeTextExpense(text) {
  const data = await api("/api/agent/text", { method: "POST", body: { text } });
  return normalizeAiResult(data);
}

export async function analyzeImageBill(file) {
  const body = new FormData();
  body.append("file", file);
  const data = await api("/api/agent/receipt", { method: "POST", body });
  const record = createTransaction({
    type: data.type,
    category: normalizeCategory(data.type, data.category),
    amount: data.amount,
    note: data.note || data.title || "图片账单",
    counterparty: data.counterparty || "", event: data.event || "",
    createdAt: dateToIso(data.occurred_at)
  });
  return buildReport([record], data.reason || "已根据图片内容生成记账记录。", data.confidence);
}

function normalizeAiResult(data) {
  const records = (data.records || []).map((record) =>
    createTransaction({
      type: record.type,
      category: normalizeCategory(record.type, record.category),
      amount: record.amount,
      note: record.note || record.source || "",
      counterparty: record.counterparty || "", event: record.event || "",
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

function normalizeCategory(type, category) {
  const list = type === "income" ? incomeCategories : expenseCategories;
  return list.includes(category) ? category : "其他";
}

function dateToIso(dateText) {
  if (!dateText) return new Date().toISOString();
  const date = new Date(`${dateText}T12:00:00`);
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
}
