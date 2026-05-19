<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Calendar Planner</h2>
        <p>展示 Google Calendar 日程，并从会议邮件生成可用时间建议。</p>
      </div>
      <div class="toolbar-actions">
        <el-input v-model="emailId" class="calendar-email-input" placeholder="邮件 ID" clearable />
        <el-input-number v-model="durationMinutes" :min="15" :max="240" :step="15" />
        <el-button :loading="suggesting" type="primary" @click="handleSuggest">生成日程建议</el-button>
        <el-button :loading="loadingEvents" @click="loadEvents">刷新日历</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div class="calendar-planner-layout">
      <section class="calendar-main-panel">
        <FullCalendar :options="calendarOptions" />
      </section>

      <aside class="calendar-side-panel">
        <div class="calendar-side-section">
          <h3>会议请求</h3>
          <div v-if="currentSuggestion" class="meeting-request-card">
            <strong>{{ currentSuggestion.meeting_title }}</strong>
            <span>时长：{{ currentSuggestion.duration_minutes }} 分钟</span>
            <span>时区：{{ currentSuggestion.timezone }}</span>
            <span>参会人：{{ currentSuggestion.participants.join(', ') || '未识别' }}</span>
            <p>{{ currentSuggestion.description || '暂无会议说明。' }}</p>
          </div>
          <div v-else class="empty-block compact">
            <h3>暂无会议建议</h3>
            <p>从邮件详情页点击“查找会议时间”，或在上方输入邮件 ID。</p>
          </div>
        </div>

        <div class="calendar-side-section">
          <h3>推荐时间段</h3>
          <div v-if="currentSuggestion?.suggested_slots.length" class="slot-list">
            <button
              v-for="slot in currentSuggestion.suggested_slots"
              :key="`${slot.start}-${slot.end}`"
              class="slot-item"
              :class="{ active: selectedSlot?.start === slot.start }"
              @click="selectedSlot = slot"
            >
              <strong>{{ formatRange(slot.start, slot.end) }}</strong>
              <span>{{ slot.reason }}</span>
            </button>
          </div>
          <p v-else class="muted-text">暂无可用时间段。</p>
        </div>

        <div class="calendar-side-section">
          <h3>创建事件预览</h3>
          <template v-if="currentSuggestion && selectedSlot">
            <div class="event-preview">
              <span>标题：{{ currentSuggestion.meeting_title }}</span>
              <span>时间：{{ formatRange(selectedSlot.start, selectedSlot.end) }}</span>
              <span>地点：{{ currentSuggestion.location || '未设置' }}</span>
              <span>参会人：{{ currentSuggestion.participants.join(', ') || '未识别' }}</span>
            </div>
            <el-button type="primary" :loading="creatingPending" @click="handleCreatePending">
              加入待确认操作
            </el-button>
          </template>
          <p v-else class="muted-text">选择一个推荐时间段后会显示创建预览。</p>
        </div>

        <div class="calendar-side-section">
          <h3>历史建议</h3>
          <div v-if="suggestions.length" class="suggestion-history">
            <button
              v-for="item in suggestions"
              :key="item.id"
              class="history-item"
              :class="{ active: currentSuggestion?.id === item.id }"
              @click="selectSuggestion(item)"
            >
              <strong>{{ item.meeting_title }}</strong>
              <span>{{ formatTime(item.created_at) }} · {{ item.status }}</span>
            </button>
          </div>
          <p v-else class="muted-text">暂无历史建议。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import timeGridPlugin from '@fullcalendar/timegrid'

import {
  createPendingCalendarAction,
  getCalendarEvents,
  getCalendarSuggestions,
  suggestCalendarSlots,
} from '@/api/calendar'
import type { CalendarEventInfo, CalendarSlotInfo, CalendarSuggestionInfo } from '@/types/calendar'

const route = useRoute()
const router = useRouter()
const events = ref<CalendarEventInfo[]>([])
const suggestions = ref<CalendarSuggestionInfo[]>([])
const currentSuggestion = ref<CalendarSuggestionInfo | null>(null)
const selectedSlot = ref<CalendarSlotInfo | null>(null)
const emailId = ref(String(route.query.email || ''))
const durationMinutes = ref(30)
const loadingEvents = ref(false)
const suggesting = ref(false)
const creatingPending = ref(false)
const error = ref('')
const message = ref('')

// FullCalendar 的配置统一放在 computed 中，事件刷新后视图会自动更新。
const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  height: 'auto',
  nowIndicator: true,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },
  events: events.value.map((item) => ({
    id: item.id,
    title: item.summary,
    start: item.start,
    end: item.end,
  })),
}))

async function loadEvents() {
  loadingEvents.value = true
  error.value = ''
  try {
    const { data } = await getCalendarEvents('week')
    events.value = data.items
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取 Google Calendar 日程失败。'
  } finally {
    loadingEvents.value = false
  }
}

async function loadSuggestions() {
  try {
    const { data } = await getCalendarSuggestions()
    suggestions.value = data
    if (!currentSuggestion.value && data.length) {
      selectSuggestion(data[0])
    }
  } catch {
    // 历史建议加载失败不阻断日历主流程。
  }
}

async function handleSuggest() {
  if (!emailId.value) {
    error.value = '请先输入会议邮件 ID，或从邮件详情页进入 Calendar Planner。'
    return
  }
  suggesting.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await suggestCalendarSlots({
      email_id: emailId.value,
      duration_minutes: durationMinutes.value,
    })
    currentSuggestion.value = data.suggestion
    selectedSlot.value = data.suggestion.suggested_slots[0] ?? null
    message.value = `已生成 ${data.suggestion.suggested_slots.length} 个可用时间段。`
    await loadSuggestions()
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '生成日程建议失败。'
  } finally {
    suggesting.value = false
  }
}

async function handleCreatePending() {
  if (!currentSuggestion.value || !selectedSlot.value) return
  creatingPending.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await createPendingCalendarAction(currentSuggestion.value.id, {
      selected_slot: selectedSlot.value,
    })
    message.value = data.message
    router.push('/pending-actions')
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建待确认日程操作失败。'
  } finally {
    creatingPending.value = false
  }
}

function selectSuggestion(item: CalendarSuggestionInfo) {
  currentSuggestion.value = item
  selectedSlot.value = item.selected_slot ?? item.suggested_slots[0] ?? null
  emailId.value = item.source_email_id
}

function formatTime(value?: string | null) {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatRange(start: string, end: string) {
  return `${formatTime(start)} - ${formatTime(end)}`
}

onMounted(async () => {
  await loadEvents()
  await loadSuggestions()
  if (emailId.value) {
    await handleSuggest()
  }
})
</script>
