from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "finance.db"
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")

TransactionType = Literal["income", "expense"]

DEFAULT_CATEGORIES = {
    "expense": ["饮食", "购物", "娱乐", "出行", "旅游", "教育", "医疗", "人情", "水电", "其他"],
    "income": ["工资", "补贴", "兼职", "人情", "幸运", "奖金", "投资", "其他"],
}


class Category(BaseModel):
    id: int
    name: str
    type: TransactionType


class TransactionIn(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0)
    category: str
    title: str = Field(min_length=1, max_length=80)
    occurred_at: date
    note: str | None = None
    source: str = "manual"
    image_path: str | None = None


class Transaction(TransactionIn):
    id: int
    created_at: datetime


class ImageSuggestion(BaseModel):
    type: TransactionType
    amount: float
    category: str
    title: str
    occurred_at: date
    note: str | None = None
    confidence: float = 0.5
    raw_text: str | None = None
    image_path: str
    agent_steps: list[str] = []
    reason: str | None = None


class AnalysisRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    question: str | None = None


class TextAgentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class LedgerTransactionIn(BaseModel):
    type: TransactionType
    category: str = Field(min_length=1, max_length=30)
    amount: float = Field(gt=0)
    note: str | None = None
    createdAt: datetime | None = None


class LedgerTransactionOut(BaseModel):
    id: str
    type: TransactionType
    category: str
    amount: float
    note: str | None = None
    createdAt: datetime


app = FastAPI(title="Smart Finance Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                UNIQUE(name, type)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                note TEXT,
                source TEXT NOT NULL DEFAULT 'manual',
                image_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for tx_type, names in DEFAULT_CATEGORIES.items():
            for name in names:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)",
                    (name, tx_type),
                )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/categories", response_model=list[Category])
def list_categories(type: TransactionType | None = None) -> list[dict[str, Any]]:
    sql = "SELECT id, name, type FROM categories"
    params: list[Any] = []
    if type:
        sql += " WHERE type = ?"
        params.append(type)
    sql += " ORDER BY type, id"
    with get_conn() as conn:
        return [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


@app.post("/api/categories", response_model=Category)
def create_category(category: CategoryCreate) -> dict[str, Any]:
    with get_conn() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO categories (name, type) VALUES (?, ?)",
                (category.name.strip(), category.type),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="分类已存在") from exc
        row = conn.execute(
            "SELECT id, name, type FROM categories WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return row_to_dict(row)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    type: TransactionType


@app.get("/api/transactions", response_model=list[Transaction])
def list_transactions(
    type: TransactionType | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if type:
        clauses.append("type = ?")
        params.append(type)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if start_date:
        clauses.append("occurred_at >= ?")
        params.append(start_date.isoformat())
    if end_date:
        clauses.append("occurred_at <= ?")
        params.append(end_date.isoformat())

    sql = "SELECT * FROM transactions"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY occurred_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        return [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


@app.post("/api/transactions", response_model=Transaction)
def create_transaction(item: TransactionIn) -> dict[str, Any]:
    ensure_category(item.category, item.type)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions
            (type, amount, category, title, occurred_at, note, source, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.type,
                item.amount,
                item.category.strip(),
                item.title.strip(),
                item.occurred_at.isoformat(),
                item.note,
                item.source,
                item.image_path,
            ),
        )
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return row_to_dict(row)


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="账单不存在")
    return {"ok": True}


@app.post("/api/agent/receipt", response_model=ImageSuggestion)
async def receipt_agent(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    extension = Path(file.filename or "").suffix or mimetypes.guess_extension(file.content_type) or ".jpg"
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    suggestion = await ai_extract_transaction(destination, file.content_type)
    suggestion["image_path"] = f"/uploads/{filename}"
    return suggestion


@app.post("/api/transactions/from-image", response_model=ImageSuggestion)
async def transaction_from_image(file: UploadFile = File(...)) -> dict[str, Any]:
    return await receipt_agent(file)


@app.post("/api/agent/text")
async def text_agent(payload: TextAgentRequest) -> dict[str, Any]:
    if not get_api_key():
        raise HTTPException(status_code=503, detail="未配置大模型密钥")

    prompt = f"""
你是一个记账 Agent。请从用户自然语言中提取今天的收入和支出，自动判断类型、分类、金额和备注。
只返回 JSON，不要 Markdown。格式：
{{
  "records": [
    {{"type": "income 或 expense", "category": "分类", "amount": 数字, "note": "备注", "time": "ISO时间，可省略"}}
  ],
  "analysis": "今日收支建议",
  "confidence": 0到1
}}
支出分类只能从 {DEFAULT_CATEGORIES['expense']} 中选，收入分类只能从 {DEFAULT_CATEGORIES['income']} 中选。
需要输出今日总收入、总支出、结余、异常消费判断和建议，写在 analysis 中。
用户输入：{payload.text}
"""
    result = await call_chat_completion(
        [
            {"role": "system", "content": "你是严谨的个人记账信息抽取助手，输出必须是可解析 JSON。"},
            {"role": "user", "content": prompt},
        ]
    )
    data = parse_json_object(result)
    return {
        "records": data.get("records", []),
        "analysis": data.get("analysis") or data.get("summary") or "AI 已完成分析。",
        "confidence": data.get("confidence", 0.75),
    }


@app.get("/api/ledger", response_model=list[LedgerTransactionOut])
def list_ledger() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                type,
                category,
                amount,
                note,
                created_at AS createdAt
            FROM transactions
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
        return [{**row_to_dict(row), "id": str(row["id"])} for row in rows]


@app.post("/api/ledger", response_model=list[LedgerTransactionOut])
def create_ledger_records(items: list[LedgerTransactionIn]) -> list[dict[str, Any]]:
    if not items:
        return []

    created_ids: list[int] = []
    with get_conn() as conn:
        for item in items:
            ensure_category(item.category, item.type)
            created_at = item.createdAt or datetime.now()
            cursor = conn.execute(
                """
                INSERT INTO transactions
                (type, amount, category, title, occurred_at, note, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.type,
                    item.amount,
                    item.category.strip(),
                    item.category.strip(),
                    created_at.date().isoformat(),
                    item.note,
                    "web",
                    created_at.isoformat(),
                ),
            )
            created_ids.append(cursor.lastrowid)

        placeholders = ",".join("?" for _ in created_ids)
        rows = conn.execute(
            f"""
            SELECT
                id,
                type,
                category,
                amount,
                note,
                created_at AS createdAt
            FROM transactions
            WHERE id IN ({placeholders})
            ORDER BY created_at DESC, id DESC
            """,
            created_ids,
        ).fetchall()
        return [{**row_to_dict(row), "id": str(row["id"])} for row in rows]


@app.post("/api/analysis")
async def analyze_bills(payload: AnalysisRequest) -> dict[str, Any]:
    records = list_transactions(start_date=payload.start_date, end_date=payload.end_date, limit=1000)
    totals = summarize(records)
    if not records:
        return {"summary": "当前筛选范围内还没有账单。", "totals": totals}

    ai_text = await ai_analyze(records, totals, payload.question)
    return {"summary": ai_text, "totals": totals}


def ensure_category(name: str, tx_type: TransactionType) -> None:
    clean = name.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="分类不能为空")
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)", (clean, tx_type))


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    income = sum(item["amount"] for item in records if item["type"] == "income")
    expense = sum(item["amount"] for item in records if item["type"] == "expense")
    by_category: dict[str, float] = {}
    for item in records:
        key = f"{'收入' if item['type'] == 'income' else '支出'}-{item['category']}"
        by_category[key] = round(by_category.get(key, 0) + item["amount"], 2)
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(income - expense, 2),
        "by_category": by_category,
    }


async def ai_extract_transaction(image_path: Path, content_type: str) -> dict[str, Any]:
    today = date.today().isoformat()
    fallback = {
        "type": "expense",
        "amount": 0.01,
        "category": "其他",
        "title": "图片账单",
        "occurred_at": today,
        "note": "未配置大模型密钥，请手动修改识别结果。",
        "confidence": 0.1,
        "raw_text": None,
        "agent_steps": ["接收图片", "等待大模型配置", "生成可编辑账单草稿"],
        "reason": "当前未配置大模型密钥，先生成一条可手动修改的默认草稿。",
    }
    if not get_api_key():
        return fallback

    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    prompt = f"""
你是一个个人记账 Agent。请从票据、付款截图、转账截图或账单图片中提取一条账单，并完成“识别内容 -> 判断收支 -> 选择分类 -> 生成可编辑草稿”的任务。
只返回 JSON，不要 Markdown。字段：
type: income 或 expense
amount: 数字，无法识别时为 0.01
category: 支出从 {DEFAULT_CATEGORIES['expense']} 中选一个，收入从 {DEFAULT_CATEGORIES['income']} 中选一个，可用“其他支出/其他收入”
title: 80字以内
occurred_at: YYYY-MM-DD，无法识别时用 {today}
note: 简短说明
confidence: 0 到 1
raw_text: 识别到的关键原文
agent_steps: 字符串数组，3 到 5 步，描述你如何识别并填账单
reason: 一句话说明为什么选这个类型和分类
"""
    try:
        result = await call_chat_completion(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{content_type};base64,{image_data}"},
                        },
                    ],
                }
            ]
        )
        parsed = parse_json_object(result)
        return normalize_suggestion(parsed, fallback)
    except Exception as exc:
        fallback["note"] = "图片已上传，但大模型图片识别失败，请手动补充金额和分类。"
        fallback["confidence"] = 0.05
        fallback["agent_steps"] = ["接收图片", "调用图片识别模型", "识别失败", "生成可编辑草稿"]
        fallback["reason"] = f"模型接口暂时无法完成图片识别：{brief_error(exc)}"
        return fallback


async def ai_analyze(records: list[dict[str, Any]], totals: dict[str, Any], question: str | None) -> str:
    if not get_api_key():
        top = sorted(totals["by_category"].items(), key=lambda item: item[1], reverse=True)[:5]
        top_text = "、".join(f"{name} {amount:.2f}元" for name, amount in top)
        return (
            f"本期收入 {totals['income']:.2f} 元，支出 {totals['expense']:.2f} 元，"
            f"结余 {totals['balance']:.2f} 元。主要分类：{top_text or '暂无'}。"
            "配置 OPENAI_API_KEY 后可获得更细的消费建议。"
        )

    brief_records = [
        {
            "类型": "收入" if item["type"] == "income" else "支出",
            "金额": item["amount"],
            "分类": item["category"],
            "标题": item["title"],
            "日期": item["occurred_at"],
            "备注": item.get("note"),
        }
        for item in records
    ]
    user_question = question or "请分析我的收支结构、异常账单、可优化的消费项，并给出简短建议。"
    content = json.dumps({"totals": totals, "records": brief_records, "question": user_question}, ensure_ascii=False)
    return await call_chat_completion(
        [
            {"role": "system", "content": "你是严谨但友好的个人财务分析助手，回答使用中文，结论要可执行。"},
            {"role": "user", "content": content},
        ]
    )


async def call_chat_completion(messages: list[dict[str, Any]]) -> str:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    if model.startswith("deepseek-v4"):
        payload["thinking"] = {"type": os.getenv("DEEPSEEK_THINKING", "disabled")}
        if payload["thinking"]["type"] == "enabled":
            payload["reasoning_effort"] = os.getenv("DEEPSEEK_REASONING_EFFORT", "medium")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def get_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")


def parse_json_object(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.strip("`")
        clean = clean.replace("json\n", "", 1).replace("JSON\n", "", 1)
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=502, detail="大模型未返回可解析的账单 JSON")
    return json.loads(clean[start : end + 1])


def normalize_suggestion(data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    tx_type = data.get("type") if data.get("type") in ("income", "expense") else fallback["type"]
    try:
        amount = float(data.get("amount", fallback["amount"]))
    except (TypeError, ValueError):
        amount = fallback["amount"]
    if amount <= 0:
        amount = fallback["amount"]

    default_category = "其他"
    category = str(data.get("category") or default_category).strip()
    title = str(data.get("title") or fallback["title"]).strip()[:80]
    occurred_at = str(data.get("occurred_at") or fallback["occurred_at"])[:10]
    try:
        date.fromisoformat(occurred_at)
    except ValueError:
        occurred_at = fallback["occurred_at"]

    return {
        "type": tx_type,
        "amount": round(amount, 2),
        "category": category,
        "title": title or fallback["title"],
        "occurred_at": occurred_at,
        "note": data.get("note") or fallback["note"],
        "confidence": min(1, max(0, float(data.get("confidence", fallback["confidence"])))),
        "raw_text": data.get("raw_text"),
        "agent_steps": data.get("agent_steps")
        if isinstance(data.get("agent_steps"), list)
        else ["识别图片内容", "判断收支类型", "匹配账单分类", "生成账单草稿"],
        "reason": data.get("reason") or "根据图片中的商户、金额和账单关键词自动生成。",
    }


def brief_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        text = exc.response.text[:180]
        return f"HTTP {exc.response.status_code} {text}"
    return str(exc)[:180] or exc.__class__.__name__
