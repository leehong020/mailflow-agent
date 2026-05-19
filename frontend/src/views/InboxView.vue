<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Inbox Triage</h2>
        <p>同步 Gmail 后，由 Email Summarizer / Triage / Task Extraction Agent 输出结构化分析。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="loading" @click="loadEmails">刷新看板</el-button>
        <el-button type="primary" :loading="analyzing" @click="handleAnalyze">同步并分析邮件</el-button>
      </div>
    </div>

    <el-alert
      v-if="message"
      :title="message"
      type="success"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="triage-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="triage-tab"
        :class="{ active: activeTab === tab.key }"
        @click="selectTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="emails.length" class="email-list">
      <article v-for="email in emails" :key="email.id" class="email-card" @click="openDetail(email.id)">
        <div class="email-card-head">
          <div class="email-card-title-wrap">
            <h3>{{ email.subject }}</h3>
            <span class="email-card-sender">{{ email.sender }}</span>
          </div>
          <time>{{ formatTime(email.received_at) }}</time>
        </div>
        <div class="tag-row">
          <el-tag size="small" :type="categoryTagType(email.analysis?.category)">
            {{ categoryLabel(email.analysis?.category) }}
          </el-tag>
          <el-tag size="small" :type="priorityTagType(email.analysis?.priority)" effect="plain">
            {{ priorityLabel(email.analysis?.priority) }}
          </el-tag>
          <el-tag v-if="email.analysis?.need_reply" size="small" type="warning" effect="plain">
            需要回复
          </el-tag>
          <el-tag v-if="email.analysis?.has_meeting_request" size="small" type="success" effect="plain">
            会议相关
          </el-tag>
          <el-tag v-if="email.analysis?.has_task" size="small" type="danger" effect="plain">
            有待办
          </el-tag>
        </div>
        <p class="email-preview">{{ email.analysis?.summary || email.snippet || email.body_preview || '暂无预览内容' }}</p>
      </article>
    </div>

    <div v-else-if="!loading" class="empty-block">
      <h3>还没有分析结果</h3>
      <p>请先在 Settings 连接 Google 账号，然后点击“同步并分析邮件”。</p>
      <el-button @click="router.push('/settings')">前往 Settings</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { analyzeEmails, getRecentEmails } from '@/api/emails'
import type { EmailListItem } from '@/types/email'

const router = useRouter()
const loading = ref(false)
const analyzing = ref(false)
const error = ref('')
const message = ref('')
const emails = ref<EmailListItem[]>([])
const activeTab = ref('all')

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'high', label: '高优先级' },
  { key: 'reply', label: '需要回复' },
  { key: 'calendar_related', label: '会议相关' },
  { key: 'task_required', label: '待办事项' },
  { key: 'notification', label: '通知类' },
  { key: 'ignore', label: '可忽略' },
]

async function loadEmails() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getRecentEmails(queryByTab())
    emails.value = data.items
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取邮件看板失败，请检查 Google 授权状态。'
  } finally {
    loading.value = false
  }
}

async function handleAnalyze() {
  analyzing.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await analyzeEmails(20)
    message.value = data.message
    await loadEmails()
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '邮件分析失败，请检查 Gmail 权限。'
  } finally {
    analyzing.value = false
  }
}

function queryByTab() {
  if (activeTab.value === 'high') return { priority: 'high' }
  if (activeTab.value === 'reply') return { need_reply: true }
  if (activeTab.value === 'calendar_related') return { category: 'calendar_related' }
  if (activeTab.value === 'task_required') return { has_task: true }
  if (activeTab.value === 'notification') return { category: 'notification' }
  if (activeTab.value === 'ignore') return { category: 'ignore' }
  return {}
}

async function selectTab(tab: string) {
  activeTab.value = tab
  await loadEmails()
}

function openDetail(id: string) {
  router.push(`/emails/${id}`)
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

function categoryLabel(value?: string) {
  const labels: Record<string, string> = {
    urgent_reply: '紧急回复',
    normal_reply: '普通回复',
    calendar_related: '会议相关',
    task_required: '待办事项',
    newsletter: '订阅邮件',
    notification: '通知类',
    ignore: '可忽略',
  }
  return labels[value || ''] ?? '未分析'
}

function priorityLabel(value?: string) {
  const labels: Record<string, string> = { high: '高优先级', medium: '中优先级', low: '低优先级' }
  return labels[value || ''] ?? '未判断'
}

function categoryTagType(value?: string) {
  if (value === 'urgent_reply') return 'danger'
  if (value === 'calendar_related') return 'success'
  if (value === 'task_required') return 'warning'
  return 'info'
}

function priorityTagType(value?: string) {
  if (value === 'high') return 'danger'
  if (value === 'medium') return 'warning'
  return 'info'
}

onMounted(loadEmails)
</script>
