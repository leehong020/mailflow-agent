<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Pending Actions</h2>
        <p>所有需要用户确认的外部操作都会在这里展示，确认后才真正执行。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="loading" @click="loadActions">刷新列表</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />

    <div v-if="actions.length" class="email-list">
      <article v-for="action in actions" :key="action.id" class="email-card">
        <div class="email-card-head">
          <div class="email-card-title-wrap">
            <h3>{{ action.action_type }}</h3>
            <span class="email-card-sender">风险等级：{{ action.risk_level }}</span>
          </div>
          <time>{{ formatTime(action.created_at) }}</time>
        </div>
        <div class="analysis-block">
          <strong>预览</strong>
          <p>{{ stringify(action.preview) }}</p>
        </div>
        <div class="toolbar-actions">
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

import { confirmPendingAction, getPendingActions, rejectPendingAction } from '@/api/drafts'
import type { PendingActionInfo } from '@/types/draft'

const loading = ref(false)
const error = ref('')
const actions = ref<PendingActionInfo[]>([])
const confirmingId = ref('')
const rejectingId = ref('')

async function loadActions() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getPendingActions({ limit: 20 })
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
    await confirmPendingAction(actionId)
    await loadActions()
  } finally {
    confirmingId.value = ''
  }
}

async function reject(actionId: string) {
  rejectingId.value = actionId
  try {
    await rejectPendingAction(actionId)
    await loadActions()
  } finally {
    rejectingId.value = ''
  }
}

function stringify(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2)
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
