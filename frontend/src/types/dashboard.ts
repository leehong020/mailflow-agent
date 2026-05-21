export interface DashboardBreakdownItem {
  label: string
  value: number
}

export interface DashboardRecentItem {
  id: string
  title: string
  subtitle: string
  status: string
  created_at?: string | null
}

// Dashboard 首页统计卡片类型。
export interface DashboardSummary {
  google_connected: boolean
  email_count_today: number
  analyzed_email_count: number
  high_priority_count: number
  need_reply_count: number
  meeting_request_count: number
  task_count: number
  pending_action_count: number
  today_event_count: number
  calendar_suggestion_count: number
  draft_preview_count: number
  trace_count: number
  category_breakdown: DashboardBreakdownItem[]
  priority_breakdown: DashboardBreakdownItem[]
  recent_emails: DashboardRecentItem[]
  recent_actions: DashboardRecentItem[]
  recent_traces: DashboardRecentItem[]
}
