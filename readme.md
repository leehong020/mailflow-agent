# MailFlow Agent

MailFlow Agent 是一个基于 **FastAPI + Vue 3 + 大模型 Agent** 的智能邮件助理系统。当前版本已经完成开发文档中的项目初始化、Google OAuth 与 Gmail 接入、邮件分析 Agent、Agent Trace 展示、回复草稿审核与 Gmail Draft 创建流程，以及 Google Calendar 日程建议。

系统不是一个简单聊天窗口，而是一个可视化办公工作台：用户连接 Google 账号后，可以同步 Gmail 最近邮件，并由多个大模型 Agent 自动完成邮件摘要、优先级分类、是否需要回复判断、会议相关识别、待办事项提取、Google Calendar 空闲时间查询、回复草稿生成，并在用户确认后创建 Gmail 草稿或 Google Calendar 日程。

## 当前进度

- 第一阶段：FastAPI 后端、Vue 3 + TypeScript + Vite 前端、基础布局、路由、`/health`、Swagger 文档。
- 第二阶段：Google OAuth 登录回调、token 加密保存、Gmail 最近邮件读取、Settings 连接状态、Inbox 邮件列表。
- 第三阶段：`EmailSummarizerAgent`、`EmailTriageAgent`、`TaskExtractionAgent`，邮件分析工作流、邮件分类看板、邮件详情分析页。
- 第四阶段：Agent Trace 持久化和前端轨迹页，用于展示多 Agent 执行过程。
- 第五阶段：`ReplyDraftAgent`、Draft Review、Pending Actions，用户确认后创建 Gmail 草稿。
- 第六阶段：`CalendarSchedulerAgent`、Google Calendar 读取、空闲时间查询、Calendar Planner 页面、待确认 Calendar Event 创建。

## 核心流程

```text
用户连接 Google 账号
  -> 后端保存加密 token
  -> 用户点击“同步并分析邮件”
  -> GmailTool 读取 Gmail 最近邮件
  -> EmailRecord 保存原始邮件
  -> EmailSummarizerAgent 调用大模型生成摘要和关键点
  -> EmailTriageAgent 调用大模型输出分类、优先级、推荐操作
  -> TaskExtractionAgent 调用大模型提取待办事项
  -> EmailAnalysis / TaskItem 保存分析结果
  -> ReplyDraftAgent 按用户选择的语气和语言生成回复草稿
  -> 用户在 Draft Review 页面审核和修改
  -> Pending Actions 中确认
  -> GmailTool 创建 Gmail Draft
  -> CalendarSchedulerAgent 从会议邮件提取会议参数
  -> GoogleCalendarTool 查询已有日程和 busy 时间段
  -> Calendar Planner 展示推荐时间
  -> Pending Actions 中确认后创建 Calendar Event
  -> Vue Inbox Triage 看板和 Email Detail 页面展示结果
```

## OAuth JSON 放在哪里

Google Cloud Console 下载的 OAuth Client JSON 请放在项目根目录：

```text
secrets/google_oauth_client.json
```

该目录已加入 `.gitignore`，不要提交到 Git。

Google Cloud Console 中的 Authorized redirect URI 配置为：

```text
http://localhost:8000/gmail/auth/callback
```

## 后端环境变量

后端配置文件位于：

```text
backend/.env
```

关键配置：

```env
DATABASE_URL="sqlite:///./mailflow_agent.db"
BACKEND_BASE_URL="http://localhost:8000"
FRONTEND_BASE_URL="http://localhost:5173"
GOOGLE_REDIRECT_URI="http://localhost:8000/gmail/auth/callback"
GOOGLE_OAUTH_CLIENT_FILE="../secrets/google_oauth_client.json"
GOOGLE_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.compose,https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar.events"

LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_API_KEY="your-dashscope-api-key"
LLM_MODEL="qwen-plus"
LLM_TIMEOUT_SECONDS=30
```

当前调用的大模型由 `backend/.env` 的 `LLM_MODEL` 决定。你当前项目配置的是 DashScope OpenAI-compatible 接口，模型名为 `qwen-plus`。`backend/.env` 可以写真实 API Key，`.env.example` 只放占位符。

## 后端启动

项目后端使用根目录 `.venv`，不要依赖 conda 环境。

```powershell
cd C:\Users\Lee\Desktop\My_pro\mailflow-agent
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

打开：

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## 前端启动

```powershell
cd C:\Users\Lee\Desktop\My_pro\mailflow-agent\frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

## 使用流程

1. 启动后端和前端。
2. 将 OAuth JSON 放入 `secrets/google_oauth_client.json`。
3. 进入 `Settings`，点击“连接 Google 账号”。
4. 授权成功后进入 `Inbox`。
5. 点击“同步并分析邮件”。
6. 在 Inbox Triage 看板查看分类、优先级、摘要。
7. 点击任意邮件进入详情页，查看原文、摘要、关键点、分类理由、推荐操作和识别出的任务。
8. 对需要回复的邮件生成回复草稿，在 Draft Review 页面审核修改。
9. 在 Pending Actions 页面确认后，由系统创建 Gmail Draft。
10. 对会议相关邮件点击“查找会议时间”，进入 Calendar Planner。
11. 系统读取 Google Calendar 并推荐可用时间段。
12. 选择时间段后加入 Pending Actions，确认后创建 Google Calendar Event。

## API 概览

```text
GET  /health
GET  /api/v1/auth/google/login
GET  /gmail/auth/callback
GET  /api/v1/auth/google/status
POST /api/v1/auth/google/disconnect
GET  /api/v1/dashboard/summary
GET  /api/v1/emails
POST /api/v1/emails/analyze
GET  /api/v1/emails/{email_id}
GET  /api/v1/traces
GET  /api/v1/traces/{trace_id}
GET  /api/v1/calendar/events?range=today
GET  /api/v1/calendar/suggestions
POST /api/v1/calendar/suggest-slots
POST /api/v1/calendar/suggestions/{suggestion_id}/pending
GET  /api/v1/drafts/previews
POST /api/v1/drafts/previews
GET  /api/v1/drafts/pending
POST /api/v1/drafts/pending/{action_id}/confirm
POST /api/v1/drafts/pending/{action_id}/reject
```

## 后端模块说明

### `backend/app/main.py`

FastAPI 应用入口。负责创建 app、注册 CORS、启动时初始化数据库、提供 `/health`，并挂载 `/api/v1` 路由和 `/gmail/auth/callback` OAuth 回调。

### `backend/app/api/router.py`

API 总路由。把 auth、dashboard、emails 三组路由统一挂载到 `/api/v1`。

### `backend/app/api/routes_auth.py`

Google OAuth 接口。包含登录跳转、回调处理、state 校验、PKCE `code_verifier` 保存与恢复、Google 连接状态查询、断开连接。

### `backend/app/api/routes_email.py`

邮件接口。包含邮件列表筛选、触发 Gmail 同步与 Agent 分析、邮件详情查询。第三阶段的核心接口是 `POST /api/v1/emails/analyze`。

### `backend/app/api/routes_dashboard.py`

Dashboard 汇总接口。当前统计本地邮件数量、高优先级数量、需要回复数量、会议相关数量。

### `backend/app/core/config.py`

统一配置模块。读取 `.env` 中的数据库、Google OAuth、DashScope 大模型、前后端地址等配置。

### `backend/app/core/security.py`

安全工具。使用 Fernet 加密和解密 Google OAuth token，避免明文保存 access token / refresh token。

### `backend/app/core/llm.py`

统一大模型客户端。使用 OpenAI Python SDK 调用 DashScope OpenAI-compatible 接口，提供 `complete_json` 方法，要求模型返回 JSON 对象。

### `backend/app/agents/base.py`

大模型 Agent 基类。负责读取 txt 系统提示词、组装邮件上下文、调用 `LLMClient`、使用 Pydantic 校验模型 JSON 输出，并把校验错误压缩成适合前端展示的错误摘要。

### `backend/app/schemas/llm_outputs.py`

大模型输出契约。定义 `EmailSummaryLLMOutput`、`EmailTriageLLMOutput`、`TaskExtractionLLMOutput`、`ReplyDraftLLMOutput`，用于严格校验模型返回字段、枚举值和列表结构；能安全修复的内容会自动归一化，例如大小写、常见别名、过长列表截断。

### `backend/app/db/base.py`

SQLAlchemy 声明式模型基类。

### `backend/app/db/session.py`

数据库连接和 Session 管理。提供 `init_db` 自动建表和 `get_db` FastAPI 依赖。

### `backend/app/models/user.py`

用户模型。保存 Google 用户邮箱、名称、头像、Google sub、授权 scope 和加密 token。

### `backend/app/models/email.py`

第三阶段邮件数据模型。

- `EmailRecord`：保存 Gmail 同步下来的原始邮件。
- `EmailAnalysis`：保存 Agent 输出的摘要、分类、优先级、推荐操作。
- `TaskItem`：保存 Task Extraction Agent 提取出的待办事项。

### `backend/app/providers/google_provider.py`

Google OAuth SDK 封装。负责读取 OAuth JSON、生成授权 URL、换取 token，并处理本地开发 HTTP OAuth 设置。

### `backend/app/tools/gmail_tool.py`

Gmail API 工具层。读取 Inbox 最近邮件，解析 Gmail message payload，提取主题、发件人、收件人、时间、snippet 和正文；第五阶段还负责调用 Gmail API 创建 draft。

### `backend/app/services/auth_service.py`

认证业务服务。负责保存 Google 用户、加密 token、读取当前用户、断开本地 Google 连接。

### `backend/app/services/google_service.py`

Google 业务服务。负责恢复 Credentials、刷新过期 token、调用 GmailTool 读取邮件，并把 Google API 异常转换成业务错误。

### `backend/app/services/email_analysis_service.py`

第三阶段核心业务服务。负责同步 Gmail 邮件、保存 `EmailRecord`、运行邮件分析工作流、写入 `EmailAnalysis` 和 `TaskItem`，并提供列表和详情查询。

### `backend/app/agents/email_summarizer_agent.py`

Email Summarizer Agent。读取 `prompts/email_summarizer_agent.txt`，调用大模型生成邮件摘要和关键点。模型失败时只做最小内容预览兜底。

### `backend/app/agents/email_triage_agent.py`

Email Triage Agent。读取 `prompts/email_triage_agent.txt`，调用大模型判断邮件分类、优先级、是否需要回复、是否会议相关、是否包含任务和推荐操作。分类枚举严格对应开发文档，代码只做枚举约束和结果清洗。

### `backend/app/agents/task_extraction_agent.py`

Task Extraction Agent。读取 `prompts/task_extraction_agent.txt`，调用大模型从邮件中提取待办事项、描述、截止时间和优先级。模型失败时只在上游已判断存在任务的情况下创建人工核查任务。

### `backend/app/agents/reply_draft_agent.py`

Reply Draft Agent。读取 `prompts/reply_draft_agent.txt`，根据邮件上下文、已有分析结果、用户选择的语气和语言生成回复草稿，返回 Draft Review 页面供用户审核。

### `backend/app/agents/calendar_scheduler_agent.py`

Calendar Scheduler Agent。读取 `prompts/calendar_scheduler_agent.txt`，从会议邮件中提取会议标题、参会人、时长、候选时间窗口、地点和说明，为 Google Calendar 查询与事件创建提供结构化参数。

### `backend/app/prompts/*.txt`

大模型 Agent 的系统提示词文件。每个 Agent 一个 txt，便于独立维护提示词内容，不需要改 Python 常量。当前包括摘要、分类、任务提取、回复草稿、日程安排五类提示词。

### `backend/app/graphs/email_analysis_graph.py`

邮件分析工作流编排器。按开发文档顺序执行 `EmailSummarizerAgent -> EmailTriageAgent -> TaskExtractionAgent`。后续可以迁移为真正 LangGraph 节点编排。

### `backend/app/models/trace.py` / `backend/app/services/trace_service.py`

Agent Trace 数据模型和服务。保存每次工作流执行的任务类型、输入摘要、每个 Agent 节点的运行状态、输入输出预览和最终结果。

### `backend/app/models/draft.py` / `backend/app/services/draft_service.py`

回复草稿和待确认操作模块。保存 Agent 生成的草稿预览，支持用户编辑、加入 Pending Actions，并在确认后调用 Gmail API 创建草稿；第六阶段也复用 Pending Actions 确认 Calendar Event 创建。

### `backend/app/models/calendar.py` / `backend/app/services/calendar_service.py`

Google Calendar 日程建议模块。保存 `CalendarSuggestion`，负责读取日程、调用 Calendar Scheduler Agent、查询 busy 时间段、计算工作时间内的可用会议档期，并生成待确认 Calendar Event 操作。

### `backend/app/tools/google_calendar_tool.py`

Google Calendar API 工具层。封装 events.list、freebusy.query、events.insert，供日程读取、空闲时间查询和确认后创建事件使用。

### `backend/app/schemas/*.py`

Pydantic 响应模型。保证 API 输出结构稳定，前端可以依赖类型字段。

## 前端模块说明

### `frontend/src/main.ts`

Vue 入口。注册 Pinia、Vue Router、Element Plus 并挂载应用。

### `frontend/src/App.vue`

根组件。只挂载全局布局 `AppLayout`。

### `frontend/src/router/index.ts`

前端路由。包含 Dashboard、Inbox、Email Detail、Agent Trace、Draft Review、Pending Actions、Settings。

### `frontend/src/api/http.ts`

Axios 实例配置。统一设置后端 API 地址。

### `frontend/src/api/auth.ts`

Google 授权相关前端 API。查询连接状态、跳转登录、断开连接。

### `frontend/src/api/dashboard.ts`

Dashboard 汇总数据 API。

### `frontend/src/api/emails.ts`

邮件 API。包含邮件列表查询、触发分析、邮件详情查询。

### `frontend/src/api/traces.ts`

Agent Trace API。查询工作流执行记录和单次执行详情。

### `frontend/src/api/drafts.ts`

回复草稿和待确认操作 API。创建草稿预览、更新草稿、加入待确认、确认或拒绝 Gmail Draft 创建。

### `frontend/src/api/calendar.ts`

Calendar Planner API。读取 Google Calendar 事件、查询历史日程建议、从会议邮件生成可用时间段、创建待确认 Calendar Event 操作。

### `frontend/src/types/*.ts`

前端 TypeScript 类型定义，和后端 Pydantic schema 对齐。

### `frontend/src/components/layout/AppLayout.vue`

全局布局。组合侧边栏、顶部栏和页面内容，并刷新 Google 连接状态。

### `frontend/src/components/layout/AppSidebar.vue`

左侧导航栏。提供 Dashboard、Inbox、Settings 入口。

### `frontend/src/components/layout/AppHeader.vue`

顶部栏。显示当前页面标题和 Google 连接状态。

### `frontend/src/views/DashboardView.vue`

首页工作台。展示 Google 连接状态和邮件统计。

### `frontend/src/views/SettingsView.vue`

设置页。展示 Google 连接状态、用户信息、连接和断开按钮。

### `frontend/src/views/InboxView.vue`

Inbox Triage 看板。支持同步并分析 Gmail，按全部、高优先级、需要回复、会议相关、待办事项、通知类、可忽略进行筛选。

### `frontend/src/views/EmailDetailView.vue`

邮件详情分析页。左侧展示原始邮件，右侧展示 Agent 摘要、关键点、分类理由、推荐操作和任务列表。

### `frontend/src/views/CalendarPlannerView.vue`

日程建议页。使用 FullCalendar 展示本周 Google Calendar 日程，展示会议请求、推荐时间段、事件预览，并支持将选定时间段加入 Pending Actions。

### `frontend/src/views/AgentTraceView.vue`

Agent 执行轨迹页。展示多 Agent 工作流的运行步骤、状态、输入输出预览，便于课程演示和问题排查。

### `frontend/src/views/DraftReviewView.vue`

草稿审核页。展示 Reply Draft Agent 生成的收件人、主题、正文、生成理由，支持用户修改后加入待确认中心。

### `frontend/src/views/PendingActionsView.vue`

待确认操作中心。展示等待用户确认的高影响操作，目前支持确认后创建 Gmail Draft 或拒绝该操作。

### `frontend/src/styles.css`

全局样式。定义工作台布局、看板卡片、详情页双栏、标签和响应式布局。

## PostgreSQL / Redis

当前默认使用 SQLite，便于本地直接演示。若要按企业化环境切换 PostgreSQL / Redis：

```powershell
docker compose up -d
```

然后把 `backend/.env` 中的 `DATABASE_URL` 改为：

```text
postgresql+psycopg://mailflow:mailflow@localhost:5432/mailflow_agent
```

## 安全说明

- `secrets/` 不提交 Git。
- `backend/.env` 不提交 Git。
- Google token 加密后保存到数据库。
- DashScope API Key 只写入本地 `.env`。
- 当前阶段申请 Gmail 读取权限、草稿创建权限、Calendar 读取权限和 Calendar 事件创建权限，不申请发送、删除邮件权限。
- 如果之前已经授权过旧 scope，需要在 Settings 中断开并重新连接 Google 账号，才能拿到 Calendar 权限。

## 后续阶段

开发文档后续还包括：

- 第七阶段：Human-in-the-loop 操作中心。
- 第八阶段：Dashboard 与课程展示优化。
