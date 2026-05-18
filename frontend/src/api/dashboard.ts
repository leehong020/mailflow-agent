import { http } from './http'
import type { DashboardSummary } from '@/types/dashboard'

// 获取 Dashboard 顶部统计。当前阶段只有 Google 连接状态是真实数据。
export function getDashboardSummary() {
  return http.get<DashboardSummary>('/dashboard/summary')
}
