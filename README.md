# 记账 · Bookkeeping

当前版本：2.4.1。Android 支持启动检查更新、账号页手动检查、下载进度与取消、安装包校验及系统确认安装。最近记录支持折叠；「账单」与「统计」支持日/月分类、金额、笔数、占比、排名及分类明细。

当前部署：[网页版](https://39.107.13.249/#/) · [Android 安装包](https://39.107.13.249/downloads/bookkeeping.apk)。应用运行在独立云服务器，本机部署已清理，仓库保留源码和开发脚本。

Vue 3 + Vite + Capacitor Android，Python FastAPI 后端，MySQL 8.0 数据库。
网页版和 App 共用账号、账本和默认 AI Key。

## 已实现

- 注册、登录、退出、修改密码；7 天登录会话，退出/改密后服务端撤销。
- 每个用户独立账单、个人分类、图片和 AI Key；所有操作都在后端检查归属。
- 金额使用整数分存储，写入重试通过客户端 UUID 去重。
- Key 新增、删除、设置默认，默认选择持久保存；首次登录引导添加，也可直接手动记账。
- 支持山大 AI、DeepSeek、OpenAI、阿里云百炼兼容接口；每个 Key 可分别配置文字/图片模型。
- Key 使用 Fernet 加密，接口只返回掩码；密钥不放在 APK、网页代码或浏览器账本缓存中。
- AI 结果紧接输入框显示为待确认账单，可修正收支、金额、分类和备注；点击“确认记账”后才入账。网络失败保留草稿并明确提示。
- 用户使用自己的 AI Key，应用不另设每日提问次数限制；服务商自身额度或限流会正常反馈。

## 本机开发（按需重新配置）

本机开发脚本使用独立 MySQL 8.0 实例：127.0.0.1:33306，数据库 bookkeeping，数据库用户 bookkeeping。
数据目录约定为 `%LOCALAPPDATA%/Bookkeeping/mysql`，不会修改原来的 MySQL80 服务。本次清理已移除本机运行环境、旧数据和配置；重新开发前需按下文安装依赖、初始化独立数据库并配置 `.env`。
数据库密码和服务端加密密钥仅保存在被 Git 忽略的 `backend/.env`。

```powershell
./scripts/start-local.ps1 -OpenBrowser
```

网页版：http://127.0.0.1:8000 ，自行注册账号。AI 密钥在登录后的“API Key”页面添加。

## 在其他电脑或服务器部署

1. 安装 Python 3.10+、Node.js 20+、MySQL 8.0.16+。
2. 创建 utf8mb4 数据库及专用数据库用户，将 `backend/.env.example` 复制为 `backend/.env`。
3. 配置 `DATABASE_URL`，生成并填写 `KEY_ENCRYPTION_SECRET`。加密密钥必须长期保留并安全备份，不能每次启动都重新生成。
4. 安装依赖、初始化数据库和构建网页：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
npm.cmd run build --prefix frontend
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

后端同时提供网页和 `/api`。开发热更新可在 frontend 运行 `npm run dev`，访问 http://127.0.0.1:5173。
正式上线在反向代理配置 HTTPS，限制请求体大小，并备份 MySQL、上传目录和加密密钥。
多副本部署时图片目录需共享或迁移到带鉴权的对象存储。
目前是可运行的多用户初版，尚未接入邮件/短信找回密码、应用商店发行或公网域名。

## Android APK

提供的 `artifacts/bookkeeping-debug.apk` 是可直接安装的调试签名测试版（Android 6+，建议使用较新系统 WebView）。
不包含服务端、数据库密码或用户的 AI Key。

本机测试：手机开启 USB 调试并连接这台电脑，执行：

```powershell
adb reverse tcp:8000 tcp:8000
```

App 登录页展开“服务器设置”，使用 `http://127.0.0.1:8000`，即可与本地网页共用账号和账本。
手机断开 USB 后此通道失效；要脱离电脑使用，需要先把后端部署到 HTTPS 地址，再在 App 中保存该地址。
可在同一局域网测试时改为私有 IP（后端需监听该网卡且防火墙放行）；公网服务器只允许填写 HTTPS。
调试版允许本地 HTTP，release 配置禁止明文流量。正式发行需要自有签名证书并保存好证书。

重建 APK 需要 JDK 21、Android SDK 35 / Build Tools 35.0.0：

```powershell
./scripts/build-apk.ps1
# 如本机 Maven 下载需要已运行的代理：
./scripts/build-apk.ps1 -ProxyPort 7890
```

## 山大 AI

在 API Key 页面点击“添加 Key”，服务商默认选择“山大 AI”，粘贴自己的 Key 即可。
接口预设为 `https://xplt.sdu.edu.cn:4000/v1`，文字模型为 `SDU-AI/DeepSeek-V4-Flash`。
实际请求为 POST `/chat/completions`，使用 Bearer 认证、`temperature: 0.7`、`stream: false`，读取 `choices[0].message.content`。
接口通过 OpenAI 兼容 HTTP 格式调用，无需在手机或网页中安装 Python SDK。
此预设不启用图片识别；图片能力需另行确认并在“模型与备注”中配置图片模型。
用户密钥只通过登录后的表单保存；源码、示例和 APK 不包含真实密钥。

请求字段参考 [OpenAI Docs：Chat Completions](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)。

## API Key 的行为

- Key 按登录用户隔离；保存后完整内容不再返回前端，服务端仅在调用模型时解密。
- 新增第一个 Key 自动设为默认；后续新增可手动设为默认。
- 删除默认 Key 会自动选择剩余的第一个；删除最后一个会关闭 AI，手动记账仍可用。
- “删除”只从本系统删除，不会撤销服务商平台上的 Key。
- 保存 Key 不会自动产生付费调用；真正识别/分析时才请求服务商。模型名称、余额和图片能力需在服务商确认。
- DeepSeek 默认文字模型为 deepseek-chat，不预设图片模型；图片识别可选择有图片能力的服务商和模型。

## 验证

后端测试使用专用 MySQL 数据库 bookkeeping_test（需预先创建并授权），不会修改真实账本：

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests -q
cd frontend
npx playwright install chromium
npm run test:e2e
```

浏览器测试默认使用 8000 端口，生成 web_/failure_ 前缀的测试账号。可通过 WEB_TEST_URL 指向测试环境。
测试涵盖权限、金额精度、重复提交、Key 加密和默认持久化、服务商限流反馈、私有图片、手机页面和保存失败提示。
AI 的真实付费调用需用户添加有效 Key 后验证；自动测试使用假 Key 与模型响应，不消耗服务商额度。

## 旧版数据

旧 SQLite 文件与旧 localStorage 账本没有用户归属，不会自动导入到某个新用户。
旧 SQLite 文件和旧浏览器缓存均保持原样；新前端不再读取未归属缓存，不会在新账号下显示。
如需迁移历史账单，应先备份旧数据并明确选择接收账号。

## 网页界面设计

首页直接呈现收支概览、记账输入和最近记录，去掉营销标题与说明。全站使用系统字体、统一间距与控件规格，内容卡片保持实色，半透明效果仅用于导航层。

参考 Apple 官方 [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles)、[Typography](https://developer.apple.com/design/human-interface-guidelines/typography) 和 [Materials](https://developer.apple.com/design/human-interface-guidelines/materials)。这是网页界面设计上的参考，页面本身仍是 Vue Web 应用。

## 最近记录：删除与撤销

首页“最近记录”每条账单右侧的垃圾桶提供删除操作，确认后该记录不再计入收支、查询或 AI 分析。
删除后可点“撤销删除”；也可在同一卡片右上角切换“已删除”，恢复历史误删账单。不会永久清除账单内容，恢复后按原日期重新计入统计。

- `DELETE /api/ledger/{id}`：可恢复删除，重复请求不会重复操作。
- `GET /api/ledger/revoked`：仅返回本人已删除记录。
- `POST /api/ledger/{id}/restore`：恢复本人记录，重复请求不产生重复账单。

## 标准格式导入接口

首页“手动记账”下点击“导入历史账单”，下载 JSON 模板、选择整理后的文件，先预览再确认写入。
可参考 `examples/ledger-import.v1.json`，机器可读格式定义在 `backend/schemas/ledger-import.v1.schema.json`，交互式接口文档在 `/docs`。

- `GET /api/ledger/import/template`：下载模板内容，需登录。
- `POST /api/ledger/import?dry_run=true`：校验并预览，**不写入**；省略参数也默认为预览。
- `POST /api/ledger/import?dry_run=false`：明确提交导入；整批成功或整批回滚，不部分写入。

请求文档：`format` 固定为 `bookkeeping.v1`，`source` 是稳定的来源名称，`records` 包含最多 1,000 条记录。

| 记录字段 | 含义 |
| --- | --- |
| external_id | 同一来源中的稳定编号，重复导入使用它去重 |
| date | YYYY-MM-DD；历史记录未提供时刻，按北京时间当天中午保存 |
| type | income 为收入，expense 为支出 |
| amount | 大于零的金额，最多两位小数，推荐使用字符串 |
| category | 分类，例如饮食、人情、工资 |
| note | 可选备注 |
| counterparty | 可选往来人，例如张三 |
| event | 可选事由，例如婚礼、生日 |

响应包含 new_count、duplicate_count、removed_count、imported_count、income、expense 以及前 20 条预览。
相同来源和编号的相同记录会跳过；内容不同返回 409；已删除记录不会被重复导入自动恢复。
同一文件内重复编号、错误日期或金额会拒绝整批导入。模型密钥不是导入所需条件。

## 账本查询 Agent

“查询账本”已从前端关键词规则改为真正的模型工具调用循环：

1. 模型根据提问生成 query_ledger 过滤条件。
2. 服务端只读查询当前账号未删除的账单，返回明细与基于整数分计算的完整汇总。
3. 模型根据结果决定直接回答或补查，最多三轮查询，最后整理中文回答。

接口：`POST /api/agent/query`，请求体为 `{"question":"我和张三有没有人情往来？"}`。
支持往来人、收支、分类、日期和关键词；往来人同时检索结构化字段及旧账单备注。
页面展示执行步骤、最后一轮查询的统计与明细。默认只取最近 30 条明细，最多 50 条，汇总不受明细上限影响。
每次最多执行三轮 SQL 查询和四次模型请求，总等待上限 60 秒；没有应用侧每日问答次数限制。
模型不能指定用户 ID、运行 SQL 或调用写入工具。无匹配只表示账本暂无记录，不能推断现实中没有往来。
需要使用支持工具调用的模型；山大 `SDU-AI/DeepSeek-V4-Flash` 已实测工具调用及结果整理可用。

工具调用协议参考 [OpenAI Docs](https://developers.openai.com/api/docs/guides/function-calling)。

## 人情往来、编辑与本地草稿

导航包含总览、账单、人情和统计；原有收入、支出分类页仍可从首页进入。
人情页按「人情」分类的结构化 counterparty 汇总送出、收到，并按日期展示事由时间线。
姓名为空的历史记录单独归入「未填写往来人」，可编辑补充，不从备注中自动猜测姓名。
收送差额仅反映礼金往来，不表示借款或欠款。

点击最近记录的标题、账单列表或人情时间线中的编辑入口，可修改原账单的时间、收支、金额、分类、往来人、事由及备注。
`PUT /api/ledger/{id}` 接收 `{ "original": {原始字段}, "changes": {新字段} }`；两者均需 type、amount、category、createdAt，其余字段可选。
服务端核对原始快照、锁定当前用户记录后更新；真实并发冲突返回 409，原记录及前端编辑草稿均保留。
重复提交相同修改不会重复入账，已删除记录不能直接编辑；导入来源、外部编号和记录身份保持不变。

输入文本、AI 待确认结果、手动新增和已入账编辑的草稿自动保存在当前浏览器 localStorage，按账号和服务器地址隔离。
首页自动恢复 AI 草稿，其余草稿可从顶部「草稿」继续；确认成功后清除对应草稿，失败保留，只有明确提交才会修改账本。
草稿仅用于当前设备恢复，不跨设备同步；浏览器清理站点数据会清除草稿。不保存密码或 API Key。
如果本地存储不可用，页面会明确提示无法保存，不会声称草稿已保存。

## 日志与临时公网访问

独立云服务器的当前部署、证书续期、备份和运维命令见 [云服务器运行说明](docs/cloud-deployment.md)。下面的临时通道仅用于本机测试。

Android 2.4.1 支持应用内检查和下载安装更新，首次需手动覆盖安装。版本接口、校验及发布方式见 [应用内更新说明](docs/app-updates.md)。

`start-local.ps1` 通过 `backend/run_server.py` 启动，日志位于 `.local/logs/`。
应用、访问及穿透日志分别使用 app.log、access.log、tunnel.log，每类单文件 5 MiB，最多保留 4 个轮转文件，三类合计约 75 MiB。
启动时及日志写入时每天检查并清理超过 14 天的已轮转文件；不删除当前日志、数据库或账单附件。
访问日志去掉 URL 查询参数、不记录健康检查，应用不记录请求正文或认证头；数据库异常隐藏绑定参数。
旧的 `.local/web.log` 和 `.local/web-error.log` 不再作为输出目标，不会继续增长。

不使用学校服务器，也不需要开放本机或校园网入站端口。使用 Cloudflare 官方 cloudflared 在本机建立出站临时通道：

```powershell
./scripts/start-local.ps1
./scripts/start-tunnel.ps1
Get-Content .local/tunnel.json
# 停止公网入口：
./scripts/stop-tunnel.ps1
```

将经官方 SHA256 校验的 `cloudflared-windows-amd64.exe` 放到 `.local/cloudflared.exe` 后运行。
通道状态和地址位于被 Git 忽略的 `.local/tunnel.json`，地址格式为 `https://随机名称.trycloudflare.com`。
这是测试入口：电脑需保持开机、联网，创建新通道后地址会变化；HTTPS 证书由 Cloudflare 管理，不能指定 Let's Encrypt。
公网账本接口仍要求登录；仅安装包下载 `/downloads/bookkeeping.apk` 公开，服务端密钥和数据库不对外开放。
参考 [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)。

生成预填当前公网地址的 APK（仍可在登录页「服务器设置」更换）：

```powershell
$bookkeepingTunnel = Get-Content -Raw .local/tunnel.json | ConvertFrom-Json
./scripts/build-apk.ps1 -ServerUrl $bookkeepingTunnel.url
```

正式部署可在拥有稳定公网入口后配置 ACME 自动续期。Let's Encrypt 已支持短期 IP 地址证书，但仍需可验证的公网入口及自动续期，临时平台地址不由本项目控制证书签发者。
