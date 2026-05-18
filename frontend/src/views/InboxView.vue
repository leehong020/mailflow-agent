<template>
  <div class="stack">
    <!-- Inbox 页面是第二阶段验收重点：读取并展示 Gmail 最近邮件。 -->
    <div class="section-header">
      <div>
        <h2>最近邮件</h2>
        <p>来自 Gmail Inbox 的最新邮件，当前阶段展示原始邮件列表。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="loadEmails">同步邮件</el-button>
    </div>

    <!-- 未授权、OAuth 过期或 Gmail API 错误都会在这里展示给用户。 -->
    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <!-- 邮件列表当前展示原始 Gmail 数据，第三阶段再加入 Agent 分类和摘要。 -->
    <div v-if="emails.length" class="email-list">
      <article v-for="email in emails" :key="email.id" class="email-card">
        <div class="email-card-head">
          <div>
            <h3>{{ email.subject }}</h3>
            <span>{{ email.sender }}</span>
          </div>
          <time>{{ formatTime(email.received_at) }}</time>
        </div>
        <p>{{ email.snippet || email.body_preview || '暂无预览内容' }}</p>
      </article>
    </div>

    <div v-else-if="!loading" class="empty-block">
      <h3>还没有邮件数据</h3>
      <p>请先在 Settings 连接 Google 账号，然后点击同步邮件。</p>
      <el-button @click="router.push('/settings')">前往 Settings</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getRecentEmails } from '@/api/emails'
import type { EmailListItem } from '@/types/email'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const emails = ref<EmailListItem[]>([])

async function loadEmails() {
  // 调用后端 /emails，后端会用保存的 Google token 访问 Gmail API。
  loading.value = true
  error.value = ''
  try {
    const { data } = await getRecentEmails(20)
    emails.value = data.items
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取 Gmail 邮件失败，请检查 Google 授权状态。'
  } finally {
    loading.value = false
  }
}

function formatTime(value?: string | null) {
  // 后端返回 ISO 时间，前端转成中文本地时间展示。
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(loadEmails)
</script>
