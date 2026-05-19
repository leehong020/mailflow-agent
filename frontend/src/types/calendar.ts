export interface CalendarEventInfo {
  id: string
  summary: string
  start: string
  end: string
  location: string
  description: string
  html_link: string
  attendees: string[]
}

export interface CalendarEventsResponse {
  items: CalendarEventInfo[]
  total: number
}

export interface CalendarSlotInfo {
  start: string
  end: string
  reason: string
}

export interface CalendarSuggestionInfo {
  id: string
  source_email_id: string
  meeting_title: string
  description: string
  location: string
  timezone: string
  duration_minutes: number
  participants: string[]
  suggested_slots: CalendarSlotInfo[]
  selected_slot?: CalendarSlotInfo | null
  status: string
  created_at?: string | null
}

export interface SuggestSlotsRequest {
  email_id: string
  duration_minutes: number
}

export interface SuggestSlotsResponse {
  suggestion: CalendarSuggestionInfo
}

export interface CreateCalendarPendingActionRequest {
  selected_slot: CalendarSlotInfo
}

export interface CreateCalendarPendingActionResponse {
  action_id: string
  status: string
  message: string
}
