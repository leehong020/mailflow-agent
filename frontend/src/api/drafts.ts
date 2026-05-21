import { http } from './http'
import type {
  ConfirmActionResponse,
  CreateDraftPreviewRequest,
  CreateDraftPreviewResponse,
  CreateSendActionResponse,
  DeleteDraftPreviewResponse,
  DraftPreviewInfo,
  DraftPreviewListResponse,
  MailEditorState,
  PendingActionListResponse,
} from '@/types/draft'

export function createDraftPreview(emailId: string, payload: CreateDraftPreviewRequest) {
  return http.post<CreateDraftPreviewResponse>(`/drafts/emails/${emailId}/preview`, payload)
}

export function createReplyWorkspacePreview(emailId: string) {
  return http.post<CreateDraftPreviewResponse>(`/drafts/emails/${emailId}/workspace`)
}

export function getDraftPreview(draftId: string) {
  return http.get<DraftPreviewInfo>(`/drafts/previews/${draftId}`)
}

export function getLatestDraftPreview(emailId: string) {
  return http.get<DraftPreviewInfo | null>(`/drafts/emails/${emailId}/preview`)
}

export function getDraftPreviews(params: { limit?: number; offset?: number } = {}) {
  return http.get<DraftPreviewListResponse>('/drafts/previews', { params: { limit: 20, ...params } })
}

export function updateDraftPreview(draftId: string, payload: MailEditorState) {
  return http.put<DraftPreviewInfo>(`/drafts/previews/${draftId}`, payload)
}

export function reviseDraftPreview(
  draftId: string,
  payload: MailEditorState & { instruction: string },
) {
  return http.post<DraftPreviewInfo>(`/drafts/previews/${draftId}/revise`, payload)
}

export function createSendActionForDraft(draftId: string) {
  return http.post<CreateSendActionResponse>(`/drafts/previews/${draftId}/send-action`)
}

export function deleteDraftPreview(draftId: string) {
  return http.delete<DeleteDraftPreviewResponse>(`/drafts/previews/${draftId}`)
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
