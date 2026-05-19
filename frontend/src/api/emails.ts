import { http } from './http'
import type { AnalyzeEmailsResponse, EmailDetail, EmailListResponse, ReanalyzeEmailResponse } from '@/types/email'

export interface EmailQuery {
  category?: string
  priority?: string
  need_reply?: boolean
  has_meeting_request?: boolean
  has_task?: boolean
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

// 重新分析单封邮件。
export function reanalyzeEmail(emailId: string) {
  return http.post<ReanalyzeEmailResponse>(`/emails/${emailId}/reanalyze`)
}

// 获取邮件详情和 Agent 分析结果。
export function getEmailDetail(emailId: string) {
  return http.get<EmailDetail>(`/emails/${emailId}`)
}
