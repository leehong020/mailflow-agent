<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Inbox Triage</h2>
        <p>同步 Gmail 后，由 Email Summarizer / Triage / Task Extraction Agent 输出结构化分析。</p>
      </div>
      <div class="toolbar-actions">
        <el-input v-model="search" class="inbox-search" placeholder="搜索主题、发件人或正文" clearable @keyup.enter="loadEmails" />
        <el-select v-model="mailboxStatus" class="trace-filter" @change="loadEmails">
          <el-option label="Inbox" value="inbox" />
          <el-option label="已归档" value="archived" />
          <el-option label="垃圾箱" value="trash" />
          <el-option label="全部状态" value="" />
        </el-select>
        <el-button :loading="loading || syncing" @click="handleRefreshBoard">刷新看板</el-button>
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

    <div class="inbox-status-row">
      <span>当前筛选：{{ activeTabLabel }}</span>
      <span>匹配 {{ total }} 封</span>
      <span>已分析 {{ analyzedTotal }} 封</span>
      <span>未分析 {{ unanalyzedTotal }} 封</span>
      <span>已选择 {{ selectedEmailIds.length }} 封</span>
      <el-button size="small" :disabled="!selectedEmailIds.length" @click="handleBatch('archive')">批量归档</el-button>
      <el-button size="small" :disabled="!selectedEmailIds.length" @click="handleBatch('mark_read')">批量已读</el-button>
      <el-button size="small" type="danger" plain :disabled="!selectedEmailIds.length" @click="handleBatch('trash')">批量垃圾箱</el-button>
    </div>

    <div v-if="emails.length" class="email-list">
      <article v-for="email in emails" :key="email.id" class="email-card" @click="openDetail(email.id)">
        <div class="email-card-head">
          <el-checkbox
            :model-value="selectedEmailIds.includes(email.id)"
            @click.stop
            @change="toggleSelection(email.id)"
          />
          <div class="email-card-title-wrap">
            <h3 :class="{ unread: !email.is_read }">{{ email.subject }}</h3>
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
          <el-tag v-if="email.is_starred" size="small" type="warning" effect="plain">
            星标
          </el-tag>
          <el-tag size="small" effect="plain">
            {{ mailboxLabel(email.mailbox_status) }}
          </el-tag>
        </div>
        <p class="email-preview">{{ email.analysis?.summary || email.snippet || email.body_preview || '暂无预览内容' }}</p>
        <div class="email-card-actions">
          <EmailOperationBar :email="email" @updated="replaceEmail" @pending="showMessage" @error="showError" />
          <el-button v-if="email.analysis?.has_meeting_request" size="small" @click.stop="router.push({ path: '/calendar', query: { email: email.id } })">
            查找会议时间
          </el-button>
          <el-button v-if="email.analysis?.need_reply" size="small" @click.stop="router.push(`/emails/${email.id}`)">
            生成草稿
          </el-button>
        </div>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import EmailOperationBar from '@/components/EmailOperationBar.vue'
import { analyzeEmails, createBatchEmailAction, getRecentEmails, syncEmails } from '@/api/emails'
import type { EmailListItem } from '@/types/email'

const router = useRouter()
const loading = ref(false)
const syncing = ref(false)
const analyzing = ref(false)
const error = ref('')
const message = ref('')
const emails = ref<EmailListItem[]>([])
const activeTab = ref('all')
const search = ref('')
const total = ref(0)
const analyzedTotal = ref(0)
const unanalyzedTotal = ref(0)
const mailboxStatus = ref('inbox')
const selectedEmailIds = ref<string[]>([])

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
    total.value = data.total
    analyzedTotal.value = data.analyzed_total
    unanalyzedTotal.value = data.unanalyzed_total
    selectedEmailIds.value = selectedEmailIds.value.filter((id) => data.items.some((item) => item.id === id))
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取邮件看板失败，请检查 Google 授权状态。'
  } finally {
    loading.value = false
  }
}

async function handleRefreshBoard() {
  syncing.value = true
  error.value = ''
  message.value = ''
  try {
    // 刷新看板时先同步 Gmail，再读取本地列表。
    // 这里不调用分析接口，避免用户只是想看新邮件时也消耗大模型 token。
    const { data } = await syncEmails(20)
    message.value = data.message
    await loadEmails()
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '同步 Gmail 邮件失败，请检查 Google 授权状态。'
  } finally {
    syncing.value = false
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
  const base = {
    ...(search.value ? { search: search.value } : {}),
    ...(mailboxStatus.value ? { mailbox_status: mailboxStatus.value } : {}),
  }
  if (activeTab.value === 'high') return { ...base, priority: 'high' }
  if (activeTab.value === 'reply') return { ...base, need_reply: true }
  if (activeTab.value === 'calendar_related') return { ...base, category: 'calendar_related' }
  if (activeTab.value === 'task_required') return { ...base, has_task: true }
  if (activeTab.value === 'notification') return { ...base, category: 'notification' }
  if (activeTab.value === 'ignore') return { ...base, category: 'ignore' }
  return base
}

const activeTabLabel = computed(() => tabs.find((item) => item.key === activeTab.value)?.label ?? '全部')

async function selectTab(tab: string) {
  activeTab.value = tab
  await loadEmails()
}

function openDetail(id: string) {
  router.push(`/emails/${id}`)
}

function toggleSelection(id: string) {
  if (selectedEmailIds.value.includes(id)) {
    selectedEmailIds.value = selectedEmailIds.value.filter((item) => item !== id)
    return
  }
  selectedEmailIds.value = [...selectedEmailIds.value, id]
}

async function handleBatch(operation: string) {
  if (!selectedEmailIds.value.length) return
  try {
    const { data } = await createBatchEmailAction({ email_ids: selectedEmailIds.value, operation })
    message.value = data.message
    selectedEmailIds.value = []
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建批量操作失败。'
  }
}

function replaceEmail(updated: EmailListItem) {
  emails.value = emails.value.map((item) => (item.id === updated.id ? updated : item))
}

function showMessage(value: string) {
  message.value = value
}

function showError(value: string) {
  error.value = value
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

function mailboxLabel(value: string) {
  const labels: Record<string, string> = { inbox: 'Inbox', archived: '已归档', trash: '垃圾箱' }
  return labels[value] ?? value
}

// 进入 Inbox 时只读取本地数据库，让之前已经同步/分析过的邮件立即显示。
// Gmail API 同步放到“刷新看板”按钮里手动触发，避免每次进页面都被网络请求卡住。
onMounted(loadEmails)
</script>
