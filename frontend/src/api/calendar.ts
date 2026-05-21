import { http } from './http'
import type {
  CalendarEventsResponse,
  CalendarEventInfo,
  CalendarEventMutationRequest,
  CalendarSuggestionInfo,
  CreateCalendarPendingActionRequest,
  CreateCalendarPendingActionResponse,
  DeleteCalendarEventPendingRequest,
  SuggestSlotsRequest,
  SuggestSlotsResponse,
} from '@/types/calendar'

export function getCalendarEvents(range: 'today' | 'week' = 'week') {
  return http.get<CalendarEventsResponse>('/calendar/events', { params: { range } })
}

export function getCalendarEventDetail(eventId: string) {
  return http.get<CalendarEventInfo>(`/calendar/events/${eventId}`)
}

export function createManualCalendarEventAction(payload: CalendarEventMutationRequest) {
  return http.post<CreateCalendarPendingActionResponse>('/calendar/events/pending', payload)
}

export function createUpdateCalendarEventAction(eventId: string, payload: CalendarEventMutationRequest) {
  return http.post<CreateCalendarPendingActionResponse>(`/calendar/events/${eventId}/update-pending`, payload)
}

export function createDeleteCalendarEventAction(eventId: string, payload: DeleteCalendarEventPendingRequest) {
  return http.post<CreateCalendarPendingActionResponse>(`/calendar/events/${eventId}/delete-pending`, payload)
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
