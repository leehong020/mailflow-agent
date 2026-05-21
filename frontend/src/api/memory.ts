import { http } from './http'
import type { ComposeMessageInfo, ComposeMessageRequest, ComposeSessionInfo, CreateComposeSessionRequest, UpdateComposeSessionRequest } from '@/types/memory'

export function createComposeSession(payload: CreateComposeSessionRequest) {
  return http.post<ComposeSessionInfo>('/memory/sessions', payload)
}

export function getComposeSessions() {
  return http.get<ComposeSessionInfo[]>('/memory/sessions')
}

export function getComposeSession(sessionId: string) {
  return http.get<ComposeSessionInfo>(`/memory/sessions/${sessionId}`)
}

export function updateComposeSession(sessionId: string, payload: UpdateComposeSessionRequest) {
  return http.patch<ComposeSessionInfo>(`/memory/sessions/${sessionId}`, payload)
}

export function addComposeMessage(sessionId: string, role: 'user' | 'assistant' | 'system', content: string) {
  return http.post(`/memory/sessions/${sessionId}/messages`, { role, content })
}

export function getDraftMemorySession(draftPreviewId: string, sessionType: 'compose' | 'reply') {
  return http.get<ComposeSessionInfo>(`/memory/drafts/${draftPreviewId}/session`, {
    params: { session_type: sessionType },
  })
}

export function addDraftMemoryMessage(
  draftPreviewId: string,
  sessionType: 'compose' | 'reply',
  payload: ComposeMessageRequest,
) {
  return http.post<ComposeMessageInfo>(`/memory/drafts/${draftPreviewId}/messages`, payload, {
    params: { session_type: sessionType },
  })
}
