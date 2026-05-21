<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Pending Actions</h2>
        <p>所有需要用户确认的外部操作都会在这里展示，也可以查看已执行和已拒绝的历史记录。</p>
      </div>
      <div class="toolbar-actions">
        <el-select v-model="statusFilter" class="trace-filter" @change="loadActions">
          <el-option label="待确认" value="pending" />
          <el-option label="已执行" value="executed" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="失败" value="failed" />
          <el-option label="全部" value="all" />
        </el-select>
        <el-button :loading="loading" @click="loadActions">刷新列表</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />

    <div v-if="actions.length" class="email-list">
      <article v-for="action in actions" :key="action.id" class="email-card">
        <div class="email-card-head">
          <div class="email-card-title-wrap">
            <h3>{{ actionLabel(action.action_type) }}</h3>
            <span class="email-card-sender">风险等级：{{ riskLabel(action.risk_level) }}</span>
          </div>
          <time>{{ formatTime(action.created_at) }}</time>
        </div>
        <div class="analysis-block">
          <strong>预览</strong>
          <p>{{ stringify(action.preview) }}</p>
        </div>
        <div class="tag-row">
          <el-tag size="small" :type="statusTagType(action.status)" effect="plain">{{ statusLabel(action.status) }}</el-tag>
        </div>
        <div v-if="action.result" class="analysis-block">
          <strong>执行结果</strong>
          <p>{{ stringify(action.result) }}</p>
        </div>
        <div v-if="action.status === 'pending'" class="toolbar-actions">
          <el-button type="primary" :loading="confirmingId === action.id" @click="confirm(action.id)">确认</el-button>
          <el-button :loading="rejectingId === action.id" @click="reject(action.id)">拒绝</el-button>
        </div>
      </article>
    </div>

    <div v-else-if="!loading" class="empty-block">
      <h3>暂无待确认操作</h3>
      <p>当你在邮件详情页生成草稿后，这里会出现待确认项目。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { confirmAction, getActions, rejectAction } from '@/api/actions'
import type { ActionInfo } from '@/types/action'

const loading = ref(false)
const error = ref('')
const actions = ref<ActionInfo[]>([])
const confirmingId = ref('')
const rejectingId = ref('')
const statusFilter = ref('pending')

async function loadActions() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getActions({ status: statusFilter.value, limit: 20 })
    actions.value = data.items
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取待确认操作失败。'
  } finally {
    loading.value = false
  }
}

async function confirm(actionId: string) {
  confirmingId.value = actionId
  try {
    await confirmAction(actionId)
    await loadActions()
  } finally {
    confirmingId.value = ''
  }
}

async function reject(actionId: string) {
  rejectingId.value = actionId
  try {
    await rejectAction(actionId)
    await loadActions()
  } finally {
    rejectingId.value = ''
  }
}

function stringify(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2)
}

function actionLabel(value: string) {
  const labels: Record<string, string> = {
    create_gmail_draft: '创建 Gmail 草稿',
    create_calendar_event: '创建 Calendar 日程',
    modify_calendar_event: '修改 Calendar 日程',
    delete_calendar_event: '删除 Calendar 日程',
    archive_email: '归档邮件',
    trash_email: '移动到垃圾箱',
    modify_email_labels: '修改邮件标签',
    batch_email_operation: '批量邮件操作',
    send_email: '发送 Gmail 邮件',
  }
  return labels[value] ?? value
}

function riskLabel(value: string) {
  const labels: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
  }
  return labels[value] ?? value
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    pending: '待确认',
    executed: '已执行',
    rejected: '已拒绝',
    failed: '失败',
  }
  return labels[value] ?? value
}

function statusTagType(value: string) {
  if (value === 'executed') return 'success'
  if (value === 'failed') return 'danger'
  if (value === 'rejected') return 'info'
  return 'warning'
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

onMounted(loadActions)
</script>
