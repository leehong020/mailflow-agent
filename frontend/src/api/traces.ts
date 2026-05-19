import { http } from './http'
import type { TraceInfo, TraceListResponse } from '@/types/trace'

// 查询轨迹列表，用于前端时间线页面的概览。
export function getTraces(params: { limit?: number; offset?: number } = {}) {
  return http.get<TraceListResponse>('/traces', { params: { limit: 20, ...params } })
}

// 查询单条轨迹详情，包含每个 Agent 节点的执行事件。
export function getTrace(traceId: string) {
  return http.get<TraceInfo>(`/traces/${traceId}`)
}

// 订阅轨迹流式事件。当前后端以 SSE 方式返回历史事件。
export function streamTrace(traceId: string) {
  return http.get(`/traces/${traceId}/stream`, { responseType: 'text' })
}
