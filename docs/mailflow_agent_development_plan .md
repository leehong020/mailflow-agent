# MailFlow Agent 开发文档

## 1. 项目名称

### 推荐 GitHub 仓库名

**mailflow-agent**

### 中文项目名

**MailFlow Agent：基于 LangGraph 与 FastAPI 的多 Agent 邮件与日程助理系统**

### 命名理由

`mailflow-agent` 能够准确表达项目定位：

- `mail`：核心场景是邮件处理；
- `flow`：强调邮件、任务、日程、回复草稿之间的工作流；
- `agent`：强调系统由多个智能 Agent 协作完成任务。

该名称比 `email-chatbot` 或 `mail-assistant` 更适合课程展示，因为它突出的是一个完整的工作流系统，而不是单调的聊天机器人。

---

## 2. 项目定位

### 2.1 项目简介

**MailFlow Agent** 是一个基于 **FastAPI + LangGraph + Vue** 构建的多 Agent 邮件与日程助理系统。

系统可以读取 Gmail 邮件，自动完成邮件摘要、优先级分类、待办事项提取、会议请求识别、Google Calendar 空闲时间查询、回复草稿生成，并在用户确认后创建 Gmail 草稿或 Google Calendar 日程。

项目重点不是做一个简单的聊天窗口，而是做一个具有可视化操作界面、任务看板、邮件详情分析、日程建议、草稿审核、Agent 执行轨迹展示的智能办公系统。

### 2.2 项目目标

本项目目标是完成一个可演示、结构清晰、工程复杂度适中的课程项目，重点展示：

1. 使用 LangGraph 编排多 Agent 工作流；
2. 使用 FastAPI 提供后端 API；
3. 使用 Vue 构建非单一聊天模式的交互式前端；
4. 使用 Gmail API 读取邮件、创建草稿；
5. 使用 Google Calendar API 查询日程、创建会议事件；
6. 使用 Human-in-the-loop 机制保证高风险操作必须用户确认；
7. 展示 Agent 执行过程，而不是只展示最终回答；
8. 将邮件、任务、日程、草稿和待确认操作统一到一个工作台中。

---

## 3. 项目边界

为了保证项目可以稳定完成，第一版只支持：

```text
Gmail + Google Calendar
```

第一版暂不支持：

```text
Microsoft Outlook
QQ 邮箱
网易邮箱
IMAP / SMTP 多邮箱适配
复杂企业多用户权限系统
自动删除邮件
未经确认自动发送邮件
复杂长期记忆系统
```

项目重点是把 Gmail 与 Google Calendar 的核心闭环做好。

---

## 4. 参考项目与借鉴方向

| 参考项目 | 借鉴方向 |
|---|---|
| Inbox Zero | 邮件分类、邮件处理工作台、草稿生成、会议简报等产品功能设计 |
| agents-from-scratch | LangGraph 邮件 Agent、邮件 triage、Human-in-the-loop、评估方式 |
| ARCIS Backend | FastAPI + LangGraph 后端结构、多 Agent 编排方式、工具调用方式 |
| Executive AI Assistant | 行政助理式工作流、邮件摄取、人类审核流程 |
| Google Workspace MCP Server | Gmail / Calendar 工具封装思路 |
| Google Workspace Agent | Orchestrator + 多 Manager 的任务分发模式 |

本项目不直接复刻任何一个仓库，而是参考其设计思想，形成自己的系统：

```text
邮件读取 → Agent 分析 → 任务/会议识别 → 日程查询 → 草稿生成 → 用户确认 → 执行操作
```

---

## 5. 核心使用场景

### 场景 1：邮件智能工作台

用户进入系统首页后，可以看到：

- 今日邮件总数；
- 高优先级邮件数量；
- 需要回复的邮件数量；
- 识别出的会议请求数量；
- 待确认操作数量；
- 今日 Google Calendar 日程。

用户不需要一上来和 Agent 聊天，而是可以直接通过 Dashboard 查看当前办公状态。

---

### 场景 2：邮件分类看板

系统将 Gmail 邮件自动分类为：

```text
urgent_reply
normal_reply
calendar_related
task_required
newsletter
notification
ignore
```

前端以看板形式展示，例如：

```text
高优先级 | 需要回复 | 会议相关 | 待办事项 | 通知类 | 可忽略
```

用户可以点击任意邮件查看摘要、分类理由和建议操作。

---

### 场景 3：邮件详情分析

用户点击一封邮件后，前端展示：

- 原始邮件主题；
- 发件人；
- 接收时间；
- 邮件正文；
- AI 摘要；
- 关键点；
- 是否需要回复；
- 是否包含会议请求；
- 是否包含待办任务；
- 推荐操作。

这比单纯对话模式更适合课程展示，因为老师可以清楚看到 Agent 如何理解邮件。

---

### 场景 4：会议请求识别与日程建议

当邮件包含会议请求时，例如：

```text
Can we meet next Tuesday afternoon to discuss the project?
```

系统流程：

1. Calendar Scheduler Agent 识别会议请求；
2. 提取候选时间范围；
3. 查询 Google Calendar；
4. 找出可用时间段；
5. 生成可选会议时间；
6. Reply Draft Agent 生成回复草稿；
7. Safety Agent 创建待确认操作；
8. 用户在前端点击确认后，系统创建日程或创建草稿。

---

### 场景 5：回复草稿审核工作区

系统不会自动发送邮件，而是将回复内容放到草稿审核区。

用户可以：

- 查看 Agent 生成的回复草稿；
- 修改草稿内容；
- 选择语气：正式、简洁、友好、拒绝、确认；
- 点击“创建 Gmail 草稿”；
- 或者放弃该建议。

---

### 场景 6：待确认操作中心

所有高风险操作都会进入 Pending Actions 页面。

高风险操作包括：

```text
创建 Gmail 草稿
发送邮件
创建 Google Calendar 日程
修改日程
邀请参会人
```

第一版建议只做：

```text
创建 Gmail 草稿
创建 Google Calendar 日程
```

用户必须手动确认后，后端才会真正执行。

---

## 6. 功能规划

### 6.1 后端功能

#### Gmail 功能

- Google OAuth 登录；
- 获取 Gmail 最近邮件；
- 按时间范围读取邮件；
- 获取单封邮件详情；
- 解析邮件主题、发件人、时间、正文；
- 创建 Gmail 回复草稿；
- 保存邮件分析结果。

#### Calendar 功能

- 获取 Google Calendar 今日 / 本周日程；
- 查询指定时间段内的日程；
- 检测日程冲突；
- 根据会议请求推荐空闲时间；
- 创建 Calendar 事件；
- 保存会议建议结果。

#### Agent 功能

- 用户意图识别；
- 邮件摘要；
- 邮件优先级分类；
- 任务提取；
- 会议请求识别；
- 日程建议；
- 回复草稿生成；
- 安全审查；
- 待确认操作生成；
- Agent 执行轨迹记录。

#### 系统功能

- REST API；
- Server-Sent Events 或 WebSocket 流式推送 Agent 执行过程；
- 操作日志；
- 错误处理；
- 数据库持久化；
- Swagger API 文档。

---

### 6.2 前端功能

前端使用 **Vue 3 + TypeScript + Vite** 实现，不采用单一聊天窗口作为主界面，而是采用“智能办公工作台”模式。

核心页面包括：

1. Dashboard 首页；
2. Inbox Triage 邮件分类看板；
3. Email Detail 邮件详情分析页；
4. Calendar Planner 日程建议页；
5. Draft Review 草稿审核页；
6. Pending Actions 待确认操作页；
7. Agent Trace Agent 执行轨迹页；
8. Settings 设置页。

聊天入口可以保留，但只作为辅助功能，而不是系统主界面。

---

## 7. 总体系统架构

```text
Vue Frontend
  ├── Dashboard
  ├── Inbox Triage Board
  ├── Email Detail Analysis
  ├── Calendar Planner
  ├── Draft Review
  ├── Pending Actions
  └── Agent Trace Timeline
        ↓
FastAPI Backend
        ↓
LangGraph Orchestrator
        ↓
Multi-Agent Layer
  ├── Supervisor Agent
  ├── Intent Agent
  ├── Planner Agent
  ├── Email Triage Agent
  ├── Email Summarizer Agent
  ├── Task Extraction Agent
  ├── Calendar Scheduler Agent
  ├── Reply Draft Agent
  └── Safety Agent
        ↓
Tool Layer
  ├── Gmail Tool
  └── Google Calendar Tool
        ↓
Data Layer
  ├── PostgreSQL
  ├── Redis
  └── LangGraph Checkpoint Store
```

---

## 8. 技术栈

### 8.1 后端技术栈

| 模块 | 技术 |
|---|---|
| Web 后端 | FastAPI |
| Agent 编排 | LangGraph |
| LLM 接入 | OpenAI API / compatible LLM |
| 邮件接口 | Gmail API |
| 日程接口 | Google Calendar API |
| 数据库 | PostgreSQL |
| 缓存 / 任务状态 | Redis |
| ORM | SQLAlchemy / SQLModel |
| 数据校验 | Pydantic |
| 鉴权 | Google OAuth 2.0 |
| 日志 | loguru / structlog |
| API 文档 | Swagger / OpenAPI |

### 8.2 前端技术栈

| 模块 | 技术 |
|---|---|
| 前端框架 | Vue 3 |
| 构建工具 | Vite |
| 语言 | TypeScript |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| UI 组件库 | Element Plus / Naive UI |
| HTTP 请求 | Axios |
| 流式通信 | Server-Sent Events / WebSocket |
| 日历展示 | FullCalendar |
| 图标 | lucide-vue-next / Iconify |
| Markdown 渲染 | markdown-it |

推荐前端组合：

```text
Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus + FullCalendar
```

---

## 9. 多 Agent 设计

### 9.1 Supervisor Agent

职责：

- 接收用户请求或系统任务；
- 判断任务应该交给哪个 Agent；
- 管理 Agent 执行顺序；
- 汇总多个 Agent 的结果；
- 决定是否需要用户确认。

---

### 9.2 Intent Agent

职责：

- 判断用户意图；
- 区分邮件分析、草稿生成、日程安排、任务提取等请求；
- 将自然语言请求转化为结构化任务。

意图类型：

```text
summarize_emails
triage_inbox
draft_reply
schedule_meeting
extract_tasks
create_calendar_event
unknown
```

---

### 9.3 Planner Agent

职责：

- 将复杂任务拆解为多个执行步骤；
- 判断哪些步骤需要工具调用；
- 判断哪些步骤需要用户确认；
- 生成 LangGraph 执行路径。

---

### 9.4 Email Triage Agent

职责：

- 判断邮件优先级；
- 识别邮件类型；
- 判断是否需要回复；
- 判断是否涉及会议或待办事项；
- 输出分类理由。

输出示例：

```json
{
  "email_id": "email_001",
  "category": "urgent_reply",
  "priority": "high",
  "need_reply": true,
  "has_meeting_request": false,
  "has_task": true,
  "reason": "邮件来自重要联系人，并包含明确截止时间。"
}
```

---

### 9.5 Email Summarizer Agent

职责：

- 生成邮件摘要；
- 提取关键点；
- 提取人物、时间、地点、附件信息；
- 为前端详情页提供结构化分析结果。

---

### 9.6 Task Extraction Agent

职责：

- 从邮件中提取待办事项；
- 识别任务截止时间；
- 判断任务优先级；
- 将任务保存到数据库；
- 在前端任务面板中展示。

---

### 9.7 Calendar Scheduler Agent

职责：

- 识别会议请求；
- 提取会议主题、参会人、候选时间、会议时长；
- 查询 Google Calendar；
- 检查冲突；
- 推荐可用时间段；
- 生成创建日程所需参数。

---

### 9.8 Reply Draft Agent

职责：

- 根据邮件内容生成回复草稿；
- 根据会议建议生成确认邮件；
- 支持中文和英文；
- 支持正式、简洁、友好等语气；
- 将草稿返回到前端审核区。

---

### 9.9 Safety Agent

职责：

- 判断操作风险；
- 拦截外部可见操作；
- 为高风险操作创建 Pending Action；
- 等待用户确认后再执行。

默认策略：

```text
所有会影响外部世界的操作都不能自动执行。
```

包括：

```text
创建 Gmail 草稿
发送邮件
创建日程
修改日程
邀请参会人
```

第一版重点实现：

```text
创建 Gmail 草稿需要确认
创建 Google Calendar 日程需要确认
```

---

## 10. LangGraph 工作流设计

### 10.1 邮件分析工作流

```text
Fetch Gmail Emails
    ↓
Email Summarizer Agent
    ↓
Email Triage Agent
    ↓
Task Extraction Agent
    ↓
Calendar Scheduler Agent
    ↓
Save Analysis Result
    ↓
Return to Vue Dashboard
```

### 10.2 回复草稿工作流

```text
User selects email
    ↓
Email Detail Loaded
    ↓
Reply Draft Agent
    ↓
Safety Agent
    ↓
Create Pending Action
    ↓
Vue Draft Review Page
    ↓
User Confirm
    ↓
Gmail Tool creates draft
```

### 10.3 会议安排工作流

```text
Meeting-related Email
    ↓
Calendar Scheduler Agent
    ↓
Google Calendar Tool: Query Events
    ↓
Find Available Slots
    ↓
Reply Draft Agent
    ↓
Safety Agent
    ↓
Pending Action
    ↓
User Confirm
    ↓
Google Calendar Tool creates event
```

### 10.4 Agent 执行轨迹

每个 Agent 节点执行时都记录事件：

```json
{
  "trace_id": "trace_001",
  "step": 3,
  "agent": "EmailTriageAgent",
  "status": "running",
  "message": "正在判断邮件优先级",
  "timestamp": "2026-05-18T10:00:00"
}
```

前端使用时间线组件展示：

```text
读取 Gmail 邮件 → 摘要生成 → 优先级分类 → 提取任务 → 查询日程 → 生成草稿 → 等待确认
```

---

## 11. Vue 前端实现方案

### 11.1 前端设计原则

本项目的前端不采用单一聊天模式，而采用“任务驱动的办公工作台”。

核心原则：

1. Dashboard 展示全局状态；
2. 邮件以列表和看板形式展示；
3. Agent 分析结果结构化展示；
4. 高风险操作集中到待确认中心；
5. Agent 执行过程用时间线展示；
6. 聊天框只作为辅助入口，不作为唯一交互方式。

---

### 11.2 前端页面结构

```text
src/
├── main.ts
├── App.vue
├── router/
│   └── index.ts
├── stores/
│   ├── auth.ts
│   ├── email.ts
│   ├── calendar.ts
│   ├── action.ts
│   └── trace.ts
├── api/
│   ├── http.ts
│   ├── auth.ts
│   ├── emails.ts
│   ├── calendar.ts
│   ├── actions.ts
│   └── agent.ts
├── views/
│   ├── DashboardView.vue
│   ├── InboxTriageView.vue
│   ├── EmailDetailView.vue
│   ├── CalendarPlannerView.vue
│   ├── DraftReviewView.vue
│   ├── PendingActionsView.vue
│   ├── AgentTraceView.vue
│   └── SettingsView.vue
├── components/
│   ├── layout/
│   │   ├── AppSidebar.vue
│   │   ├── AppHeader.vue
│   │   └── AppLayout.vue
│   ├── email/
│   │   ├── EmailList.vue
│   │   ├── EmailCard.vue
│   │   ├── EmailCategoryBadge.vue
│   │   ├── EmailPriorityTag.vue
│   │   └── EmailAnalysisPanel.vue
│   ├── calendar/
│   │   ├── CalendarMiniView.vue
│   │   ├── SuggestedSlots.vue
│   │   └── EventCreatePreview.vue
│   ├── draft/
│   │   ├── DraftEditor.vue
│   │   └── ToneSelector.vue
│   ├── actions/
│   │   ├── PendingActionCard.vue
│   │   └── ConfirmActionDialog.vue
│   ├── agent/
│   │   ├── AgentTraceTimeline.vue
│   │   ├── AgentStepCard.vue
│   │   └── AgentStatusIndicator.vue
│   └── common/
│       ├── StatCard.vue
│       ├── EmptyState.vue
│       └── LoadingState.vue
└── types/
    ├── email.ts
    ├── calendar.ts
    ├── action.ts
    └── agent.ts
```

---

### 11.3 页面一：Dashboard 首页

Dashboard 是系统主入口，展示整体办公状态。

#### 页面模块

- 邮件统计卡片；
- 高优先级邮件列表；
- 需要回复邮件列表；
- 今日会议列表；
- 待确认操作列表；
- Agent 最近执行记录。

#### 示例布局

```text
┌──────────────────────────────────────────────┐
│ MailFlow Agent Dashboard                      │
├──────────────┬──────────────┬───────────────┤
│ 今日邮件 24  │ 高优先级 3  │ 待确认操作 2 │
├──────────────┴──────────────┴───────────────┤
│ 高优先级邮件                                 │
├──────────────────────────────────────────────┤
│ 今日会议                                     │
├──────────────────────────────────────────────┤
│ Agent 执行轨迹                               │
└──────────────────────────────────────────────┘
```

#### 对应 API

```http
GET /api/v1/dashboard/summary
GET /api/v1/emails?priority=high
GET /api/v1/calendar/events?range=today
GET /api/v1/actions?status=pending
```

---

### 11.4 页面二：Inbox Triage 邮件分类看板

#### 功能

- 展示 Gmail 邮件列表；
- 支持按分类筛选；
- 支持按优先级筛选；
- 支持按是否需要回复筛选；
- 支持触发“重新分析邮件”；
- 支持点击邮件进入详情页。

#### 推荐视图

```text
全部 | 高优先级 | 需要回复 | 会议相关 | 待办事项 | 通知类 | 可忽略
```

#### 邮件卡片展示字段

- 主题；
- 发件人；
- 时间；
- 分类标签；
- 优先级标签；
- 摘要前两行；
- 是否需要回复；
- 是否包含会议请求。

---

### 11.5 页面三：Email Detail 邮件详情分析页

#### 左侧：原始邮件

- 邮件主题；
- 发件人；
- 收件时间；
- 正文；
- 附件信息。

#### 右侧：Agent 分析结果

- 邮件摘要；
- 关键点；
- 分类结果；
- 分类理由；
- 识别出的任务；
- 识别出的会议请求；
- 推荐操作按钮。

#### 推荐操作按钮

```text
生成回复草稿
查找会议时间
创建待办事项
标记为已处理
```

---

### 11.6 页面四：Calendar Planner 日程建议页

#### 功能

- 展示 Google Calendar 日程；
- 展示从邮件中识别出的会议请求；
- 展示 Agent 推荐的可用时间段；
- 支持用户选择一个时间段；
- 支持生成会议回复草稿；
- 支持创建待确认日程操作。

#### UI 组成

- 日历视图：FullCalendar；
- 会议请求卡片；
- 推荐时间段列表；
- 创建事件预览。

---

### 11.7 页面五：Draft Review 草稿审核页

#### 功能

- 展示 Agent 生成的回复草稿；
- 支持用户编辑草稿内容；
- 支持切换回复语气；
- 支持重新生成草稿；
- 支持提交为待确认操作；
- 支持创建 Gmail 草稿。

#### 草稿字段

```text
收件人
主题
正文
语气
关联邮件
生成理由
```

---

### 11.8 页面六：Pending Actions 待确认操作页

#### 功能

所有需要用户确认的操作都在这里展示。

操作类型：

```text
create_gmail_draft
create_calendar_event
```

每个操作卡片展示：

- 操作类型；
- 风险等级；
- 操作预览；
- Agent 执行理由；
- 关联邮件；
- 确认按钮；
- 拒绝按钮。

#### 确认后流程

```text
用户点击确认
    ↓
POST /api/v1/actions/{action_id}/confirm
    ↓
后端执行 Gmail / Calendar 工具
    ↓
更新操作状态
    ↓
前端刷新结果
```

---

### 11.9 页面七：Agent Trace 执行轨迹页

#### 功能

展示 Agent 系统的内部执行过程。

包括：

- 当前任务 ID；
- 每个 Agent 节点名称；
- 执行状态；
- 输入摘要；
- 输出摘要；
- 是否调用工具；
- 耗时；
- 错误信息。

#### 时间线示例

```text
1. Intent Agent：识别用户想要分析今日邮件
2. Gmail Tool：读取最近 20 封邮件
3. Email Summarizer Agent：生成邮件摘要
4. Email Triage Agent：判断优先级
5. Calendar Scheduler Agent：发现 1 个会议请求
6. Google Calendar Tool：查询可用时间
7. Reply Draft Agent：生成回复草稿
8. Safety Agent：创建待确认操作
```

这个页面是课程展示时的亮点，可以证明项目不是简单调用一次 LLM，而是一个多步骤 Agent 工作流。

---

### 11.10 页面八：Settings 设置页

#### 功能

- Google OAuth 连接状态；
- 当前登录用户信息；
- 邮件同步范围设置；
- 默认回复语言；
- 默认回复语气；
- 是否启用自动分析；
- 退出登录。

第一版设置项建议简单即可，不做复杂个性化记忆。

---

## 12. 前后端 API 设计

### 12.1 Dashboard API

```http
GET /api/v1/dashboard/summary
```

响应：

```json
{
  "email_count_today": 24,
  "high_priority_count": 3,
  "need_reply_count": 5,
  "meeting_request_count": 2,
  "pending_action_count": 2,
  "today_event_count": 4
}
```

---

### 12.2 邮件列表 API

```http
GET /api/v1/emails
```

查询参数：

```text
category
priority
need_reply
has_meeting_request
limit
offset
```

响应：

```json
{
  "items": [
    {
      "id": "email_001",
      "subject": "Project Meeting",
      "sender": "alice@example.com",
      "received_at": "2026-05-18T09:30:00",
      "summary": "对方希望下周二讨论项目进展。",
      "category": "calendar_related",
      "priority": "medium",
      "need_reply": true,
      "has_meeting_request": true
    }
  ],
  "total": 1
}
```

---

### 12.3 邮件详情 API

```http
GET /api/v1/emails/{email_id}
```

返回：

- 原始邮件内容；
- Agent 摘要；
- 分类结果；
- 任务提取结果；
- 会议请求识别结果；
- 推荐操作。

---

### 12.4 邮件分析 API

```http
POST /api/v1/emails/analyze
```

请求：

```json
{
  "range": "today",
  "limit": 20
}
```

响应：

```json
{
  "trace_id": "trace_001",
  "status": "running"
}
```

前端随后通过 SSE 或 WebSocket 获取执行进度。

---

### 12.5 草稿生成 API

```http
POST /api/v1/emails/{email_id}/draft-reply
```

请求：

```json
{
  "tone": "polite",
  "language": "en"
}
```

响应：

```json
{
  "draft_preview_id": "draft_preview_001",
  "to": "alice@example.com",
  "subject": "Re: Project Meeting",
  "body": "Dear Alice, ...",
  "requires_confirmation": true
}
```

---

### 12.6 日程 API

```http
GET /api/v1/calendar/events?range=today
```

```http
POST /api/v1/calendar/suggest-slots
```

请求：

```json
{
  "email_id": "email_001",
  "duration_minutes": 30
}
```

响应：

```json
{
  "suggested_slots": [
    {
      "start": "2026-05-19T14:00:00",
      "end": "2026-05-19T14:30:00",
      "reason": "该时间段没有已有会议。"
    }
  ]
}
```

---

### 12.7 待确认操作 API

```http
GET /api/v1/actions?status=pending
```

```http
POST /api/v1/actions/{action_id}/confirm
```

```http
POST /api/v1/actions/{action_id}/reject
```

确认操作响应：

```json
{
  "status": "executed",
  "result": "Gmail draft created successfully."
}
```

---

### 12.8 Agent Trace API

```http
GET /api/v1/traces/{trace_id}
```

```http
GET /api/v1/traces/{trace_id}/events
```

SSE：

```http
GET /api/v1/traces/{trace_id}/stream
```

事件示例：

```json
{
  "agent": "EmailTriageAgent",
  "status": "completed",
  "message": "完成 20 封邮件的优先级判断",
  "timestamp": "2026-05-18T10:00:00"
}
```

---

## 13. 数据库设计

### 13.1 users 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 用户 ID |
| email | VARCHAR | Google 邮箱 |
| name | VARCHAR | 用户名 |
| google_sub | VARCHAR | Google 用户唯一标识 |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.2 email_records 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 内部邮件 ID |
| user_id | UUID | 用户 ID |
| gmail_message_id | VARCHAR | Gmail 邮件 ID |
| thread_id | VARCHAR | Gmail 会话 ID |
| subject | TEXT | 邮件主题 |
| sender | TEXT | 发件人 |
| recipients | JSONB | 收件人 |
| received_at | TIMESTAMP | 接收时间 |
| body_text | TEXT | 邮件正文 |
| snippet | TEXT | Gmail snippet |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.3 email_analysis 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 分析 ID |
| email_id | UUID | 邮件 ID |
| summary | TEXT | 邮件摘要 |
| key_points | JSONB | 关键点 |
| category | VARCHAR | 邮件分类 |
| priority | VARCHAR | 优先级 |
| need_reply | BOOLEAN | 是否需要回复 |
| has_task | BOOLEAN | 是否包含任务 |
| has_meeting_request | BOOLEAN | 是否包含会议请求 |
| reason | TEXT | 判断理由 |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.4 tasks 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 任务 ID |
| user_id | UUID | 用户 ID |
| source_email_id | UUID | 来源邮件 |
| title | TEXT | 任务标题 |
| description | TEXT | 任务描述 |
| deadline | TIMESTAMP | 截止时间 |
| priority | VARCHAR | 优先级 |
| status | VARCHAR | todo / done / ignored |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.5 calendar_suggestions 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 建议 ID |
| user_id | UUID | 用户 ID |
| source_email_id | UUID | 来源邮件 |
| meeting_title | TEXT | 会议标题 |
| participants | JSONB | 参会人 |
| suggested_slots | JSONB | 推荐时间段 |
| selected_slot | JSONB | 用户选择的时间段 |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.6 draft_previews 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 草稿预览 ID |
| user_id | UUID | 用户 ID |
| source_email_id | UUID | 来源邮件 |
| to | TEXT | 收件人 |
| subject | TEXT | 主题 |
| body | TEXT | 正文 |
| tone | VARCHAR | 语气 |
| language | VARCHAR | 语言 |
| status | VARCHAR | preview / pending / created / rejected |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.7 pending_actions 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 操作 ID |
| user_id | UUID | 用户 ID |
| action_type | VARCHAR | create_gmail_draft / create_calendar_event |
| payload | JSONB | 操作参数 |
| preview | JSONB | 前端展示用预览 |
| risk_level | VARCHAR | low / medium / high |
| status | VARCHAR | pending / approved / rejected / executed / failed |
| result | JSONB | 执行结果 |
| created_at | TIMESTAMP | 创建时间 |
| executed_at | TIMESTAMP | 执行时间 |

---

### 13.8 agent_traces 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | Trace ID |
| user_id | UUID | 用户 ID |
| task_type | VARCHAR | analyze_emails / draft_reply / schedule_meeting |
| status | VARCHAR | running / completed / failed |
| input_summary | TEXT | 输入摘要 |
| output_summary | TEXT | 输出摘要 |
| created_at | TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP | 完成时间 |

---

### 13.9 agent_trace_events 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 事件 ID |
| trace_id | UUID | Trace ID |
| step | INTEGER | 步骤序号 |
| agent_name | VARCHAR | Agent 名称 |
| status | VARCHAR | running / completed / failed |
| message | TEXT | 展示信息 |
| input_preview | TEXT | 输入预览 |
| output_preview | TEXT | 输出预览 |
| created_at | TIMESTAMP | 创建时间 |

---

## 14. 后端项目目录结构

```text
mailflow-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes_auth.py
│   │   │   ├── routes_dashboard.py
│   │   │   ├── routes_email.py
│   │   │   ├── routes_calendar.py
│   │   │   ├── routes_actions.py
│   │   │   └── routes_traces.py
│   │   ├── agents/
│   │   │   ├── supervisor.py
│   │   │   ├── intent_agent.py
│   │   │   ├── planner_agent.py
│   │   │   ├── email_triage_agent.py
│   │   │   ├── email_summarizer_agent.py
│   │   │   ├── task_extraction_agent.py
│   │   │   ├── calendar_scheduler_agent.py
│   │   │   ├── reply_draft_agent.py
│   │   │   └── safety_agent.py
│   │   ├── graphs/
│   │   │   ├── email_analysis_graph.py
│   │   │   ├── draft_reply_graph.py
│   │   │   └── schedule_meeting_graph.py
│   │   ├── tools/
│   │   │   ├── gmail_tool.py
│   │   │   └── google_calendar_tool.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   └── google_provider.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   └── db/
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 15. 前端交互流程设计

### 15.1 邮件分析流程

```text
用户点击“同步并分析邮件”
    ↓
前端调用 POST /api/v1/emails/analyze
    ↓
后端返回 trace_id
    ↓
前端进入 Agent Trace 监听模式
    ↓
后端通过 SSE 推送执行过程
    ↓
分析完成后刷新 Dashboard 和 Inbox Triage
```

### 15.2 生成回复草稿流程

```text
用户在 Email Detail 页面点击“生成回复草稿”
    ↓
前端调用 POST /api/v1/emails/{id}/draft-reply
    ↓
后端生成 draft_preview
    ↓
前端跳转 Draft Review 页面
    ↓
用户编辑草稿
    ↓
用户点击“创建 Gmail 草稿”
    ↓
后端创建 Pending Action
    ↓
用户在 Pending Actions 页面确认
    ↓
后端调用 Gmail API 创建草稿
```

### 15.3 创建日程流程

```text
用户在会议相关邮件详情页点击“查找可用时间”
    ↓
前端调用 POST /api/v1/calendar/suggest-slots
    ↓
后端查询 Google Calendar
    ↓
前端展示推荐时间段
    ↓
用户选择时间段
    ↓
前端创建 Pending Action
    ↓
用户确认
    ↓
后端创建 Calendar Event
```

---

## 16. 开发路线图

### 第一阶段：项目初始化

目标：搭建前后端基础工程。

任务：

- 创建 GitHub 仓库 `mailflow-agent`；
- 初始化 FastAPI 后端；
- 初始化 Vue 3 + TypeScript + Vite 前端；
- 配置前后端目录结构；
- 配置 `.env.example`；
- 配置 PostgreSQL / Redis；
- 实现 `/health` 接口；
- 实现前端基础布局、侧边栏、路由。

验收标准：

```text
后端 uvicorn 可以启动。
前端 npm run dev 可以启动。
前端可以访问 Dashboard 空页面。
后端 /docs 可以打开。
```

---

### 第二阶段：Google OAuth 与 Gmail 接入

目标：实现 Google 登录和 Gmail 邮件读取。

任务：

- 创建 Google Cloud 项目；
- 配置 OAuth consent screen；
- 启用 Gmail API；
- 实现 OAuth 登录回调；
- 保存 token；
- 实现读取 Gmail 最近邮件；
- 前端实现 Settings 页显示 Google 连接状态；
- 前端实现 Inbox 邮件列表。

验收标准：

```text
用户可以连接 Google 账号。
系统可以读取 Gmail 最近邮件。
前端可以展示邮件列表。
```

---

### 第三阶段：邮件分析 Agent

目标：实现邮件摘要、分类和任务提取。

任务：

- 实现 Email Summarizer Agent；
- 实现 Email Triage Agent；
- 实现 Task Extraction Agent；
- 建立 email_analysis 表；
- 实现邮件分析工作流；
- 前端实现 Inbox Triage 看板；
- 前端实现 Email Detail 分析面板。

验收标准：

```text
点击“分析邮件”后，系统可以输出摘要、分类、优先级、是否需要回复、是否包含任务或会议请求。
```

---

### 第四阶段：Agent Trace 可视化

目标：展示多 Agent 执行过程。

任务：

- 后端记录 agent_traces；
- 后端记录 agent_trace_events；
- 实现 SSE 或 WebSocket 推送；
- 前端实现 AgentTraceTimeline；
- 在邮件分析过程中实时展示执行步骤。

验收标准：

```text
用户能看到 Agent 正在执行哪个步骤，而不是只看到最终结果。
```

---

### 第五阶段：回复草稿工作流

目标：根据邮件生成草稿，并由用户审核。

任务：

- 实现 Reply Draft Agent；
- 实现 draft_previews 表；
- 实现草稿生成 API；
- 前端实现 Draft Review 页面；
- 支持用户修改草稿；
- 实现创建 Gmail 草稿的 Pending Action。

验收标准：

```text
用户可以从邮件详情页生成草稿，在前端编辑后确认创建 Gmail 草稿。
```

---

### 第六阶段：Google Calendar 接入

目标：实现会议请求识别和日程建议。

任务：

- 启用 Google Calendar API；
- 实现读取日程接口；
- 实现查询可用时间；
- 实现 Calendar Scheduler Agent；
- 前端接入 FullCalendar；
- 前端实现 Calendar Planner 页面；
- 支持从会议邮件生成日程建议。

验收标准：

```text
系统可以根据会议请求查询日历，并给出可用时间段。
```

---

### 第七阶段：Human-in-the-loop 操作中心

目标：所有高风险操作都必须确认。

任务：

- 实现 pending_actions 表；
- 实现创建 Pending Action；
- 实现确认 / 拒绝 API；
- 前端实现 Pending Actions 页面；
- 确认后执行 Gmail 草稿创建或 Calendar 日程创建。

验收标准：

```text
系统不会直接执行外部操作，必须由用户点击确认。
```

---

### 第八阶段：Dashboard 与课程展示优化

目标：形成完整可演示系统。

任务：

- 完善 Dashboard 数据统计；
- 优化邮件看板；
- 优化 Agent Trace 页面；
- 准备演示数据；
- 完善 README；
- 编写课程展示脚本；
- 录制或准备 Demo 流程。

验收标准：

```text
可以完整演示：连接 Google → 同步邮件 → Agent 分析 → 发现会议请求 → 查询日程 → 生成回复草稿 → 用户确认 → 创建草稿或日程。
```

---

## 17. 安全设计

### 17.1 OAuth 权限最小化

只申请必要权限：

```text
读取 Gmail 邮件
创建 Gmail 草稿
读取 Google Calendar
创建 Google Calendar 事件
```

第一版不申请删除邮件、批量修改邮件、自动发送邮件等高风险权限。

---

### 17.2 Human-in-the-loop

所有外部可见操作必须确认。

外部可见操作包括：

```text
创建 Gmail 草稿
创建 Google Calendar 事件
邀请参会人
```

前端必须展示操作预览，用户确认后才执行。

---

### 17.3 日志脱敏

日志中不能直接输出：

```text
access_token
refresh_token
完整邮件正文
联系人隐私信息
OAuth client secret
```

---

## 18. 课程展示方案

### 18.1 展示标题

```text
MailFlow Agent：基于 FastAPI、LangGraph 与 Vue 的多 Agent 邮件与日程助理系统
```

### 18.2 展示重点

1. 系统不是聊天机器人，而是智能办公工作台；
2. 前端通过 Dashboard、邮件看板、草稿审核、待确认中心展示 Agent 能力；
3. LangGraph 负责任务拆解和多 Agent 编排；
4. Gmail 和 Google Calendar 提供真实工具调用；
5. Human-in-the-loop 保证安全；
6. Agent Trace 展示每一步执行过程，便于解释系统行为。

### 18.3 Demo 流程

```text
1. 打开 Dashboard，查看今日邮件和待办状态。
2. 点击“同步并分析 Gmail”。
3. Agent Trace 页面展示执行过程。
4. 进入 Inbox Triage，看邮件被自动分类。
5. 点击一封会议相关邮件，查看分析结果。
6. 系统推荐可用会议时间。
7. 生成英文回复草稿。
8. 用户在 Draft Review 页面编辑草稿。
9. 用户在 Pending Actions 页面确认创建 Gmail 草稿或 Calendar 事件。
10. 系统返回执行结果。
```

### 18.4 项目亮点

```text
Vue 智能办公工作台
多 Agent 工作流
Agent Trace 可视化
Gmail + Calendar 联动
邮件分类看板
草稿审核机制
Human-in-the-loop 安全控制
FastAPI 工程化后端
```

---

## 19. README 建议结构

```markdown
# MailFlow Agent

A multi-agent email and calendar assistant built with FastAPI, LangGraph and Vue.

## Features

- Gmail inbox synchronization
- Email summarization
- Email triage board
- Task extraction
- Meeting request detection
- Google Calendar scheduling suggestions
- Reply draft generation
- Draft review workspace
- Pending action confirmation
- Agent execution trace visualization

## Tech Stack

### Backend

- FastAPI
- LangGraph
- PostgreSQL
- Redis
- Gmail API
- Google Calendar API

### Frontend

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Element Plus
- FullCalendar

## Architecture

[architecture diagram]

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Demo Flow

1. Connect Google account
2. Sync Gmail messages
3. Run multi-agent email analysis
4. Review categorized inbox
5. Generate reply draft
6. Suggest calendar slots
7. Confirm pending action

## License

MIT
```

---

## 20. 最小可交付版本

如果时间有限，至少完成以下内容：

```text
1. FastAPI 后端可运行；
2. Vue 前端可运行；
3. Google OAuth 可登录；
4. 可以读取 Gmail 最近邮件；
5. 可以对邮件生成摘要和分类；
6. 可以在 Vue 邮件看板中展示分类结果；
7. 可以点击邮件查看详情和 Agent 分析；
8. 可以生成回复草稿；
9. 可以展示 Pending Action；
10. 用户确认后可以创建 Gmail 草稿；
11. Agent Trace 页面可以展示执行步骤。
```

如果时间允许，再完成：

```text
12. Google Calendar 日程读取；
13. 会议请求识别；
14. 推荐可用时间；
15. 用户确认后创建 Calendar Event。
```

---

## 21. 最终一句话介绍

```text
MailFlow Agent 是一个基于 FastAPI、LangGraph 和 Vue 构建的多 Agent 邮件与日程助理系统，它通过可视化办公工作台展示邮件分类、任务提取、会议安排、草稿审核和 Agent 执行轨迹，并通过 Human-in-the-loop 机制保证所有高风险操作都由用户确认。
```

---

## 22. 推荐开发顺序总结

```text
Step 1: 初始化 FastAPI 后端和 Vue 前端
Step 2: 实现 Google OAuth
Step 3: 接入 Gmail API，展示邮件列表
Step 4: 实现邮件摘要和分类 Agent
Step 5: 实现 Vue 邮件分类看板和详情分析页
Step 6: 实现 Agent Trace 可视化
Step 7: 实现回复草稿生成和 Draft Review 页面
Step 8: 实现 Pending Actions 确认机制
Step 9: 接入 Google Calendar
Step 10: 实现会议请求识别和日程建议
Step 11: 优化 Dashboard 和课程展示流程
```

建议优先保证这条主链路稳定：

```text
Gmail 邮件读取 → Agent 邮件分析 → Vue 看板展示 → 邮件详情分析 → 生成草稿 → 用户确认 → 创建 Gmail 草稿
```

完成这条链路后，再加入 Google Calendar 会议安排能力。

