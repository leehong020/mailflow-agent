import { API_BASE_URL, http } from './http'
import type { TraceInfo, TraceListResponse } from '@/types/trace'

// 查询轨迹列表，用于前端时间线页面的概览。
export function getTraces(params: { status?: string | null; task_type?: string | null; limit?: number; offset?: number } = {}) {
  return http.get<TraceListResponse>('/traces', { params: { limit: 20, ...params } })
}

// 查询单条轨迹详情，包含每个 Agent 节点的执行事件。
export function getTrace(traceId: string) {
  return http.get<TraceInfo>(`/traces/${traceId}`)
}

// 订阅轨迹流式事件。EventSource 才能持续接收后端 SSE 推送。
export function streamTrace(traceId: string) {
  return new EventSource(`${API_BASE_URL}/traces/${traceId}/stream`)
}
