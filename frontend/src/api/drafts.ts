import { http } from './http'
import type {
  ConfirmActionResponse,
  CreatePendingActionForDraftResponse,
  CreateDraftPreviewRequest,
  CreateDraftPreviewResponse,
  DraftPreviewInfo,
  DraftPreviewListResponse,
  PendingActionListResponse,
  UpdateDraftPreviewRequest,
  UpdateDraftPreviewResponse,
} from '@/types/draft'

export function createDraftPreview(emailId: string, payload: CreateDraftPreviewRequest) {
  return http.post<CreateDraftPreviewResponse>(`/emails/${emailId}/draft-reply`, payload)
}

export function getDraftPreviews(params: { limit?: number; offset?: number } = {}) {
  return http.get<DraftPreviewListResponse>('/drafts/previews', { params: { limit: 20, ...params } })
}

export function getDraftPreview(previewId: string) {
  return http.get<DraftPreviewInfo>(`/drafts/previews/${previewId}`)
}

export function updateDraftPreview(previewId: string, payload: UpdateDraftPreviewRequest) {
  return http.put<UpdateDraftPreviewResponse>(`/drafts/previews/${previewId}`, payload)
}

export function createPendingActionForDraft(previewId: string) {
  return http.post<CreatePendingActionForDraftResponse>(`/drafts/previews/${previewId}/pending`)
}

export function getPendingActions(params: { limit?: number; offset?: number } = {}) {
  return http.get<PendingActionListResponse>('/drafts/pending', { params: { limit: 20, ...params } })
}

export function confirmPendingAction(actionId: string) {
  return http.post<ConfirmActionResponse>(`/drafts/pending/${actionId}/confirm`)
}

export function rejectPendingAction(actionId: string) {
  return http.post(`/drafts/pending/${actionId}/reject`)
}
