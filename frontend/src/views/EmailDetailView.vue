<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>邮件详情分析</h2>
        <p>左侧展示原始邮件，右侧展示第三阶段 Agent 分析结果。</p>
      </div>
      <div class="toolbar-actions">
        <EmailOperationBar v-if="email" :email="email" @updated="applyEmailUpdate" @pending="showMessage" @error="showError" />
        <el-button v-if="email?.analysis?.has_meeting_request" type="primary" @click="handleScheduleMeeting">
          查找会议时间
        </el-button>
        <el-button :loading="drafting" @click="handleCreateDraft">AI 回复</el-button>
        <el-button :loading="forwarding" @click="handleForwardDraft">转发邮件</el-button>
        <el-button :loading="reanalyzing" @click="handleReanalyze">重新分析</el-button>
        <el-button @click="router.push('/inbox')">返回 Inbox</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div v-if="email" class="detail-grid">
      <section class="detail-panel">
        <h3>{{ email.subject }}</h3>
        <div class="meta-list">
          <span>发件人：{{ email.sender }}</span>
          <span>收件时间：{{ formatTime(email.received_at) }}</span>
          <span>收件人：{{ email.recipients.join(', ') || '无' }}</span>
          <span>状态：{{ email.is_read ? '已读' : '未读' }} / {{ email.is_starred ? '星标' : '未星标' }} / {{ mailboxLabel(email.mailbox_status) }}</span>
        </div>
        <div class="email-body">{{ email.body_text || email.snippet || '暂无正文内容' }}</div>
      </section>

      <section class="detail-panel analysis-panel">
        <h3>Agent 分析结果</h3>
        <template v-if="email.analysis">
          <div class="tag-row">
            <el-tag :type="categoryTagType(email.analysis.category)">{{ categoryLabel(email.analysis.category) }}</el-tag>
            <el-tag :type="priorityTagType(email.analysis.priority)" effect="plain">{{ priorityLabel(email.analysis.priority) }}</el-tag>
            <el-tag v-if="email.analysis.need_reply" type="warning" effect="plain">需要回复</el-tag>
            <el-tag v-if="email.analysis.has_meeting_request" type="success" effect="plain">会议相关</el-tag>
            <el-tag v-if="email.analysis.has_task" type="danger" effect="plain">有待办</el-tag>
          </div>

          <div class="analysis-block">
            <strong>摘要</strong>
            <p>{{ email.analysis.summary }}</p>
          </div>

          <div class="analysis-block">
            <strong>关键点</strong>
            <ul>
              <li v-for="point in email.analysis.key_points" :key="point">{{ point }}</li>
              <li v-if="!email.analysis.key_points.length">暂无关键点</li>
            </ul>
          </div>

          <div class="analysis-block">
            <strong>分类理由</strong>
            <p>{{ email.analysis.reason }}</p>
          </div>

          <div class="analysis-block">
            <strong>推荐操作</strong>
            <div class="tag-row">
              <el-tag v-for="action in email.analysis.recommended_actions" :key="action" effect="plain">{{ action }}</el-tag>
            </div>
          </div>

          <div class="analysis-block">
            <strong>识别出的任务</strong>
            <div v-if="email.tasks.length" class="task-list">
              <div v-for="task in email.tasks" :key="task.id" class="task-item">
                <span>{{ task.title }}</span>
                <small>{{ task.deadline ? `截止：${task.deadline}` : '未识别截止时间' }}</small>
              </div>
            </div>
            <p v-else>未识别出待办任务。</p>
          </div>
        </template>

        <div v-else class="empty-block compact">
          <h3>尚未分析</h3>
          <p>请回到 Inbox 点击“同步并分析邮件”。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import EmailOperationBar from '@/components/EmailOperationBar.vue'
import { createDraftPreview } from '@/api/drafts'
import { getEmailDetail, reanalyzeEmail } from '@/api/emails'
import type { EmailDetail } from '@/types/email'

const route = useRoute()
const router = useRouter()
const email = ref<EmailDetail | null>(null)
const error = ref('')
const message = ref('')
const reanalyzing = ref(false)
const drafting = ref(false)
const forwarding = ref(false)

async function loadDetail() {
  try {
    const { data } = await getEmailDetail(String(route.params.id))
    email.value = data
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取邮件详情失败。'
  }
}

async function handleReanalyze() {
  reanalyzing.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await reanalyzeEmail(String(route.params.id))
    message.value = data.message
    await loadDetail()
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '重新分析失败。'
  } finally {
    reanalyzing.value = false
  }
}

async function handleCreateDraft() {
  drafting.value = true
  error.value = ''
  message.value = ''
  try {
    router.push({ path: '/reply-workspace', query: { email: String(route.params.id) } })
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '打开 AI 回复工作台失败。'
  } finally {
    drafting.value = false
  }
}

async function handleForwardDraft() {
  forwarding.value = true
  error.value = ''
  message.value = ''
  try {
    const { data } = await createDraftPreview(String(route.params.id), { tone: 'friendly', language: 'auto' })
    message.value = `已生成转发草稿：${data.subject}`
    router.push({ path: '/drafts', query: { preview: data.draft_preview_id } })
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '生成转发草稿失败。'
  } finally {
    forwarding.value = false
  }
}

function handleScheduleMeeting() {
  if (!email.value) return
  router.push({ path: '/calendar', query: { email: email.value.id } })
}

function applyEmailUpdate(updated: any) {
  if (!email.value) return
  email.value = { ...email.value, ...updated, body_text: email.value.body_text, tasks: email.value.tasks }
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
    year: 'numeric',
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

onMounted(loadDetail)
</script>
