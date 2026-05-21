import { http } from './http'
import type { ActionListResponse, ConfirmActionResponse } from '@/types/action'

export function getActions(params: { status?: string | null; limit?: number; offset?: number } = {}) {
  return http.get<ActionListResponse>('/actions', { params: { status: 'pending', limit: 20, ...params } })
}

export function confirmAction(actionId: string) {
  return http.post<ConfirmActionResponse>(`/actions/${actionId}/confirm`)
}

export function rejectAction(actionId: string) {
  return http.post(`/actions/${actionId}/reject`)
}
