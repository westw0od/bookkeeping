"""Provider calls use only the authenticated user's decrypted default key."""
import base64
import json
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import HTTPException
from models import DEFAULT_CATEGORIES

async def call_chat_message(messages, config, vision=False, tools=None, tool_choice="auto"):
    model = config["vision_model"] if vision else config["model"]
    payload = {"model": model, "messages": messages,
               "temperature": config.get("temperature", 0.2), "stream": False}
    if tools:
        payload.update(tools=tools, tool_choice=tool_choice, parallel_tool_calls=False)
    # No redirects: credentials must only be sent to the selected fixed provider.
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5, pool=5, write=15), follow_redirects=False) as client:
        response = await client.post(config["base_url"].rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + config["api_key"]}, json=payload)
        response.raise_for_status()
        try:
            message = response.json()["choices"][0]["message"]
            if not isinstance(message, dict):
                raise ValueError()
            return message
        except (KeyError, IndexError, TypeError, ValueError):
            raise HTTPException(502, "模型返回格式不正确，请检查模型名称或重试")

async def call_chat_completion(messages, config, vision=False):
    message = await call_chat_message(messages, config, vision=vision)
    if not isinstance(message.get("content"), str):
        raise HTTPException(502, "模型未返回有效文本，请检查模型名称或重试")
    return message["content"]

def parse_json_object(value):
    if not isinstance(value, str):
        raise HTTPException(502, "模型未返回有效文本")
    start, end = value.find("{"), value.rfind("}")
    try:
        data = json.loads(value[start:end + 1])
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, TypeError):
        raise HTTPException(502, "模型未返回有效账单，请重试或手动记账")

async def ai_extract_transaction(image_path, content_type, config):
    prompt = ('从票据或付款截图提取一条账单。仅返回 JSON：'
        '{"type":"income或expense","amount":正数,"category":"分类","title":"标题",'
        '"occurred_at":"YYYY-MM-DD","note":"备注","confidence":0到1,"reason":"识别说明"}。'
        '金额无法辨认时返回 {"error":"无法识别金额"}，不要编造。'
        f'今天是 {date.today().isoformat()}。可用分类：{json.dumps(DEFAULT_CATEGORIES, ensure_ascii=False)}')
    image = base64.b64encode(image_path.read_bytes()).decode()
    result = await call_chat_completion([{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image}"}}
    ]}], config, vision=True)
    data = parse_json_object(result)
    try:
        amount = Decimal(str(data["amount"]))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99") or amount.as_tuple().exponent < -2:
            raise ValueError()
        kind = data["type"]
        if kind not in DEFAULT_CATEGORIES:
            raise ValueError()
        occurred = date.fromisoformat(data.get("occurred_at") or date.today().isoformat()).isoformat()
        confidence = max(0, min(1, float(data.get("confidence", .5))))
    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise HTTPException(422, "未能识别有效金额或日期，请换一张图片或手动记账")
    category = data.get("category")
    return {"type": kind, "amount": float(amount),
        "category": category if category in DEFAULT_CATEGORIES[kind] else "其他",
        "title": str(data.get("title") or "图片账单")[:80], "occurred_at": occurred,
        "note": str(data.get("note") or "")[:2000], "confidence": confidence,
        "reason": str(data.get("reason") or "请核对识别结果后保存")[:500]}
