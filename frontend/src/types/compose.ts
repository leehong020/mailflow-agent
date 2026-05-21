// 第十二阶段主动写邮件的前端类型。
// 它和 draft 类型分开，是为了让“主动写邮件”和“草稿记录”边界更清楚。

export interface ComposeGenerateRequest {
  goal: string
  to: string
  subject: string
  body: string
  tone: string
  language: string
}

export interface ComposeReviseRequest {
  instruction: string
  to: string
  subject: string
  body: string
  tone: string
  language: string
}

export interface ComposeDraftResponse {
  draft_preview_id: string
  to: string
  subject: string
  body: string
  tone: string
  language: string
  generation_reason: string
  trace_id?: string | null
}
