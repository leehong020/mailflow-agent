import { http } from './http'
import type { ComposeDraftResponse, ComposeGenerateRequest, ComposeReviseRequest } from '@/types/compose'

// 根据用户写信目标生成一条本地草稿记录。
export function generateComposeDraft(payload: ComposeGenerateRequest) {
  return http.post<ComposeDraftResponse>('/compose/generate', payload)
}

// 根据用户对话要求修改已有主动写邮件草稿。
export function reviseComposeDraft(previewId: string, payload: ComposeReviseRequest) {
  return http.post<ComposeDraftResponse>(`/compose/previews/${previewId}/revise`, payload)
}
