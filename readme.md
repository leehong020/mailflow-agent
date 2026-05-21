# MailFlow Agent

MailFlow Agent 是一个基于 `FastAPI + LangGraph + Vue 3 + TypeScript + Element Plus + 大模型 Agent` 的智能邮件与日程办公工作台。

它不是一个简单的聊天机器人，而是一个“可视化工作台”式系统，目标是把邮件分析、回复草稿、主动写邮件、邮件管理、日程建议、待确认操作和 Agent 执行轨迹整合到一个统一的产品里。

当前仓库已经实现了开发文档中的前 12 个阶段，并正在继续补齐第 13 阶段的写作记忆系统。

---

## 一、项目目标

这个项目解决的是一个很典型的办公场景问题：

- 邮件数量多，难以及时筛选和分类；
- 需要回复的邮件容易遗漏；
- 会议相关邮件需要人工反复查日程；
- 主动写邮件和回复邮件需要反复修改草稿；
- 高风险操作不能自动执行，必须让用户确认；
- 希望把大模型能力放到“工作台”里，而不是只做一个聊天窗口。

因此 MailFlow Agent 设计成一个**任务驱动的邮件工作台**，核心能力包括：

1. 同步 Gmail 邮件；
2. 对邮件做摘要、分类、任务提取；
3. 生成回复草稿；
4. 主动写邮件；
5. 处理 Gmail 管理操作；
6. 提供 Google Calendar 会议建议；
7. 记录 Agent Trace；
8. 所有外部写操作都走 Pending Actions 二次确认；
9. 通过长期偏好和短期记忆提升连续写作体验。

---

## 二、当前开发阶段说明

### 已完成的阶段

- **第 1 阶段**  项目初始化、FastAPI、Vue、基础路由、健康检查。
- **第 2 阶段**  Google OAuth、Gmail 最近邮件读取、Settings 页面、Inbox 列表。
- **第 3 阶段**  邮件摘要、邮件分类、任务提取、邮件看板、邮件详情分析。
- **第 4 阶段**  Agent Trace 持久化、轨迹时间线、SSE 推送。
- **第 5 阶段**  回复草稿审核、Pending Actions、确认后创建 Gmail Draft。
- **第 6 阶段**  Calendar Scheduler、会议建议、Calendar Planner 页面。
- **第 7 阶段**  Safety Agent、统一操作中心、外部写操作的确认机制。
- **第 8 阶段**  Dashboard 统计增强、Inbox 检索和状态统计、Trace 筛选。
- **第 9 阶段**  Gmail 邮件管理：已读/未读、星标、归档、垃圾箱、标签、批量操作。
- **第 10 阶段** 邮件发送能力：新邮件、回复、转发、草稿修改、发送确认。
- **第 11 阶段** AI Reply Workspace、左侧编辑器 + 右侧 AI 对话修改。
- **第 12 阶段** Compose Mail 主动写邮件主界面、ComposeMailAgent、生成草稿、草稿修改。

### 正在推进的阶段

- **第 13 阶段** 写作体验与记忆系统优化：
  - 短期记忆 `compose_sessions` / `compose_messages`
  - 长期记忆 `user_preferences`
  - 自动保存
  - 草稿历史继续编辑
  - 设置页偏好管理
  - AI Reply Workspace 与 Compose Mail 共用会话记忆

### 后续阶段

- **第 14 阶段** Calendar 基础创建能力收尾。
- **第 15 阶段** 测试与展示完善。
- **第 16 阶段** 日程管理能力完善。
- **第 17 阶段** 安全、权限与可靠性完善。

---

## 三、系统架构总览

项目采用“前后端分离 + Agent 服务化 + 数据库持久化 + Human-in-the-loop”架构。

```text
Vue 工作台
  -> 调用 FastAPI 接口
  -> FastAPI 调用 Service 层
  -> Service 层调用 Agent / Tool / Trace / DB
  -> SQLite / Google API / 大模型服务
  -> 返回结构化数据给前端
```

### 主要设计原则

1. **前端是工作台，不是纯聊天窗口**
   - 通过列表、详情页、看板、时间线、确认中心组织操作。

2. **Agent 负责生成结构化结果**
   - 不是简单返回自然语言，而是输出可落库、可展示、可二次操作的数据。

3. **所有外部写操作必须确认**
   - 发送邮件、创建草稿、创建日程、修改日程等都要进入 Pending Actions。

4. **数据库是系统缓存层**
   - Gmail 邮件、分析结果、草稿、待确认操作、Trace、偏好都写入 SQLite。

5. **长文本和复杂结构要分层展示**
   - 例如邮件详情页左侧原文、右侧分析；Compose / Reply 页面左侧编辑器、右侧 AI 对话。

---

## 四、项目目录说明

下面按功能解释关键目录。

### `backend/`
后端 FastAPI 服务。

#### `backend/app/main.py`
后端入口，负责：
- 创建 FastAPI app；
- 注册 CORS；
- 启动时初始化数据库；
- 挂载 API 路由；
- 提供 `/health`。

#### `backend/app/api/`
HTTP 接口层，负责把前端请求转成 Service 调用。

- `router.py`：总路由聚合。
- `routes_auth.py`：Google OAuth 登录、回调、状态、断开。
- `routes_dashboard.py`：Dashboard 汇总。
- `routes_email.py`：邮件列表、详情、分析、同步等。
- `routes_drafts.py`：草稿预览、确认、拒绝。
- `routes_compose.py`：主动写邮件生成与修改。
- `routes_calendar.py`：日程建议与日程创建入口。
- `routes_actions.py`：统一待确认操作中心。
- `routes_traces.py`：Agent Trace 列表和详情。
- `routes_memory.py`：第 13 阶段会话记忆和长期偏好。

#### `backend/app/services/`
业务逻辑层，负责：
- 业务编排；
- 调用 Agent；
- 调用 Gmail / Calendar 工具；
- 事务控制；
- 数据写入数据库。

#### `backend/app/agents/`
Agent 层，每个 Agent 负责一种结构化任务，例如：
- 邮件摘要；
- 邮件分类；
- 任务提取；
- 回复草稿；
- 主动写邮件；
- 日程建议；
- 安全判断。

#### `backend/app/tools/`
外部工具封装层，例如：
- Gmail API；
- Google Calendar API。

#### `backend/app/models/`
SQLAlchemy ORM 模型层，负责 SQLite 持久化。

#### `backend/app/schemas/`
Pydantic API 数据结构定义。

#### `backend/app/prompts/`
Agent 系统提示词统一管理目录。

#### `backend/app/graphs/`
LangGraph 工作流编排。

#### `backend/app/core/`
通用配置、加密、LLM 客户端等基础能力。

---

### `frontend/`
Vue 3 前端工作台。

#### `frontend/src/main.ts`
前端入口。

#### `frontend/src/router/`
前端路由配置。

#### `frontend/src/api/`
前端 API 封装，统一调用后端接口。

#### `frontend/src/views/`
页面级视图。

#### `frontend/src/components/`
可复用组件，例如：
- 布局组件；
- 邮件编辑器；
- AI 助手面板；
- 邮件操作栏。

#### `frontend/src/types/`
前端类型定义，与后端 schema 对齐。

#### `frontend/src/styles.css`
全局样式。

---

## 五、主要功能说明

### 1. Dashboard
首页工作台，用于总览系统状态。

展示内容通常包括：
- Google 是否已连接；
- 今日邮件数量；
- 高优先级邮件数量；
- 需要回复数量；
- 今日会议数量；
- 待确认操作数量；
- 最近 Agent Trace。

入口页面：`frontend/src/views/DashboardView.vue`

---

### 2. Inbox Triage
邮件看板页，展示 Gmail 同步结果和结构化分析结果。

支持：
- 同步并分析邮件；
- 按分类筛选；
- 按优先级筛选；
- 按是否需要回复筛选；
- 点击进入详情页。

入口页面：`frontend/src/views/InboxView.vue`

后端核心接口：
- `GET /api/v1/emails`
- `POST /api/v1/emails/analyze`
- `GET /api/v1/emails/{email_id}`

---

### 3. 邮件详情分析
左侧展示原文，右侧展示 Agent 分析结果。

展示内容：
- 原始正文；
- 摘要；
- 关键点；
- 分类；
- 优先级；
- 分类理由；
- 推荐操作；
- 提取任务。

入口页面：`frontend/src/views/EmailDetailView.vue`

---

### 4. Draft Review
草稿审核页，用于查看历史草稿、继续编辑和提交待确认操作。

支持：
- 查看草稿列表；
- 打开历史草稿；
- 修改正文；
- 重新生成；
- 保存修改；
- 创建 Pending Action。

入口页面：`frontend/src/views/DraftReviewView.vue`

---

### 5. Pending Actions
待确认操作中心。

这里集中展示所有高风险外部操作，例如：
- 创建 Gmail Draft；
- 发送邮件；
- 创建 Calendar Event；
- 修改日程；
- 删除日程；
- 标签修改等。

用户必须在这里确认后，系统才会执行真正的外部写操作。

入口页面：`frontend/src/views/PendingActionsView.vue`

---

### 6. AI Reply Workspace
回复工作台。

设计目标是：
- 左侧编辑最终回复；
- 右侧通过对话不断修改；
- 保留原邮件上下文；
- 支持撤销修改；
- 支持保存草稿；
- 支持发送前确认。

入口页面：`frontend/src/views/AIReplyWorkspaceView.vue`

---

### 7. Compose Mail
主动写邮件工作台。

设计目标是：
- 用户不需要先选一封邮件；
- 可以直接描述写信目标；
- 由 ComposeMailAgent 生成主题和正文；
- 之后继续通过右侧对话修改；
- 保存到 Draft Review；
- 发送前进入 Pending Actions。

入口页面：`frontend/src/views/ComposeMailView.vue`

---

### 8. Calendar Planner
日程建议页。

支持：
- 查看日程；
- 展示会议建议；
- 推荐可用时间；
- 创建待确认日程事件。

入口页面：`frontend/src/views/CalendarPlannerView.vue`

---

### 9. Agent Trace
Agent 执行轨迹页。

支持：
- 查看每次工作流执行；
- 查看每一步 Agent 的输入输出摘要；
- 查看状态和执行结果；
- 支持 SSE 实时更新。

入口页面：`frontend/src/views/AgentTraceView.vue`

---

### 10. Settings
设置页。

支持：
- Google 连接和断开；
- 第 13 阶段长期偏好管理；
- 签名、常用称呼、风格偏好等。

入口页面：`frontend/src/views/SettingsView.vue`

---

## 六、数据库设计说明

当前默认数据库是 SQLite，文件名一般是：

```text
backend/mailflow_agent.db
```

### 主要表说明

#### `users`
存储 Google 用户和加密 token。

#### `email_records`
存储 Gmail 同步下来的原始邮件。

#### `email_analysis`
存储邮件摘要、分类、优先级、推荐操作。

#### `tasks`
存储从邮件里提取出来的待办事项。

#### `draft_previews`
存储回复草稿和主动写邮件草稿。

#### `pending_actions`
存储需要用户确认的高风险操作。

#### `agent_traces`
存储一次 Agent 工作流的总执行记录。

#### `agent_trace_events`
存储每个 Agent 节点的分步事件。

#### `compose_sessions`
第 13 阶段新增，存储短期写作会话。

#### `compose_messages`
第 13 阶段新增，存储会话中的用户/AI 消息。

#### `user_preferences`
第 13 阶段新增，存储长期偏好。

---

## 七、API 一览

下面列出常用接口，便于你调试前后端联调。

### 认证
- `GET /api/v1/auth/google/login`
- `GET /gmail/auth/callback`
- `GET /api/v1/auth/google/status`
- `POST /api/v1/auth/google/disconnect`

### Dashboard
- `GET /api/v1/dashboard/summary`

### 邮件
- `GET /api/v1/emails`
- `POST /api/v1/emails/analyze`
- `GET /api/v1/emails/{email_id}`
- `POST /api/v1/emails/{email_id}/reanalyze`

### 草稿
- `GET /api/v1/drafts/previews`
- `GET /api/v1/drafts/previews/{draft_id}`
- `POST /api/v1/drafts/emails/{email_id}/preview`
- `PATCH /api/v1/drafts/previews/{draft_id}`
- `POST /api/v1/drafts/previews/{draft_id}/revise`
- `POST /api/v1/drafts/previews/{draft_id}/pending`
- `POST /api/v1/drafts/previews/{draft_id}/send-action`
- `DELETE /api/v1/drafts/previews/{draft_id}`

### 主动写邮件
- `POST /api/v1/compose/generate`
- `POST /api/v1/compose/previews/{preview_id}/revise`

### 记忆系统
- `POST /api/v1/memory/sessions`
- `GET /api/v1/memory/sessions`
- `GET /api/v1/memory/sessions/{session_id}`
- `PATCH /api/v1/memory/sessions/{session_id}`
- `POST /api/v1/memory/sessions/{session_id}/messages`
- `GET /api/v1/memory/preferences`
- `POST /api/v1/memory/preferences`
- `DELETE /api/v1/memory/preferences/{preference_id}`

### 待确认操作
- `GET /api/v1/actions`
- `POST /api/v1/actions/{action_id}/confirm`
- `POST /api/v1/actions/{action_id}/reject`

### 轨迹
- `GET /api/v1/traces`
- `GET /api/v1/traces/{trace_id}`
- `GET /api/v1/traces/{trace_id}/stream`

### Calendar
- `GET /api/v1/calendar/events`
- `GET /api/v1/calendar/suggestions`
- `POST /api/v1/calendar/suggest-slots`
- `POST /api/v1/calendar/suggestions/{suggestion_id}/pending`

---

## 八、启动方式

### 后端启动

```powershell
cd C:\Users\Lee\Desktop\My_pro\mailflow-agent
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 前端启动

```powershell
cd C:\Users\Lee\Desktop\My_pro\mailflow-agent\frontend
npm install
npm run dev
```

### 构建前端

```powershell
npm run build
```

---

## 九、环境配置说明

### 后端 `.env`

关键配置示例：

```env
DATABASE_URL="sqlite:///./mailflow_agent.db"
BACKEND_BASE_URL="http://localhost:8000"
FRONTEND_BASE_URL="http://localhost:5173"
GOOGLE_REDIRECT_URI="http://localhost:8000/gmail/auth/callback"
GOOGLE_OAUTH_CLIENT_FILE="../secrets/google_oauth_client.json"
GOOGLE_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.compose,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar.events"
LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_API_KEY="your-dashscope-api-key"
LLM_MODEL="qwen-plus"
LLM_TIMEOUT_SECONDS=30
```

### OAuth JSON

Google OAuth Client JSON 放在：

```text
secrets/google_oauth_client.json
```

不要提交到 Git。

---

## 十、开发约定

### 1. Python 代码

- 后端业务逻辑放在 `services/`；
- HTTP 处理放在 `api/`；
- 大模型交互尽量统一到 Agent；
- 复杂的结构化输出使用 Pydantic schema 校验；
- 需要写入外部系统的操作必须经过 Safety / Pending Action。

### 2. 前端代码

- 页面级逻辑放在 `views/`；
- 可复用 UI 放在 `components/`；
- API 调用集中放在 `api/`；
- 类型定义统一放在 `types/`；
- 全局样式集中在 `styles.css`。

### 3. 数据流

- 前端只负责展示和触发；
- 后端负责业务编排和写库；
- Agent 负责结构化推理；
- Tool 负责对接 Gmail / Calendar；
- Trace 负责记录执行过程。

---

## 十一、调试建议

### 如果邮件分析失败

优先检查：
- Google 是否已连接；
- Gmail scope 是否正确；
- `LLM_API_KEY` 是否配置；
- `LLM_MODEL` 是否可用；
- 后端日志中的 API 异常。

### 如果草稿不显示

优先检查：
- 是否已生成 `draft_previews`；
- `DraftReviewView` 是否请求草稿列表；
- 后端 `GET /api/v1/drafts/previews` 是否返回数据；
- 当前用户是否仍然是同一个 Google 账号。

### 如果前端样式错乱

优先检查：
- `frontend/src/styles.css`；
- 是否有长文本未做 `overflow-wrap`；
- 卡片布局是否被超长内容撑坏；
- 是否有未处理的空状态。

---

## 十二、项目定位总结

MailFlow Agent 的目标不是做一个通用聊天产品，而是做一个**面向办公场景的可视化多 Agent 工作台**。

它的核心价值是：

- 邮件内容可分析；
- 回复草稿可审核；
- 主动写信可持续修改；
- 日程建议可视化；
- 所有高风险操作都由用户确认；
- 所有 Agent 执行过程都能追踪；
- 所有写作偏好都能记忆。

如果你后续要继续开发，建议按开发文档阶段顺序推进，这样最稳，也最容易展示。
