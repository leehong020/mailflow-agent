// Inbox 列表中单封邮件的展示字段。
export interface EmailListItem {
  id: string
  thread_id?: string | null
  subject: string
  sender: string
  recipients: string[]
  label_ids: string[]
  is_read: boolean
  is_starred: boolean
  mailbox_status: string
  received_at?: string | null
  snippet: string
  body_preview?: string | null
  analysis?: EmailAnalysisInfo | null
}

// 邮件列表响应，保留 total 便于后续分页。
export interface EmailListResponse {
  items: EmailListItem[]
  total: number
  analyzed_total: number
  unanalyzed_total: number
}

export interface EmailAnalysisInfo {
  summary: string
  key_points: string[]
  category: string
  priority: string
  need_reply: boolean
  has_task: boolean
  has_meeting_request: boolean
  reason: string
  recommended_actions: string[]
}

export interface TaskInfo {
  id: string
  title: string
  description: string
  deadline?: string | null
  priority: string
  status: string
}

export interface EmailDetail extends EmailListItem {
  body_text: string
  tasks: TaskInfo[]
}

export interface AnalyzeEmailsResponse {
  status: string
  analyzed_count: number
  message: string
  trace_ids: string[]
}

// Gmail 同步响应：只说明本次新增了多少封邮件，不代表这些邮件已经完成 Agent 分析。
export interface SyncEmailsResponse {
  status: string
  synced_count: number
  message: string
}

export interface ReanalyzeEmailResponse {
  status: string
  message: string
}

export interface GmailLabelInfo {
  id: string
  name: string
  type: string
}

export interface GmailLabelListResponse {
  items: GmailLabelInfo[]
}

export interface EmailOperationResponse {
  status: string
  message: string
  action_id?: string | null
  email?: EmailListItem | null
}

export interface LabelActionRequest {
  add_label_ids: string[]
  remove_label_ids: string[]
}

export interface BatchEmailActionRequest {
  email_ids: string[]
  operation: string
  add_label_ids?: string[]
  remove_label_ids?: string[]
}
