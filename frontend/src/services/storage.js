import { api, loadLedgerSafely } from "./api";

export const expenseCategories = ["饮食", "购物", "娱乐", "出行", "旅游", "教育", "医疗", "人情", "水电", "其他"];
export const incomeCategories = ["工资", "补贴", "兼职", "人情", "幸运", "奖金", "投资", "其他"];

export async function loadTransactionsFromStore() {
  const result = await loadLedgerSafely();
  return result || [];
}

export function createTransaction({ type, category, amount, note = "", createdAt, counterparty = "", event = "" }) {
  return { id: crypto.randomUUID(), type, category, amount: Number(amount), note, counterparty, event,
    createdAt: createdAt || new Date().toISOString() };
}

export async function addTransactionsToStore(records) {
  await api("/api/ledger", { method: "POST", body: records });
  // Only a server-confirmed result is shown. A failed refresh never claims save failure.
  const fresh = await loadLedgerSafely();
  if (fresh === null) throw new Error("账单已保存，但列表刷新失败，请刷新页面；重试同一条记录不会重复入账。");
  return fresh;
}

export async function removeTransaction(id) {
  const result = await api(`/api/ledger/${encodeURIComponent(id)}`, { method: "DELETE" });
  return result.record;
}

export async function restoreTransaction(id) {
  const result = await api(`/api/ledger/${encodeURIComponent(id)}/restore`, { method: "POST" });
  return result.record;
}

export function loadRemovedTransactions() {
  return api("/api/ledger/revoked");
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

export function inPeriod(record, mode, day, month) {
  if (mode === 'all') return true;
  const localDate = dateInputValue(new Date(record.createdAt));
  return mode === 'day' ? localDate === day : localDate.slice(0, 7) === month;
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

function parseDateText(dateText) {
  if (!dateText) return new Date();
  const [year, month, day] = dateText.split("-").map(Number);
  return new Date(year, month - 1, day);
}
