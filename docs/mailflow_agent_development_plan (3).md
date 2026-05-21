# MailFlow Agent 开发文档

## 1. 项目名称

### 推荐 GitHub 仓库名

**mailflow-agent**

### 中文项目名

**MailFlow Agent：基于 LangGraph 与 FastAPI 的多 Agent 邮件与日程助理系统**

### 命名理由

`mailflow-agent` 能够准确表达项目定位：

- `mail`：核心场景是邮件处理；
- `flow`：强调邮件、任务、日程、草稿、发送、确认之间的工作流；
- `agent`：强调系统由多个智能 Agent 协作完成任务。

该名称比 `email-chatbot` 或 `mail-assistant` 更适合课程展示，因为它突出的是一个完整的邮件与日程处理系统，而不是单调的聊天机器人。

---

## 2. 项目定位

### 2.1 项目简介

**MailFlow Agent** 是一个基于 **FastAPI + LangGraph + Vue** 构建的多 Agent 邮件与日程助理系统。

系统可以读取 Gmail 邮件，自动完成邮件摘要、优先级分类、待办事项提取、会议请求识别、Google Calendar 空闲时间查询、回复草稿生成、主动邮件撰写、邮件发送、邮件管理，并在用户确认后执行邮件和日程操作。

项目重点不是做一个简单对话机器人，而是做一个具有可视化操作界面、邮件工作台、AI 写信工作台、日程管理、草稿审核、待确认操作中心和 Agent 执行轨迹展示的智能办公系统。

### 2.2 项目目标

本项目目标是完成一个可演示、结构清晰、功能相对完整的课程项目，重点展示：

1. 使用 LangGraph 编排多 Agent 工作流；
2. 使用 FastAPI 提供后端 API；
3. 使用 Vue 构建非单一聊天模式的交互式前端；
4. 使用 Gmail API 完成邮件读取、草稿创建、草稿修改、邮件发送、邮件归档、移动到垃圾箱等操作；
5. 使用 Google Calendar API 完成日程查询、会议建议、日程创建等操作；
6. 使用 Human-in-the-loop 机制保证高风险操作必须用户确认；
7. 将 AI 写信从单纯聊天模式升级为“左侧邮件编辑器 + 右侧 AI 对话修改区”的双栏工作台；
8. 增加主动写邮件主界面，支持用户从零开始描述需求，由 Agent 生成邮件；
9. 展示 Agent 执行过程，而不是只展示最终回答；
10. 将邮件、任务、日程、草稿和待确认操作统一到一个工作台中。

---

## 3. 项目边界

为了保证项目可以稳定完成，当前版本只支持：

```text
Gmail + Google Calendar
```

当前版本暂不支持：

```text
Microsoft Outlook
QQ 邮箱
网易邮箱
IMAP / SMTP 多邮箱适配
复杂企业多用户权限系统
跨平台长期记忆系统
```

当前版本需要支持项目内记忆能力：

```text
短期记忆：保存一次写信 / 回复会话中的上下文、右侧 AI 对话记录、用户修改要求、当前编辑器状态。
```

记忆能力只服务于当前 MailFlow Agent 项目的写作会话，不扩展为复杂个人知识库、跨平台记忆系统或长期偏好设置。

需要特别说明：

```text
普通已接收邮件和已发送邮件的正文不能像文档一样被“修改”。
邮件修改主要指：修改草稿、修改标签、标记已读/未读、加星标、归档、移动到垃圾箱等。
删除邮件第一版建议实现“移动到垃圾箱”，不建议实现永久删除。
发送邮件、删除邮件、修改日程、删除日程等操作必须经过用户确认。
```

项目重点是把 Gmail 与 Google Calendar 的核心办公闭环做好，而不是扩展更多平台。

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
邮件读取 → Agent 分析 → 任务/会议识别 → 草稿生成/主动写信 → 用户编辑与 AI 修改 → 用户确认 → 邮件/日程执行操作
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
- 今日 Google Calendar 日程；
- 最近一次 Agent 分析状态。

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

前端以看板或列表形式展示，例如：

```text
高优先级 | 需要回复 | 会议相关 | 待办事项 | 通知类 | 可忽略
```

用户可以点击任意邮件查看摘要、分类理由和建议操作。

---

### 场景 3：邮件详情分析与邮件操作

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
- 推荐操作；
- 邮件操作按钮。

邮件操作包括：

```text
生成回复草稿
进入 AI 回复工作台
直接撰写回复
创建草稿
发送邮件
转发邮件
标记已读 / 未读
加星标 / 取消星标
归档
移动到垃圾箱
修改标签
```

其中发送、转发、删除、批量归档等操作必须进入待确认操作中心。

---

### 场景 4：AI 回复工作台

当用户点击某封邮件的“回复”或“生成回复草稿”时，系统进入专门的 **AI Reply Workspace**。

该页面采用双栏布局：

```text
左侧：邮件回复编辑器
右侧：AI 对话修改区
```

左侧用于展示和编辑最终要发送的邮件内容，包括：

- 收件人；
- 主题；
- 正文；
- 关联原邮件；
- 创建草稿按钮；
- 发送邮件按钮。

右侧用于和 AI 对话，用户可以提出修改要求，例如：

```text
帮我写得更正式一点。
语气不要太强硬。
帮我改成英文。
帮我缩短到 100 字以内。
帮我委婉拒绝这个会议邀请。
帮我加一句我明天下午有空。
```

AI 修改后，不应该只在聊天框中输出一段文本，而应该直接更新左侧邮件编辑器中的正文。用户可以继续人工编辑，也可以继续通过右侧 AI 对话修改。

---

### 场景 5：主动写邮件主界面

除了从某封邮件进入回复，系统还需要支持用户主动写一封新邮件。

左侧栏需要新增一个主入口：

```text
Compose Mail / 写邮件
```

用户进入该页面后，可以：

- 手动填写收件人、主题、正文；
- 输入自然语言需求，让 Agent 生成邮件；
- 选择语气：正式、简洁、友好、道歉、拒绝、确认；
- 选择语言：中文 / 英文；
- 让 AI 持续修改左侧邮件正文；
- 创建 Gmail 草稿；
- 发送邮件。

主动写邮件页面同样采用双栏布局：

```text
左侧：新邮件编辑器
右侧：AI 写作助手对话区
```

示例用户请求：

```text
帮我写一封邮件给导师，说明我这周五前会提交项目报告，语气正式一点。
```

Agent 应自动生成：

- 合适的主题；
- 邮件正文；
- 语气说明；
- 可选的后续建议。

用户确认后再创建草稿或发送。

---

### 场景 6：会议请求识别与日程建议

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
7. 进入 AI Reply Workspace，左侧显示回复内容，右侧允许用户继续修改；
8. Safety Agent 创建待确认操作；
9. 用户确认后，系统创建日程、修改日程或发送回复邮件。

---

### 场景 7：日程管理工作区

用户可以在 Calendar Planner 页面完成：

- 查看今日 / 本周日程；
- 查看事件详情；
- 创建新日程；
- 根据邮件创建会议日程；
- 修改日程时间、标题、地点、描述；
- 删除日程；
- 检测冲突；
- 为会议生成邮件回复草稿。

日程创建、修改、删除都属于外部可见操作，必须经过 Pending Actions 确认。

---

### 场景 8：待确认操作中心

所有高风险操作都会进入 Pending Actions 页面。

高风险操作包括：

```text
发送邮件
转发邮件
移动邮件到垃圾箱
批量归档邮件
创建 Gmail 草稿
修改 Gmail 草稿
创建 Google Calendar 日程
修改 Google Calendar 日程
删除 Google Calendar 日程
邀请参会人
```

用户必须手动确认后，后端才会真正执行。

---

## 6. 功能规划

### 6.1 后端功能

#### Gmail 基础功能

- Google OAuth 登录；
- 获取 Gmail 最近邮件；
- 按时间范围读取邮件；
- 获取单封邮件详情；
- 获取邮件 thread；
- 解析邮件主题、发件人、收件人、时间、正文；
- 读取 Gmail labels；
- 保存邮件分析结果。

#### Gmail 操作功能

- 创建 Gmail 草稿；
- 修改 Gmail 草稿；
- 删除 Gmail 草稿；
- 发送 Gmail 草稿；
- 直接发送新邮件；
- 回复邮件；
- 转发邮件；
- 标记已读 / 未读；
- 加星标 / 取消星标；
- 归档邮件；
- 修改邮件标签；
- 移动邮件到垃圾箱；
- 批量处理邮件。

第一版实现建议：

```text
优先实现：创建草稿、修改草稿、发送草稿、回复邮件、标记已读/未读、归档、移动到垃圾箱。
可后续实现：转发邮件、批量标签修改、批量归档。
不建议第一版实现：永久删除邮件。
```

#### AI 写信功能

- 根据原邮件生成回复草稿；
- 根据用户自然语言需求生成新邮件；
- 支持邮件主题自动生成；
- 支持收件人、主题、正文结构化输出；
- 支持右侧 AI 对话持续修改左侧编辑器内容；
- 支持语气转换；
- 支持语言转换；
- 支持缩写、扩写、润色、正式化、委婉化；
- 支持保存为本地草稿预览；
- 支持创建 Gmail 草稿；
- 支持发送前预览与确认。

#### Calendar 基础功能

- 获取 Google Calendar 今日 / 本周日程；
- 查询指定时间段内的日程；
- 获取单个日程详情；
- 检测日程冲突；
- 根据会议请求推荐空闲时间；
- 保存会议建议结果。

#### Calendar 操作功能

- 创建 Calendar 事件；
- 修改 Calendar 事件；
- 删除 Calendar 事件；
- 修改事件时间；
- 修改事件标题、地点、描述；
- 添加 / 移除参会人；
- 设置会议提醒；
- 生成会议回复草稿；
- 创建事件前冲突检测。

第一版实现建议：

```text
优先实现：创建事件、查询冲突、推荐时间。
可后续实现：修改事件、删除事件、复杂提醒配置、参会人 RSVP、Google Meet 链接。
```

#### Agent 功能

- 用户意图识别；
- 邮件摘要；
- 邮件优先级分类；
- 任务提取；
- 会议请求识别；
- 日程建议；
- 回复草稿生成；
- 主动邮件撰写；
- 邮件内容对话式修改；
- 安全审查；
- 待确认操作生成；
- Agent 执行轨迹记录。

#### 系统功能

- REST API；
- Server-Sent Events 或 WebSocket 流式推送 Agent 执行过程；
- 操作日志；
- 错误处理；
- 数据库持久化；
- Swagger API 文档；
- token 刷新；
- 操作失败重试；
- 权限不足提示。

---

### 6.2 前端功能

前端使用 **Vue 3 + TypeScript + Vite** 实现，不采用单一聊天窗口作为主界面，而是采用“智能办公工作台 + AI 写信工作台”模式。

核心页面包括：

1. Dashboard 首页；
2. Compose Mail 主动写邮件页；
3. Inbox Triage 邮件分类看板；
4. Email Detail 邮件详情分析页；
5. AI Reply Workspace AI 回复工作台；
6. Mail Operations 邮件操作区；
7. Calendar Planner 日程建议页；
8. Calendar Event Detail 日程详情页；
9. Draft Review 草稿列表与历史页；
10. Pending Actions 待确认操作页；
11. Agent Trace Agent 执行轨迹页；
12. Settings 设置页。

聊天入口可以保留，但只作为邮件写作或邮件修改工作台的一部分，而不是系统主界面。

---

## 7. 总体系统架构

```text
Vue Frontend
  ├── Dashboard
  ├── Compose Mail
  ├── Inbox Triage Board
  ├── Email Detail Analysis
  ├── AI Reply Workspace
  ├── Mail Operations
  ├── Calendar Planner
  ├── Calendar Event Detail
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
  ├── Memory Agent
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
| 富文本编辑器 | TipTap / Quill / Milkdown |
| 图标 | lucide-vue-next / Iconify |
| Markdown 渲染 | markdown-it |

推荐前端组合：

```text
Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus + FullCalendar + TipTap
```

---

## 9. 多 Agent 设计

本项目整体保持原有 Agent 体系，不额外扩展过多 Agent。考虑到 AI 回复工作台和主动写邮件页面都需要连续对话和草稿状态保存，因此允许新增一个必要的 **Memory Agent**。该 Agent 只负责短期会话记忆，不参与复杂任务规划，也不管理长期偏好设置，避免系统过度复杂化。

### 9.1 Supervisor Agent

职责：

- 接收用户请求或系统任务；
- 判断任务应该交给哪个 Agent；
- 管理 Agent 执行顺序；
- 汇总多个 Agent 的结果；
- 决定是否需要用户确认；
- 根据 Safety Agent 的结果决定进入 Pending Actions 或直接返回。

---

### 9.2 Intent Agent

职责：

- 判断用户意图；
- 区分邮件分析、主动写邮件、回复邮件、邮件内容修改、邮件发送、邮件删除、草稿修改、日程创建、日程修改、日程删除等请求；
- 将自然语言请求转化为结构化任务。

意图类型：

```text
summarize_emails
triage_inbox
compose_new_email
draft_reply
revise_email_content
send_email
reply_email
forward_email
modify_draft
archive_email
trash_email
mark_email_read
schedule_meeting
create_calendar_event
update_calendar_event
delete_calendar_event
extract_tasks
unknown
```

---

### 9.3 Planner Agent

职责：

- 将复杂任务拆解为多个执行步骤；
- 判断哪些步骤需要 Gmail Tool 或 Calendar Tool；
- 判断哪些步骤需要用户确认；
- 生成 LangGraph 执行路径。

示例一：回复邮件

```text
用户请求：帮我回复这封邮件并安排明天下午的会议。
Planner 输出：
1. 获取邮件详情
2. 摘要邮件需求
3. 查询明天下午日程
4. 推荐可用时间
5. 生成回复草稿
6. 更新 AI Reply Workspace 左侧编辑器
7. 创建发送邮件和创建日程的待确认操作
```

示例二：主动写邮件

```text
用户请求：帮我给导师写一封邮件，说明我周五前提交报告。
Planner 输出：
1. 识别写信目的、对象、语气和语言
2. 生成主题和正文
3. 更新 Compose Mail 左侧编辑器
4. 等待用户编辑或继续要求 AI 修改
5. 用户确认后创建 Gmail 草稿或发送邮件
```

---

### 9.4 Email Triage Agent

职责：

- 判断邮件优先级；
- 识别邮件类型；
- 判断是否需要回复；
- 判断是否涉及会议或待办事项；
- 输出分类理由；
- 为邮件操作提供建议，例如归档、忽略、回复、移动到垃圾箱。

输出示例：

```json
{
  "email_id": "email_001",
  "category": "urgent_reply",
  "priority": "high",
  "need_reply": true,
  "has_meeting_request": false,
  "has_task": true,
  "suggested_actions": ["draft_reply", "create_task"],
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
- 在前端任务区域中展示。

---

### 9.7 Calendar Scheduler Agent

职责：

- 识别会议请求；
- 提取会议主题、参会人、候选时间、会议时长；
- 查询 Google Calendar；
- 检查冲突；
- 推荐可用时间段；
- 生成创建、修改或删除日程所需参数。

---

### 9.8 Reply Draft Agent

职责：

- 根据邮件内容生成回复草稿；
- 根据用户自然语言需求生成新邮件；
- 根据会议建议生成确认邮件；
- 支持中文和英文；
- 支持正式、简洁、友好、拒绝、道歉、确认等语气；
- 支持对已有邮件正文进行修改；
- 支持把修改结果直接返回给前端编辑器；
- 支持用户修改后的草稿保存。

---

### 9.9 Memory Agent

职责：

- 管理 AI Reply Workspace 和 Compose Mail 的短期会话上下文；
- 保存当前写作 / 回复会话中的用户要求、右侧 AI 对话历史、AI 修改记录和编辑器快照；
- 在 Reply Draft Agent 生成或修改邮件时提供上下文；
- 在 Compose Mail Agent 生成或修改邮件时提供上下文；

短期记忆内容：

```text
当前 compose_session_id
当前邮件编辑器状态
本轮右侧 AI 对话历史
用户最近的修改要求
原邮件摘要
AI 修改记录
撤销历史
```

记忆写入规则：

```text
只保存当前草稿工作台中的短期会话记忆。
用户只是临时要求“这封邮件写正式一点”时，作为当前会话消息保存。
不做长期偏好保存，不在 Settings 中提供偏好管理。
```

---

### 9.10 Safety Agent

职责：

- 判断操作风险；
- 拦截外部可见操作；
- 为高风险操作创建 Pending Action；
- 等待用户确认后再执行；
- 防止 Agent 自动执行危险操作。

默认策略：

```text
所有会影响外部世界的操作都不能自动执行。
```

高风险操作包括：

```text
send_email
forward_email
trash_email
batch_archive_email
create_gmail_draft
update_gmail_draft
create_calendar_event
update_calendar_event
delete_calendar_event
invite_attendees
```

中低风险操作包括：

```text
mark_email_read
mark_email_unread
star_email
unstar_email
local_category_update
local_task_status_update
local_draft_preview_update
```

建议策略：

```text
读取类操作：无需确认
本地编辑器内容更新：无需确认
本地状态修改：无需确认或轻确认
Gmail / Calendar 外部写操作：必须确认
发送、删除、邀请类操作：必须二次确认
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

### 10.2 AI 回复工作流

```text
User selects email and clicks Reply / Generate Draft
    ↓
Email Detail Loaded
    ↓
Email Summarizer Agent provides context
    ↓
Memory Agent loads short-term session context and visible chat history
    ↓
Reply Draft Agent generates initial reply
    ↓
Memory Agent saves editor snapshot and AI generation record
    ↓
Return structured draft to AI Reply Workspace
    ↓
Left panel shows editable email content
    ↓
Right panel supports AI chat modifications
    ↓
User requests revision
    ↓
Memory Agent loads current editor state and conversation history
    ↓
Reply Draft Agent revises current editor content
    ↓
Memory Agent saves new editor snapshot
    ↓
Left panel updates final email content
    ↓
User chooses Create Draft or Send Email
    ↓
Safety Agent creates Pending Action
    ↓
User Confirm
    ↓
Gmail Tool creates draft or sends email
```

### 10.3 主动写邮件工作流

```text
User opens Compose Mail
    ↓
User enters writing goal in AI assistant panel
    ↓
Intent Agent identifies compose_new_email
    ↓
Planner Agent extracts recipient and writing goal
    ↓
Memory Agent loads current compose session and visible chat history
    ↓
Reply Draft Agent generates subject and body
    ↓
Left email editor is filled automatically
    ↓
User edits manually or asks AI to revise
    ↓
Memory Agent provides current editor state and conversation history
    ↓
Reply Draft Agent updates editor content
    ↓
Memory Agent saves editor snapshot
    ↓
User chooses Create Draft or Send Email
    ↓
Safety Agent creates Pending Action
    ↓
User Confirm
    ↓
Gmail Tool creates draft or sends email
```

### 10.4 邮件管理操作工作流

```text
User selects email operation
    ↓
Intent Agent identifies operation
    ↓
Planner Agent builds operation payload
    ↓
Safety Agent checks risk
    ↓
If low risk: execute directly
If high risk: create Pending Action
    ↓
User Confirm
    ↓
Gmail Tool executes operation
    ↓
Update local email state
```

支持操作：

```text
mark_read
mark_unread
star
unstar
archive
trash
modify_labels
send
reply
forward
```

### 10.5 会议安排工作流

```text
Meeting-related Email
    ↓
Calendar Scheduler Agent
    ↓
Google Calendar Tool: Query Events
    ↓
Find Available Slots
    ↓
Reply Draft Agent creates meeting reply
    ↓
AI Reply Workspace displays reply content
    ↓
Safety Agent creates Pending Action
    ↓
User Confirm
    ↓
Google Calendar Tool creates event
    ↓
Gmail Tool sends or drafts confirmation email
```

### 10.6 日程修改 / 删除工作流

```text
User selects calendar event
    ↓
Calendar Event Detail Loaded
    ↓
User modifies title/time/location/attendees or chooses delete
    ↓
Calendar Scheduler Agent checks conflicts if time changed
    ↓
Safety Agent creates Pending Action
    ↓
User Confirm
    ↓
Google Calendar Tool updates or deletes event
    ↓
Refresh Calendar Planner
```

### 10.7 Agent 执行轨迹

每个 Agent 节点执行时都记录事件：

```json
{
  "trace_id": "trace_001",
  "step": 3,
  "agent": "ReplyDraftAgent",
  "status": "running",
  "message": "正在根据用户要求修改邮件正文",
  "timestamp": "2026-05-18T10:00:00"
}
```

前端使用时间线组件展示：

```text
读取邮件 → 摘要生成 → 生成草稿 → 用户提出修改 → 更新编辑器 → 等待确认 → 执行操作
```

---

## 11. Vue 前端实现方案

### 11.1 前端设计原则

本项目的前端不采用单一聊天模式，而采用“任务驱动的办公工作台”。

核心原则：

1. Dashboard 展示全局状态；
2. Compose Mail 支持用户主动写邮件；
3. AI Reply Workspace 支持左侧编辑、右侧 AI 对话修改；
4. 邮件以列表和看板形式展示；
5. Agent 分析结果结构化展示；
6. 邮件和日程操作必须可视化；
7. 高风险操作集中到待确认中心；
8. Agent 执行过程用时间线展示；
9. 聊天框只作为写作助手，不作为唯一交互方式。

---

### 11.2 左侧栏设计

建议左侧栏调整为：

```text
Dashboard
Compose Mail
Inbox
Calendar Planner
Draft Review
Pending Actions
Agent Trace
Settings
```

其中新增的 **Compose Mail** 是主动写邮件的主界面。

---

### 11.3 前端页面结构

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
│   ├── draft.ts
│   ├── compose.ts
│   ├── memory.ts
│   ├── action.ts
│   └── trace.ts
├── api/
│   ├── http.ts
│   ├── auth.ts
│   ├── emails.ts
│   ├── calendar.ts
│   ├── drafts.ts
│   ├── compose.ts
│   ├── memory.ts
│   ├── actions.ts
│   └── agent.ts
├── views/
│   ├── DashboardView.vue
│   ├── ComposeMailView.vue
│   ├── InboxTriageView.vue
│   ├── EmailDetailView.vue
│   ├── AIReplyWorkspaceView.vue
│   ├── CalendarPlannerView.vue
│   ├── CalendarEventDetailView.vue
│   ├── DraftReviewView.vue
│   ├── PendingActionsView.vue
│   ├── AgentTraceView.vue
│   └── SettingsView.vue
├── components/
│   ├── layout/
│   ├── email/
│   │   ├── EmailList.vue
│   │   ├── EmailCard.vue
│   │   ├── EmailCategoryBadge.vue
│   │   ├── EmailPriorityTag.vue
│   │   ├── EmailAnalysisPanel.vue
│   │   └── EmailOperationBar.vue
│   ├── compose/
│   │   ├── MailEditor.vue
│   │   ├── ComposeAssistantPanel.vue
│   │   ├── ComposeToolbar.vue
│   │   ├── RecipientInput.vue
│   │   └── DraftMemoryPanel.vue
│   ├── calendar/
│   │   ├── CalendarMiniView.vue
│   │   ├── SuggestedSlots.vue
│   │   ├── EventCreatePreview.vue
│   │   └── EventEditDialog.vue
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
    ├── draft.ts
    ├── compose.ts
    ├── action.ts
    └── agent.ts
```

---

### 11.4 Dashboard 首页

Dashboard 是系统主入口，展示整体办公状态。

页面模块：

- 邮件统计卡片；
- 高优先级邮件列表；
- 需要回复邮件列表；
- 今日会议列表；
- 待确认操作列表；
- Agent 最近执行记录；
- 快捷操作按钮。

快捷操作按钮：

```text
同步并分析邮件
写一封新邮件
创建新日程
查看待确认操作
```

---

### 11.5 Compose Mail 主动写邮件页

页面采用双栏布局：

```text
左侧：邮件编辑器
右侧：AI 写作助手
```

左侧邮件编辑器字段：

```text
To
Subject
Body
Attachments 可先预留
```

右侧 AI 写作助手能力：

```text
根据用户需求生成邮件
根据当前正文继续修改
调整语气
调整语言
缩短正文
扩写正文
生成主题
检查是否礼貌
检查是否遗漏关键信息
```

操作按钮：

```text
生成邮件
重新生成
创建 Gmail 草稿
发送邮件
清空
```

发送邮件和创建 Gmail 草稿都必须进入 Pending Actions。

---

### 11.6 AI Reply Workspace 回复工作台

进入方式：

```text
Inbox 邮件卡片 → 回复 / 生成草稿
Email Detail 页面 → 回复 / 生成回复草稿
会议建议页 → 生成会议回复
```

页面布局：

```text
左侧：回复邮件编辑器
右侧：AI 对话修改区
底部或顶部：原邮件上下文摘要
```

左侧编辑器字段：

```text
To
Subject
Body
关联原邮件
```

右侧对话区功能：

```text
显示当前 AI 修改历史
支持用户自然语言要求修改
AI 返回结构化修改结果
自动更新左侧编辑器
支持撤销上一次 AI 修改
```

关键交互要求：

```text
AI 的输出不能只停留在聊天区。
AI 修改后的邮件正文必须同步到左侧编辑器。
用户最终以左侧编辑器内容为准。
```

实现要点：

```text
1. 左侧编辑器是最终邮件内容的唯一可信来源。
2. 右侧 AI 对话区只负责生成修改建议和触发编辑器更新。
3. 每次 AI 修改前，前端需要把当前 editor state 一起传给后端。
4. 后端不要只返回自然语言说明，而要返回结构化邮件字段。
5. 前端收到 AI 修改结果后，直接覆盖或局部更新 To / Subject / Body。
6. 每次 AI 修改都保存一份 editor_snapshot，便于撤销和历史恢复。
7. 点击“发送邮件”时，以左侧编辑器当前内容为准创建 Pending Action。
```

推荐返回格式：

```json
{
  "updated_email": {
    "to": "example@example.com",
    "subject": "Re: Project Meeting",
    "body": "Dear Alice, ..."
  },
  "change_summary": "已将语气改得更正式，并补充了可参会时间。",
  "updated_fields": ["subject", "body"]
}
```

---

### 11.7 Compose Mail 主动写邮件页交互细化

Compose Mail 页面和 AI Reply Workspace 复用同一套核心组件，但业务上下文不同：

```text
Compose Mail：没有原始邮件上下文，用户从零开始写信。
AI Reply Workspace：有原始邮件上下文，用户基于某封邮件生成回复。
```

Compose Mail 推荐交互流程：

```text
1. 用户进入 Compose Mail。
2. 左侧编辑器为空，右侧 AI 写作助手显示引导问题。
3. 用户描述写信目的，例如“帮我给导师写一封请假邮件”。
4. Agent 生成收件人建议、主题和正文。
5. 左侧编辑器自动填充生成结果。
6. 用户可以手动修改，也可以继续要求 AI 修改。
7. 用户点击“创建 Gmail 草稿”或“发送邮件”。
8. Safety Agent 创建 Pending Action。
9. 用户确认后执行 Gmail 操作。
```

Compose Mail 与回复工作台的组件复用建议：

```text
MailEditor：复用，用于左侧邮件编辑器。
ComposeAssistantPanel：复用，用于右侧 AI 对话修改区，并展示历史对话。
DraftMemoryPanel：可选复用，用于展示当前草稿的会话记忆状态。
ConfirmActionDialog：复用，用于发送和创建草稿确认。
```

新增路由建议：

```text
/compose                    主动写新邮件
/reply/:emailId             回复某封邮件
/compose/:sessionId         继续编辑历史写作会话
```

---

### 11.8 Inbox Triage 邮件分类看板

功能：

- 展示 Gmail 邮件列表；
- 支持按分类筛选；
- 支持按优先级筛选；
- 支持按是否需要回复筛选；
- 支持触发“重新分析邮件”；
- 支持批量选择邮件；
- 支持批量标记已读、归档、移动到垃圾箱；
- 支持点击邮件进入详情页；
- 支持从邮件卡片直接进入 AI Reply Workspace。

推荐视图：

```text
全部 | 高优先级 | 需要回复 | 会议相关 | 待办事项 | 通知类 | 可忽略 | 垃圾箱
```

---

### 11.9 Email Detail 邮件详情分析页

左侧：原始邮件

- 邮件主题；
- 发件人；
- 收件时间；
- 正文；
- 附件信息。

右侧：Agent 分析结果

- 邮件摘要；
- 关键点；
- 分类结果；
- 分类理由；
- 识别出的任务；
- 识别出的会议请求；
- 推荐操作按钮。

顶部或底部：邮件操作栏

```text
回复
转发
进入 AI 回复工作台
标记已读 / 未读
加星标 / 取消星标
归档
移动到垃圾箱
修改标签
```

---

### 11.10 Calendar Planner 日程建议页

功能：

- 展示 Google Calendar 日程；
- 展示从邮件中识别出的会议请求；
- 展示 Agent 推荐的可用时间段；
- 支持用户选择一个时间段；
- 支持生成会议回复草稿；
- 支持创建待确认日程操作；
- 支持点击日程进入详情；
- 支持修改和删除日程。

UI 组成：

- 日历视图：FullCalendar；
- 会议请求卡片；
- 推荐时间段列表；
- 创建事件预览；
- 事件编辑弹窗。

---

### 11.11 Calendar Event Detail 日程详情页

功能：

- 展示事件标题、时间、地点、描述、参会人；
- 修改事件标题；
- 修改事件时间；
- 修改地点和描述；
- 添加或移除参会人；
- 删除事件；
- 修改前进行冲突检测；
- 提交修改为 Pending Action。

该页面可以放到后期实现。

---

### 11.12 Draft Review 草稿列表与历史页

Draft Review 不再作为唯一写信页面，而是用于管理已经生成或保存过的草稿。

功能：

- 查看本地草稿预览；
- 查看已创建的 Gmail 草稿记录；
- 继续编辑草稿；
- 进入 Compose Mail 或 AI Reply Workspace；
- 删除草稿；
- 发送草稿。

真正的写作和修改主要发生在：

```text
Compose Mail
AI Reply Workspace
```

---

### 11.13 Pending Actions 待确认操作页

功能：

所有需要用户确认的操作都在这里展示。

操作类型：

```text
create_gmail_draft
update_gmail_draft
send_email
forward_email
trash_email
archive_email
create_calendar_event
update_calendar_event
delete_calendar_event
```

每个操作卡片展示：

- 操作类型；
- 风险等级；
- 操作预览；
- Agent 执行理由；
- 关联邮件或日程；
- 确认按钮；
- 拒绝按钮。

---

### 11.14 Agent Trace 执行轨迹页

功能：

展示 Agent 系统的内部执行过程。

包括：

- 当前任务 ID；
- 每个 Agent 节点名称；
- 执行状态；
- 输入摘要；
- 输出摘要；
- 是否调用工具；
- 调用的 Gmail / Calendar 操作；
- 对编辑器的更新动作；
- 耗时；
- 错误信息。

---

### 11.15 Settings 设置页

功能：

- Google OAuth 连接状态；
- 当前登录用户信息；
- 邮件同步范围设置；
- 是否启用自动分析；
- 高风险操作确认策略；
- 清空短期写作会话；
- 退出登录。

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

### 12.2 邮件列表与分析 API

```http
GET  /api/v1/emails
GET  /api/v1/emails/{email_id}
POST /api/v1/emails/sync
POST /api/v1/emails/analyze
POST /api/v1/emails/{email_id}/analyze
```

查询参数：

```text
category
priority
need_reply
has_meeting_request
label
is_read
is_starred
limit
offset
```

---

### 12.3 AI 写信 API

```http
POST /api/v1/compose/generate
POST /api/v1/compose/revise
POST /api/v1/compose/check
POST /api/v1/compose/create-draft-action
POST /api/v1/compose/send-action
```

`POST /api/v1/compose/generate` 请求示例：

```json
{
  "goal": "帮我给导师写一封邮件，说明我周五前提交项目报告。",
  "tone": "formal",
  "language": "zh",
  "current_email": {
    "to": "",
    "subject": "",
    "body": ""
  }
}
```

响应示例：

```json
{
  "to": "",
  "subject": "关于项目报告提交时间的说明",
  "body": "老师您好，...",
  "explanation": "已使用正式语气，并明确说明提交时间。"
}
```

`POST /api/v1/compose/revise` 请求示例：

```json
{
  "instruction": "帮我写得更委婉一点，并缩短一些。",
  "current_email": {
    "to": "teacher@example.com",
    "subject": "关于项目报告提交时间的说明",
    "body": "老师您好，..."
  }
}
```

响应要求：

```text
compose/generate 和 compose/revise 都必须返回结构化邮件对象。
前端不能从一段普通文本中再手动解析主题和正文。
```

统一响应格式：

```json
{
  "session_id": "compose_session_001",
  "email": {
    "to": "teacher@example.com",
    "subject": "关于项目报告提交时间的说明",
    "body": "老师您好，..."
  },
  "assistant_message": "我已将邮件调整得更委婉，并保留了提交时间。",
  "updated_fields": ["subject", "body"]
}
```

---

### 12.4 AI 回复 API

```http
POST /api/v1/emails/{email_id}/reply-workspace/init
POST /api/v1/reply-workspace/{workspace_id}/revise
POST /api/v1/reply-workspace/{workspace_id}/create-draft-action
POST /api/v1/reply-workspace/{workspace_id}/send-action
```

说明：

```text
init 用于根据原邮件生成初始回复内容。
revise 用于根据右侧 AI 对话要求修改左侧编辑器内容。
create-draft-action 和 send-action 都需要进入 Pending Actions。
```

---

### 12.5 记忆 API

```http
GET    /api/v1/compose/sessions/{session_id}/memory
POST   /api/v1/compose/sessions/{session_id}/clear-memory
```

说明：

```text
compose session memory 用于短期记忆，例如当前写作 / 回复会话的右侧 AI 对话历史、用户修改要求和编辑器快照。
该对话历史必须作为前端可展示数据返回，包含 role、content、created_at、对应 editor_snapshot_id 等字段，保证用户重新进入草稿时能看到之前和大模型的聊天记录。
短期记忆可以在会话结束、用户清空草稿或退出登录后清理。
```

---

### 12.6 Gmail 操作 API

```http
POST /api/v1/emails/{email_id}/mark-read
POST /api/v1/emails/{email_id}/mark-unread
POST /api/v1/emails/{email_id}/star
POST /api/v1/emails/{email_id}/unstar
POST /api/v1/emails/{email_id}/archive-action
POST /api/v1/emails/{email_id}/trash-action
POST /api/v1/emails/{email_id}/labels-action
POST /api/v1/emails/batch-action
```

说明：

```text
mark-read、mark-unread、star、unstar 可以根据设置直接执行。
archive、trash、labels-action 建议进入 Pending Action。
batch-action 必须进入 Pending Action。
```

---

### 12.7 草稿与发送 API

```http
POST /api/v1/emails/{email_id}/draft-reply
POST /api/v1/emails/{email_id}/draft-forward
POST /api/v1/drafts
GET  /api/v1/drafts/{draft_id}
PATCH /api/v1/drafts/{draft_id}
DELETE /api/v1/drafts/{draft_id}/action
POST /api/v1/drafts/{draft_id}/send-action
POST /api/v1/emails/send-action
```

说明：

```text
创建草稿可以作为中风险操作，需要确认。
发送邮件必须作为高风险操作，需要二次确认。
删除草稿可以作为中风险操作，需要确认。
```

---

### 12.8 日程 API

```http
GET  /api/v1/calendar/events
GET  /api/v1/calendar/events/{event_id}
POST /api/v1/calendar/suggest-slots
POST /api/v1/calendar/events/create-action
PATCH /api/v1/calendar/events/{event_id}/update-action
DELETE /api/v1/calendar/events/{event_id}/delete-action
POST /api/v1/calendar/events/{event_id}/conflict-check
```

说明：

```text
创建、修改、删除日程都必须进入 Pending Action。
修改日程时间前必须进行冲突检测。
```

---

### 12.9 待确认操作 API

```http
GET  /api/v1/actions?status=pending
GET  /api/v1/actions/{action_id}
POST /api/v1/actions/{action_id}/confirm
POST /api/v1/actions/{action_id}/reject
POST /api/v1/actions/{action_id}/retry
```

确认操作响应：

```json
{
  "status": "executed",
  "result": "Email sent successfully."
}
```

---

### 12.10 Agent Trace API

```http
GET /api/v1/traces/{trace_id}
GET /api/v1/traces/{trace_id}/events
GET /api/v1/traces/{trace_id}/stream
```

事件示例：

```json
{
  "agent": "ReplyDraftAgent",
  "status": "completed",
  "message": "已根据用户要求更新左侧邮件编辑器内容。",
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

### 13.2 google_tokens 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | Token ID |
| user_id | UUID | 用户 ID |
| access_token_encrypted | TEXT | 加密后的 access token |
| refresh_token_encrypted | TEXT | 加密后的 refresh token |
| scopes | TEXT | 授权范围 |
| expires_at | TIMESTAMP | 过期时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.3 email_records 表

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
| labels | JSONB | Gmail 标签 |
| is_read | BOOLEAN | 是否已读 |
| is_starred | BOOLEAN | 是否星标 |
| is_trashed | BOOLEAN | 是否在垃圾箱 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.4 email_analysis 表

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
| suggested_actions | JSONB | 建议操作 |
| reason | TEXT | 判断理由 |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.5 tasks 表

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
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.6 compose_sessions 表

用于保存主动写邮件和回复邮件时的编辑会话。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 写作会话 ID |
| user_id | UUID | 用户 ID |
| source_email_id | UUID | 可为空，回复邮件时关联原邮件 |
| session_type | VARCHAR | compose_new / reply / forward |
| to | TEXT | 收件人 |
| subject | TEXT | 主题 |
| body | TEXT | 当前正文 |
| tone | VARCHAR | 语气 |
| language | VARCHAR | 语言 |
| status | VARCHAR | editing / pending / drafted / sent / abandoned |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.7 compose_messages 表

用于保存右侧 AI 对话修改历史。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 消息 ID |
| session_id | UUID | 写作会话 ID |
| role | VARCHAR | user / assistant |
| content | TEXT | 对话内容 |
| editor_snapshot | JSONB | 本轮对话后的编辑器快照 |
| created_at | TIMESTAMP | 创建时间 |

---

### 13.9 calendar_suggestions 表

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

### 13.10 calendar_events_cache 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 内部事件 ID |
| user_id | UUID | 用户 ID |
| google_event_id | VARCHAR | Google Calendar Event ID |
| title | TEXT | 标题 |
| description | TEXT | 描述 |
| location | TEXT | 地点 |
| attendees | JSONB | 参会人 |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| status | VARCHAR | confirmed / cancelled |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.11 draft_previews 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 草稿预览 ID |
| user_id | UUID | 用户 ID |
| source_email_id | UUID | 来源邮件 |
| compose_session_id | UUID | 关联写作会话 |
| gmail_draft_id | VARCHAR | Gmail 草稿 ID |
| to | TEXT | 收件人 |
| subject | TEXT | 主题 |
| body | TEXT | 正文 |
| tone | VARCHAR | 语气 |
| language | VARCHAR | 语言 |
| status | VARCHAR | preview / pending / created / sent / rejected / failed |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

### 13.12 pending_actions 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 操作 ID |
| user_id | UUID | 用户 ID |
| action_type | VARCHAR | 操作类型 |
| payload | JSONB | 操作参数 |
| preview | JSONB | 前端展示用预览 |
| risk_level | VARCHAR | low / medium / high |
| status | VARCHAR | pending / approved / rejected / executed / failed |
| result | JSONB | 执行结果 |
| created_at | TIMESTAMP | 创建时间 |
| executed_at | TIMESTAMP | 执行时间 |

支持的 `action_type`：

```text
create_gmail_draft
update_gmail_draft
send_email
forward_email
archive_email
trash_email
modify_email_labels
create_calendar_event
update_calendar_event
delete_calendar_event
```

---

### 13.13 agent_traces 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | Trace ID |
| user_id | UUID | 用户 ID |
| task_type | VARCHAR | analyze_emails / compose_email / revise_email / draft_reply / send_email / schedule_meeting / update_event |
| status | VARCHAR | running / completed / failed |
| input_summary | TEXT | 输入摘要 |
| output_summary | TEXT | 输出摘要 |
| created_at | TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP | 完成时间 |

---

### 13.14 agent_trace_events 表

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
│   │   │   ├── routes_compose.py
│   │   │   ├── routes_memory.py
│   │   │   ├── routes_draft.py
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
│   │   │   ├── memory_agent.py
│   │   │   └── safety_agent.py
│   │   ├── graphs/
│   │   │   ├── email_analysis_graph.py
│   │   │   ├── mail_operation_graph.py
│   │   │   ├── compose_mail_graph.py
│   │   │   ├── draft_reply_graph.py
│   │   │   ├── schedule_meeting_graph.py
│   │   │   └── calendar_operation_graph.py
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

### 15.2 回复邮件双栏编辑流程

```text
用户在 Email Detail 或 Inbox 中点击“回复 / 生成草稿”
    ↓
前端进入 AI Reply Workspace
    ↓
后端生成初始回复内容
    ↓
左侧编辑器展示收件人、主题和正文
    ↓
用户在右侧 AI 对话区提出修改要求
    ↓
后端根据当前编辑器内容和用户要求生成修改版
    ↓
左侧编辑器自动更新
    ↓
用户可继续手动编辑或继续让 AI 修改
    ↓
用户保存本地草稿或点击“发送邮件”
    ↓
后端创建 Pending Action
    ↓
用户确认
    ↓
Gmail Tool 发送邮件
```

### 15.3 主动写邮件流程

```text
用户点击左侧栏 Compose Mail
    ↓
进入主动写邮件页面
    ↓
用户在右侧 AI 写作助手中描述写信需求
    ↓
后端生成主题和正文
    ↓
左侧邮件编辑器自动填充
    ↓
用户继续让 AI 修改或手动编辑
    ↓
用户保存本地草稿或点击“发送邮件”
    ↓
后端创建 Pending Action
    ↓
用户确认
    ↓
Gmail Tool 发送邮件
```

### 15.4 邮件删除 / 归档流程

```text
用户在 Email Detail 或 Inbox 中选择归档 / 移动到垃圾箱
    ↓
前端展示操作预览
    ↓
后端创建 Pending Action
    ↓
用户确认
    ↓
Gmail Tool 执行归档或移动到垃圾箱
    ↓
前端刷新邮件列表
```

### 15.5 创建日程流程

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

### 15.6 修改 / 删除日程流程

```text
用户点击某个日程
    ↓
前端打开 Calendar Event Detail
    ↓
用户修改时间、标题、地点或选择删除
    ↓
如果修改时间，先调用冲突检测
    ↓
后端创建 Pending Action
    ↓
用户确认
    ↓
Google Calendar Tool 执行修改或删除
    ↓
前端刷新日历
```

该流程可以后期实现。

---

## 16. 完善后的开发路线图

你当前已经完成前 10 个阶段，因此后续应优先补强“AI 写信交互”和“主动写邮件主界面”。原先的第 11 阶段（日程管理能力完善）和第 12 阶段（安全、权限与可靠性完善）调整到最后实现。

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
- 配置 Gmail 读取、草稿、发送、标签修改相关 scope；
- 实现 OAuth 登录回调；
- 保存 token；
- 实现 token 刷新；
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
- 实现创建 Gmail 草稿的 Pending Action；
- 支持草稿修改和删除。

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
- 完善 README；
- 编写课程展示脚本；
- 录制或准备 Demo 流程。

验收标准：

```text
可以完整演示：连接 Google → 同步邮件 → Agent 分析 → 发现会议请求 → 查询日程 → 生成回复草稿 → 用户确认 → 创建草稿或日程。
```

---

### 第九阶段：邮件操作能力完善

目标：让系统从“只会分析邮件”升级为“可以管理邮件”。

任务：

- 实现邮件标记已读 / 未读；
- 实现星标 / 取消星标；
- 实现归档；
- 实现移动到垃圾箱；
- 实现标签修改；
- 实现批量邮件操作；
- 前端增加 EmailOperationBar；
- 高风险操作接入 Pending Actions。

验收标准：

```text
用户可以在邮件详情页或邮件列表中对邮件执行常见管理操作，并且高风险操作必须确认。
```

---

### 第十阶段：邮件发送能力完善

目标：支持完整的邮件撰写、回复、转发和发送，并为后续 AI 写信工作台提供基础能力。

任务：

- 实现新邮件撰写；
- 实现回复邮件；
- 实现转发邮件；
- 实现草稿修改；
- 实现发送草稿；
- 实现直接发送邮件；
- 发送前展示完整预览；
- 发送操作进入二次确认；
- 抽象统一的邮件编辑数据结构，供 Compose Mail 和 AI Reply Workspace 复用。

验收标准：

```text
用户可以生成、修改、确认并发送邮件；系统不会未经确认自动发送邮件。
同时，前端已经具备可复用的 MailEditor 数据结构，为第十一、十二阶段的双栏 AI 写信工作台做准备。
```

---

### 第十一阶段：AI 回复工作台重构

目标：把“生成回复草稿”从普通页面升级为“左侧邮件编辑器 + 右侧 AI 对话修改区”的双栏工作台。该阶段应优先于完整日程修改 / 删除实现，因为它直接改善邮件 Agent 的核心体验。

任务：

- 新增 `AIReplyWorkspaceView.vue`；
- 新增 `MailEditor.vue`；
- 新增 `ComposeAssistantPanel.vue`；
- 实现根据原邮件生成初始回复；
- 左侧展示可编辑的 To / Subject / Body；
- 右侧支持用户输入修改要求；
- AI 修改后自动更新左侧编辑器内容；
- 支持撤销上一次 AI 修改；
- 支持保存本地草稿修改；
- 支持发送邮件；
- 发送邮件进入 Pending Actions。

验收标准：

```text
用户可以在左侧看到最终回信内容，在右侧通过对话要求 AI 修改，AI 修改结果会直接同步到左侧编辑器。
```

---

### 第十二阶段：Compose Mail 主动写邮件主界面

目标：增加一个左侧栏主入口，让用户可以主动写一封新邮件，而不是必须从某封邮件进入回复。该阶段是项目从“邮件处理助手”升级为“邮件写作与处理工作台”的关键。

任务：

- 左侧栏新增 `Compose Mail`；
- 新增 `ComposeMailView.vue`；
- 新增 `ComposeMailAgent`；
- 新增 `compose_mail_agent.txt` 提示词；
- 新增 `routes_compose.py`；
- 实现用户自然语言描述写信需求；
- Agent 自动生成主题和正文；
- 左侧邮件编辑器展示生成结果；
- 右侧 AI 对话区支持持续修改；
- 支持保存为本地草稿记录，并出现在 Draft Review；
- 支持发送邮件；
- 写信过程记录 Agent Trace。

验收标准：

```text
用户可以点击左侧栏 Compose Mail，描述写信需求，由 ComposeMailAgent 生成邮件，并通过右侧 AI 对话不断修改左侧正文；生成过的内容会进入 Draft Review，最后可发送邮件并进入 Pending Actions。
```

---

### 第十三阶段：写作体验与记忆系统优化

目标：完善主动写信和回复写信的使用体验，并实现可见的短期会话记忆。第十三阶段不做语气选择器、语言选择器和长期偏好设置，语言由模型根据上下文自动判断，表达风格通过右侧 AI 对话临时指定。

任务：

- 支持邮件正文格式化；
- 支持 AI 生成主题；
- 支持保存本地草稿预览；
- 支持 Draft Review 管理历史草稿；
- 支持继续编辑历史草稿；
- 支持邮件发送前二次确认弹窗；
- 支持编辑器内容自动保存；
- 新增 Memory Agent；
- 实现 compose_sessions 和 compose_messages 的短期记忆；
- AI Reply Workspace 和 Compose Mail 都必须接入同一套短期记忆，保存并展示右侧 AI 对话历史、用户修改要求、AI 回复内容和 editor_snapshot；
- 用户重新进入历史草稿时，右侧 AI 对话区必须恢复之前和大模型聊天的上下文，而不是只恢复左侧邮件正文；

验收标准：

```text
写信过程不会因为页面切换丢失内容，用户可以从 Draft Review 继续编辑历史草稿。
用户在一次写信会话中多轮修改时，AI 能记住上下文和当前编辑器内容。
用户重新打开历史草稿时，右侧 AI 对话区能显示之前与大模型的聊天记录，包括用户指令和 AI 回复。
回复草稿工作台的右侧 AI 对话也具备和 Compose Mail 相同的短期记忆能力；Settings 不提供长期偏好管理。
```

---

### 第十四阶段：Calendar 基础创建能力收尾

目标：保证会议邮件到 Calendar Event 的主链路稳定，不急于实现复杂日程修改和删除。

任务：

- 优化会议请求识别；
- 优化时间段推荐；
- 支持从推荐时间创建 Calendar Event；
- 支持同时生成会议回复邮件；
- Calendar 创建操作进入 Pending Actions；
- 前端展示创建结果。

验收标准：

```text
用户可以从会议邮件生成可用时间建议，确认后创建 Calendar Event，并生成会议回复邮件。
```

---

### 第十五阶段：测试与展示完善

目标：形成稳定课程展示版本。

任务：

- 编写后端核心 API 测试；
- 编写 Gmail Tool 测试；
- 编写 AI 写信 API 测试；
- 编写前端关键页面检查；
- 完善 README；
- 完善演示脚本；
- 录制 Demo。

验收标准：

```text
项目可以稳定演示完整链路：邮件分析、AI 回复工作台、主动写邮件、邮件发送、日程创建、待确认操作和 Agent Trace。
```

---

### 第十六阶段：日程管理能力完善

目标：支持 Calendar 事件的完整管理。该阶段从原第十一阶段后移到最后实现。

任务：

- 实现 Calendar Event Detail 页面；
- 实现创建事件；
- 实现修改事件；
- 实现删除事件；
- 实现修改时间前冲突检测；
- 实现参会人管理；
- 日程写操作接入 Pending Actions。

验收标准：

```text
用户可以创建、修改、删除 Google Calendar 日程，并且所有写操作都需要确认。
```

---

### 第十七阶段：安全、权限与可靠性完善

目标：保证系统操作可控、错误可恢复。该阶段从原第十二阶段后移到最后实现。

任务：

- token 加密存储；
- token 自动刷新；
- Gmail / Calendar API 错误处理；
- Pending Action 失败重试；
- 操作日志脱敏；
- 高风险操作二次确认；
- 删除操作默认移动到垃圾箱；
- 前端显示权限不足提示；
- 补充生产环境 OAuth scope 说明。

验收标准：

```text
当 Google API 报错、token 过期、权限不足或操作失败时，系统能给出明确提示，并且不会执行不安全操作。
```

---

## 17. 记忆设计

### 17.1 短期记忆

短期记忆用于支持 AI Reply Workspace 和 Compose Mail 的连续编辑体验。

短期记忆保存范围：

```text
当前写作会话 ID
当前编辑器内容
右侧 AI 对话历史，必须可在前端聊天窗口重新展示
每条对话的 role、content、created_at
用户最近的修改要求
AI 每次回复给用户的说明文本
每次 AI 修改后的 editor_snapshot
原邮件摘要和上下文
撤销历史
```

短期记忆生命周期：

```text
用户仍在编辑页面：持续保留
用户跳转到 Draft Review：保留
用户发送成功：归档为历史记录
用户放弃草稿：可清理
用户手动清空：立即删除
```

### 17.2 记忆与 Agent 的关系

Memory Agent 不替代 Planner Agent，也不参与复杂任务规划。

```text
Memory Agent：读取或写入当前草稿的短期会话记忆
Reply Draft Agent：根据记忆生成或修改邮件
Compose Mail Agent：根据记忆生成或修改主动写邮件草稿
Safety Agent：判断最终操作是否需要确认
```

---

## 18. 安全设计

### 17.1 OAuth 权限规划

根据功能增强，需要合理申请权限。建议分阶段申请，不要一开始申请过多权限。

基础权限：

```text
读取 Gmail 邮件
创建 Gmail 草稿
读取 Google Calendar
创建 Google Calendar 事件
```

增强权限：

```text
发送 Gmail 邮件
修改 Gmail 标签和状态
移动 Gmail 邮件到垃圾箱
修改 Google Calendar 事件
删除 Google Calendar 事件
```

不建议第一版申请或使用：

```text
永久删除 Gmail 邮件
Drive 全量读取权限
非必要通讯录权限
```

---

### 17.2 Human-in-the-loop

所有外部可见操作必须确认。

外部可见操作包括：

```text
创建 Gmail 草稿
修改 Gmail 草稿
发送邮件
转发邮件
移动邮件到垃圾箱
创建 Google Calendar 事件
修改 Google Calendar 事件
删除 Google Calendar 事件
邀请参会人
```

前端必须展示操作预览，用户确认后才执行。

---

### 17.3 高风险操作二次确认

以下操作需要二次确认：

```text
发送邮件
转发邮件
移动邮件到垃圾箱
删除日程
邀请外部参会人
批量处理邮件
```

二次确认弹窗需要展示：

- 操作类型；
- 影响对象；
- 邮件收件人或日程参会人；
- 操作后果；
- 是否可撤销。

---

### 17.4 日志脱敏

日志中不能直接输出：

```text
access_token
refresh_token
完整邮件正文
联系人隐私信息
OAuth client secret
邮件附件内容
```

---

## 19. 课程展示方案

### 18.1 展示标题

```text
MailFlow Agent：基于 FastAPI、LangGraph 与 Vue 的多 Agent 邮件与日程助理系统
```

### 18.2 展示重点

1. 系统不是聊天机器人，而是智能办公工作台；
2. 前端通过 Dashboard、邮件看板、AI 写信工作台、待确认中心展示 Agent 能力；
3. AI 写信采用“左侧最终邮件 + 右侧对话修改”的交互方式；
4. LangGraph 负责任务拆解和多 Agent 编排；
5. Gmail 和 Google Calendar 提供真实工具调用；
6. Human-in-the-loop 保证安全；
7. Agent Trace 展示每一步执行过程，便于解释系统行为；
8. 系统不仅能分析邮件，还能执行邮件管理、主动写邮件、回复邮件和日程创建操作。

### 18.3 Demo 流程

```text
1. 打开 Dashboard，查看今日邮件和日程状态。
2. 点击“同步并分析 Gmail”。
3. Agent Trace 页面展示执行过程。
4. 进入 Inbox Triage，看邮件被自动分类。
5. 点击一封需要回复的邮件，进入 AI Reply Workspace。
6. 左侧展示 Agent 生成的回复邮件。
7. 在右侧要求 AI “写得更正式一点”或“改成英文”。
8. 左侧编辑器自动更新邮件正文。
9. 用户点击发送邮件，进入 Pending Actions 二次确认。
10. 打开 Compose Mail，主动描述写信需求。
11. Agent 生成新邮件主题和正文。
12. 用户继续通过右侧对话修改，最后创建 Gmail 草稿。
13. 对会议相关邮件生成可用时间建议，并创建 Calendar Event。
14. 回到 Dashboard，展示状态更新。
```

### 18.4 项目亮点

```text
Vue 智能办公工作台
主动写邮件主界面
AI 回复工作台双栏布局
多 Agent 工作流
Agent Trace 可视化
Gmail + Calendar 联动
邮件分类看板
草稿审核机制
邮件发送与管理
Human-in-the-loop 安全控制
FastAPI 工程化后端
```

---

## 20. README 建议结构

```markdown
# MailFlow Agent

A multi-agent email and calendar assistant built with FastAPI, LangGraph and Vue.

## Features

- Gmail inbox synchronization
- Email summarization
- Email triage board
- AI reply workspace with editable mail editor
- AI compose workspace for new emails
- Email management operations
- Reply draft generation
- Email sending with human confirmation
- Meeting request detection
- Google Calendar scheduling suggestions
- Calendar event creation
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
- TipTap / Rich Text Editor

## Demo Flow

1. Connect Google account
2. Sync Gmail messages
3. Run multi-agent email analysis
4. Review categorized inbox
5. Generate and revise reply in AI Reply Workspace
6. Compose a new email with AI
7. Confirm email sending
8. Suggest calendar slots
9. Create calendar event
10. Confirm pending action

## License

MIT
```

---

## 21. 最小可交付版本

如果时间有限，至少完成以下内容：

```text
1. FastAPI 后端可运行；
2. Vue 前端可运行；
3. Google OAuth 可登录；
4. 可以读取 Gmail 最近邮件；
5. 可以对邮件生成摘要和分类；
6. 可以在 Vue 邮件看板中展示分类结果；
7. 可以点击邮件查看详情和 Agent 分析；
8. 可以进入 AI Reply Workspace；
9. 左侧编辑器显示回复邮件内容；
10. 右侧 AI 对话可以修改左侧邮件正文；
11. 可以进入 Compose Mail 主动写邮件；
12. Agent 可以根据需求生成新邮件主题和正文；
13. 可以修改草稿；
14. 可以展示 Pending Action；
15. 用户确认后可以创建 Gmail 草稿；
16. 用户确认后可以发送邮件；
17. 可以标记已读 / 未读、归档、移动到垃圾箱；
18. Agent Trace 页面可以展示执行步骤；
19. 可以读取 Google Calendar 日程；
20. 可以从会议邮件创建 Calendar Event。
```

如果时间允许，再完成：

```text
21. Calendar Event 修改；
22. Calendar Event 删除；
23. 邮件转发；
24. 批量邮件处理；
25. 修改标签；
26. 日程冲突检测增强；
27. token 加密和生产级错误处理；
28. 写作会话历史恢复；
29. 右侧 AI 对话历史展示优化。
```

---

## 22. 最终一句话介绍

```text
MailFlow Agent 是一个基于 FastAPI、LangGraph 和 Vue 构建的多 Agent 邮件与日程助理系统，它通过可视化办公工作台展示邮件分类、任务提取、会议安排、主动写邮件、AI 回复修改、邮件发送、邮件管理、日程创建和 Agent 执行轨迹，并通过 Human-in-the-loop 机制保证所有高风险操作都由用户确认。
```

---

## 23. 推荐开发顺序总结

你当前已完成前 10 个阶段，后续建议优先顺序为：

```text
Step 11: 重构 AI Reply Workspace，实现左侧邮件编辑器 + 右侧 AI 对话修改
Step 12: 增加 Compose Mail 主界面，支持主动写邮件
Step 13: 优化写作体验、Draft Review 草稿管理和短期会话记忆
Step 14: 完成 Calendar 基础创建能力收尾
Step 15: 测试与课程展示完善
Step 16: 最后完善 Calendar 创建、修改、删除等完整日程管理
Step 17: 最后完善安全、权限、token 加密、错误处理和可靠性
```

建议优先保证这条主链路稳定：

```text
选择邮件 → 进入 AI Reply Workspace → 左侧生成回信 → 右侧对话修改 → 左侧同步更新 → 用户确认 → 发送邮件
```

然后补充第二条链路：

```text
Compose Mail 主动写邮件 → 描述写信需求 → Agent 生成主题和正文 → 保存到 Draft Review → 右侧对话修改 → 用户确认 → 发送邮件
```

最后补充第三条链路：

```text
会议邮件识别 → 查询 Google Calendar → 推荐时间 → 用户确认 → 创建 Calendar Event
```

原来规划中的完整日程修改 / 删除，以及安全、权限与可靠性增强，可以放到最后实现。
