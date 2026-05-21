<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Settings</h2>
        <p>这里管理 Google 连接状态和本地授权信息。</p>
      </div>
      <el-button :loading="loading" @click="loadStatus">刷新状态</el-button>
    </div>

    <div class="settings-panel">
      <div v-if="status?.connected" class="account-row">
        <el-avatar :src="status.picture || undefined" :size="56">{{ avatarText }}</el-avatar>
        <div class="account-main">
          <strong>{{ status.name || status.email }}</strong>
          <span>{{ status.email }}</span>
          <small>已授权 {{ status.scopes.length }} 个 scope</small>
        </div>
        <el-button type="danger" plain @click="handleDisconnect">断开连接</el-button>
      </div>
      <div v-else class="empty-block">
        <h3>尚未连接 Google 账号</h3>
        <p>请先完成 OAuth 授权，随后 Inbox 页面即可展示 Gmail 最近邮件。</p>
        <el-button type="primary" @click="redirectToGoogleLogin">连接 Google 账号</el-button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { disconnectGoogle, getGoogleStatus, redirectToGoogleLogin } from '@/api/auth'
import type { GoogleConnectionStatus } from '@/types/auth'

const emit = defineEmits<{ 'google-status-change': [] }>()

const loading = ref(false)
const status = ref<GoogleConnectionStatus | null>(null)
const avatarText = computed(() => status.value?.email?.slice(0, 1).toUpperCase() ?? 'G')

async function loadStatus() {
  loading.value = true
  try {
    const { data } = await getGoogleStatus()
    status.value = data
    emit('google-status-change')
  } finally {
    loading.value = false
  }
}

async function handleDisconnect() {
  await disconnectGoogle()
  ElMessage.success('已断开本地 Google 连接')
  await loadStatus()
}

onMounted(async () => {
  await loadStatus()
})
</script>
