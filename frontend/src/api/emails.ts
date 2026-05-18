import { http } from './http'
import type { EmailListResponse } from '@/types/email'

// 读取 Gmail 最近邮件，limit 控制最多返回多少封。
export function getRecentEmails(limit = 20) {
  return http.get<EmailListResponse>('/emails', { params: { limit } })
}
