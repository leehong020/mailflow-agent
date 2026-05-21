export interface ActionInfo {
  id: string
  action_type: string
  draft_preview_id?: string | null
  payload: Record<string, unknown>
  preview: Record<string, unknown>
  risk_level: string
  status: string
  result?: Record<string, unknown> | null
  created_at: string
  executed_at?: string | null
}

export interface ActionListResponse {
  items: ActionInfo[]
  total: number
}

export interface ConfirmActionResponse {
  status: string
  result: string
}
