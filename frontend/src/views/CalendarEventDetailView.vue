<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Calendar Event Detail</h2>
        <p>查看、修改或删除 Google Calendar 日程；所有写操作都会先进入 Pending Actions。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="router.push('/calendar')">返回 Calendar</el-button>
        <el-button :loading="loading" @click="loadEvent">刷新详情</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div v-if="event" class="event-detail-layout">
      <section class="event-editor-panel">
        <h3>日程内容</h3>
        <el-form label-position="top">
          <el-form-item label="标题">
            <el-input v-model="form.summary" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="开始时间">
              <el-input v-model="form.start" placeholder="例如 2026-05-20T10:00:00+08:00" />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-input v-model="form.end" placeholder="例如 2026-05-20T10:30:00+08:00" />
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="时区">
              <el-input v-model="form.timezone" />
            </el-form-item>
            <el-form-item label="地点">
              <el-input v-model="form.location" />
            </el-form-item>
          </div>
          <el-form-item label="说明">
            <el-input v-model="form.description" type="textarea" :rows="6" />
          </el-form-item>
          <el-form-item label="参会人">
            <div class="attendee-editor">
              <el-tag
                v-for="attendee in form.attendees"
                :key="attendee"
                closable
                @close="removeAttendee(attendee)"
              >
                {{ attendee }}
              </el-tag>
              <el-input v-model="newAttendee" placeholder="输入邮箱后点击添加" @keyup.enter="addAttendee" />
              <el-button @click="addAttendee">添加</el-button>
            </div>
          </el-form-item>
        </el-form>

        <div class="toolbar-actions">
          <el-button type="primary" :loading="submittingUpdate" @click="submitUpdate">
            创建修改待确认操作
          </el-button>
          <el-button type="danger" plain :loading="submittingDelete" @click="submitDelete">
            创建删除待确认操作
          </el-button>
        </div>
      </section>

      <aside class="event-preview-panel">
        <h3>当前 Google 日程</h3>
        <div class="event-preview">
          <span>标题：{{ event.summary }}</span>
          <span>时间：{{ formatRange(event.start, event.end) }}</span>
          <span>地点：{{ event.location || '未设置' }}</span>
          <span>参会人：{{ event.attendees.join(', ') || '无' }}</span>
          <a v-if="event.html_link" :href="event.html_link" target="_blank" rel="noreferrer">在 Google Calendar 打开</a>
        </div>
        <p class="muted-text">
          修改时间会先进行冲突检测；如果目标时间段已有其他日程，后端会拒绝创建待确认操作。
        </p>
      </aside>
    </div>

    <div v-else-if="!loading" class="empty-block">
      <h3>未找到日程</h3>
      <p>请从 Calendar Planner 点击一个已有日程进入详情页。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  createDeleteCalendarEventAction,
  createUpdateCalendarEventAction,
  getCalendarEventDetail,
} from '@/api/calendar'
import type { CalendarEventInfo, CalendarEventMutationRequest } from '@/types/calendar'

const route = useRoute()
const router = useRouter()
const eventId = String(route.params.id || '')
const loading = ref(false)
const submittingUpdate = ref(false)
const submittingDelete = ref(false)
const error = ref('')
const message = ref('')
const event = ref<CalendarEventInfo | null>(null)
const newAttendee = ref('')

const form = reactive<CalendarEventMutationRequest>({
  summary: '',
  start: '',
  end: '',
  location: '',
  description: '',
  timezone: 'Asia/Shanghai',
  attendees: [],
})

async function loadEvent() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getCalendarEventDetail(eventId)
    event.value = data
    form.summary = data.summary
    form.start = data.start
    form.end = data.end
    form.location = data.location
    form.description = data.description
    form.timezone = data.timezone || 'Asia/Shanghai'
    form.attendees = [...data.attendees]
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取 Calendar 日程详情失败。'
  } finally {
    loading.value = false
  }
}

function addAttendee() {
  const value = newAttendee.value.trim()
  if (!value || !value.includes('@') || form.attendees.includes(value)) return
  form.attendees = [...form.attendees, value]
  newAttendee.value = ''
}

function removeAttendee(value: string) {
  form.attendees = form.attendees.filter((item) => item !== value)
}

async function submitUpdate() {
  submittingUpdate.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await createUpdateCalendarEventAction(eventId, { ...form })
    message.value = data.message
    router.push('/pending-actions')
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建修改日程待确认操作失败。'
  } finally {
    submittingUpdate.value = false
  }
}

async function submitDelete() {
  submittingDelete.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await createDeleteCalendarEventAction(eventId, {
      reason: '用户在 Calendar Event Detail 页面请求删除该日程。',
    })
    message.value = data.message
    router.push('/pending-actions')
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建删除日程待确认操作失败。'
  } finally {
    submittingDelete.value = false
  }
}

function formatTime(value?: string | null) {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatRange(start: string, end: string) {
  return `${formatTime(start)} - ${formatTime(end)}`
}

onMounted(loadEvent)
</script>
