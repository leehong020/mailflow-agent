import { http } from './http'
import type {
  AnalyzeEmailsResponse,
  BatchEmailActionRequest,
  EmailDetail,
  EmailListResponse,
  EmailOperationResponse,
  GmailLabelListResponse,
  LabelActionRequest,
  ReanalyzeEmailResponse,
  SyncEmailsResponse,
} from '@/types/email'

export interface EmailQuery {
  category?: string
  priority?: string
  need_reply?: boolean
  has_meeting_request?: boolean
  has_task?: boolean
  search?: string
  analyzed?: boolean
  label?: string
  is_read?: boolean
  is_starred?: boolean
  mailbox_status?: string
  limit?: number
  offset?: number
}

// 查询本地邮件列表，支持第三阶段看板筛选。
export function getRecentEmails(params: EmailQuery = {}) {
  return http.get<EmailListResponse>('/emails', { params: { limit: 20, ...params } })
}

// 触发第三阶段分析：只分析本地尚未分析的邮件。
export function analyzeEmails(limit = 20) {
  return http.post<AnalyzeEmailsResponse>('/emails/analyze', { range: 'recent', limit })
}

// 只同步 Gmail 最新邮件到本地库，不触发大模型 Agent 分析。
// 用在“刷新看板”：先把新邮件拉进数据库，再调用列表接口展示出来。
export function syncEmails(limit = 20) {
  return http.post<SyncEmailsResponse>('/emails/sync', { limit })
}

// 重新分析单封邮件。
export function reanalyzeEmail(emailId: string) {
  return http.post<ReanalyzeEmailResponse>(`/emails/${emailId}/reanalyze`)
}

// 获取邮件详情和 Agent 分析结果。
export function getEmailDetail(emailId: string) {
  return http.get<EmailDetail>(`/emails/${emailId}`)
}

export function getGmailLabels() {
  return http.get<GmailLabelListResponse>('/emails/labels')
}

export function markEmailRead(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/mark-read`)
}

export function markEmailUnread(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/mark-unread`)
}

export function starEmail(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/star`)
}

export function unstarEmail(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/unstar`)
}

export function createArchiveAction(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/archive-action`)
}

export function createTrashAction(emailId: string) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/trash-action`)
}

export function createLabelsAction(emailId: string, payload: LabelActionRequest) {
  return http.post<EmailOperationResponse>(`/emails/${emailId}/labels-action`, payload)
}

export function createBatchEmailAction(payload: BatchEmailActionRequest) {
  return http.post<EmailOperationResponse>('/emails/batch-action', payload)
}
