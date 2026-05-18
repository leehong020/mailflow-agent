// Inbox 列表中单封邮件的展示字段。
export interface EmailListItem {
  id: string
  thread_id?: string | null
  subject: string
  sender: string
  recipients: string[]
  received_at?: string | null
  snippet: string
  body_preview?: string | null
}

// 邮件列表响应，保留 total 便于后续分页。
export interface EmailListResponse {
  items: EmailListItem[]
  total: number
}
