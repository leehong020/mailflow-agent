export interface ComposeSessionInfo {
  id: string
  draft_preview_id: string
  session_type: string
  title: string
  editor_snapshot: Record<string, unknown>
  summary: string
  created_at: string
  updated_at: string
  messages: ComposeMessageInfo[]
}

export interface CreateComposeSessionRequest {
  draft_preview_id?: string
  session_type: string
  title: string
  editor_snapshot: Record<string, unknown>
}

export interface UpdateComposeSessionRequest {
  title?: string | null
  editor_snapshot?: Record<string, unknown> | null
}

export interface ComposeMessageRequest {
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type?: 'normal' | 'summary'
  editor_snapshot?: Record<string, unknown>
}

export interface ComposeMessageInfo {
  id: string
  role: 'user' | 'assistant' | 'system'
  message_type: 'normal' | 'summary'
  content: string
  editor_snapshot: Record<string, unknown>
  archived: boolean
  created_at: string
}
