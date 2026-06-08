# 智能记账 Web App

当前实现：Vue 3 + Vite + Vue Router 前端，FastAPI 后端，SQLite 后端保留，前端账本统一保存到 `localStorage`。

## 页面

- `/` 首页：三个主模块、AI 文本分析、图片账单上传、今日财报结果
- `/expense` 支出模块：支出分类卡片、弹窗记账、今日支出列表、分类占比图
- `/income` 收入模块：收入分类卡片、弹窗记账、今日收入列表、分类占比图


## 启动后端

```powershell
cd manage\backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## 启动前端

```powershell
cd manage\frontend
npm.cmd install
npm.cmd run dev
```

打开 http://127.0.0.1:5173

## DeepSeek V4

在 `manage\backend` 创建 `.env`：

```env
DEEPSEEK_API_KEY=你的 DeepSeek 密钥
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
DEEPSEEK_THINKING=disabled
```

