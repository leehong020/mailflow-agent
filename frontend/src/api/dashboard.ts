import { http } from './http'
import type { DashboardSummary } from '@/types/dashboard'

// 获取 Dashboard 顶部统计，数据全部来自当前账号的真实邮件、草稿、日程建议和 Agent 轨迹。
export function getDashboardSummary() {
  return http.get<DashboardSummary>('/dashboard/summary')
}
