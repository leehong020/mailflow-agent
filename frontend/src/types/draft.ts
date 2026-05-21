export interface CreateDraftPreviewRequest {
  tone: string
  language: string
}

export interface CreateDraftPreviewResponse {
  draft_preview_id: string
  to: string
  subject: string
  body: string
  requires_confirmation: boolean
  generation_reason: string
}

export interface DraftPreviewInfo {
  id: string
  source_email_id: string
  to: string
  subject: string
  body: string
  tone: string
  language: string
  status: string
  generation_reason: string
  created_at?: string | null
  updated_at?: string | null
}

export interface DraftPreviewListResponse {
  items: DraftPreviewInfo[]
  total: number
}

export interface MailEditorState {
  to: string
  subject: string
  body: string
  tone: string
  language: string
}

export interface PendingActionInfo {
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

export interface PendingActionListResponse {
  items: PendingActionInfo[]
  total: number
}

export interface CreateSendActionResponse {
  action_id: string
  status: string
  message: string
}

export interface DeleteDraftPreviewResponse {
  status: string
  message: string
}

export interface ConfirmActionResponse {
  status: string
  result: string
}
