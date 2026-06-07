const STORAGE_KEY = "smart-ledger-transactions";

export const expenseCategories = ["饮食", "购物", "娱乐", "出行", "旅游", "教育", "医疗", "人情", "水电", "其他"];
export const incomeCategories = ["工资", "补贴", "兼职", "人情", "幸运", "奖金", "投资", "其他"];

export function loadTransactions() {
  return loadLocalTransactions();
}

export async function loadTransactionsFromStore() {
  try {
    const response = await fetch("/api/ledger");
    if (!response.ok) throw new Error("database unavailable");
    const records = await response.json();
    saveLocalTransactions(records);
    return records;
  } catch {
    return loadLocalTransactions();
  }
}

function loadLocalTransactions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveTransactions(records) {
  saveLocalTransactions(records);
}

function saveLocalTransactions(records) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

export function createTransaction({ type, category, amount, note = "", createdAt }) {
  return {
    id: crypto.randomUUID(),
    type,
    category,
    amount: Number(amount),
    note,
    createdAt: createdAt || new Date().toISOString()
  };
}

export function addTransactions(records) {
  const current = loadLocalTransactions();
  const next = [...records, ...current];
  saveLocalTransactions(next);
  return next;
}

export async function addTransactionsToStore(records) {
  try {
    const response = await fetch("/api/ledger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(records)
    });
    if (!response.ok) throw new Error("database unavailable");
    const savedRecords = await response.json();
    const next = [...savedRecords, ...loadLocalTransactions()];
    saveLocalTransactions(dedupeById(next));
    return await loadTransactionsFromStore();
  } catch {
    return addTransactions(records);
  }
}

export function isSameDay(isoDate, dateText) {
  const date = new Date(isoDate);
  const target = parseDateText(dateText);
  return (
    date.getFullYear() === target.getFullYear() &&
    date.getMonth() === target.getMonth() &&
    date.getDate() === target.getDate()
  );
}

export function isToday(isoDate) {
  return isSameDay(isoDate, dateInputValue(new Date()));
}

export function recordsByDate(records, dateText, type = "") {
  return records.filter((record) => isSameDay(record.createdAt, dateText) && (!type || record.type === type));
}

export function todayRecords(records, type = "") {
  return recordsByDate(records, dateInputValue(new Date()), type);
}

export function dateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function datetimeLocalValue(date) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${dateInputValue(date)}T${hours}:${minutes}`;
}

export function totalAmount(records) {
  return roundMoney(records.reduce((sum, record) => sum + Number(record.amount || 0), 0));
}

export function groupByCategory(records) {
  return records.reduce((acc, record) => {
    acc[record.category] = roundMoney((acc[record.category] || 0) + Number(record.amount || 0));
    return acc;
  }, {});
}

export function formatDateTime(isoDate) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(isoDate));
}

export function roundMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}

function dedupeById(records) {
  const seen = new Set();
  return records.filter((record) => {
    if (seen.has(record.id)) return false;
    seen.add(record.id);
    return true;
  });
}

function parseDateText(dateText) {
  if (!dateText) return new Date();
  const [year, month, day] = dateText.split("-").map(Number);
  return new Date(year, month - 1, day);
}
