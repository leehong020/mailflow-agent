// 单条 Agent 执行事件。
export interface TraceEventInfo {
  id: string
  step: number
  agent_name: string
  status: string
  message: string
  input_preview: string
  output_preview: string
  created_at: string
}

// 单次轨迹详情。
export interface TraceInfo {
  id: string
  task_type: string
  status: string
  input_summary: string
  output_summary: string
  created_at: string
  completed_at?: string | null
  events: TraceEventInfo[]
}

// 轨迹列表项。
export interface TraceListItem {
  id: string
  task_type: string
  status: string
  input_summary: string
  output_summary: string
  created_at: string
}

// 轨迹列表响应。
export interface TraceListResponse {
  items: TraceListItem[]
  total: number
}
