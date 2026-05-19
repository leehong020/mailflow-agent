import { http } from './http'
import type {
  CalendarEventsResponse,
  CalendarSuggestionInfo,
  CreateCalendarPendingActionRequest,
  CreateCalendarPendingActionResponse,
  SuggestSlotsRequest,
  SuggestSlotsResponse,
} from '@/types/calendar'

export function getCalendarEvents(range: 'today' | 'week' = 'week') {
  return http.get<CalendarEventsResponse>('/calendar/events', { params: { range } })
}

export function getCalendarSuggestions(params: { limit?: number; offset?: number } = {}) {
  return http.get<CalendarSuggestionInfo[]>('/calendar/suggestions', { params: { limit: 20, ...params } })
}

export function suggestCalendarSlots(payload: SuggestSlotsRequest) {
  return http.post<SuggestSlotsResponse>('/calendar/suggest-slots', payload)
}

export function createPendingCalendarAction(suggestionId: string, payload: CreateCalendarPendingActionRequest) {
  return http.post<CreateCalendarPendingActionResponse>(`/calendar/suggestions/${suggestionId}/pending`, payload)
}
