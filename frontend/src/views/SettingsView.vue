<template>
  <div class="stack">
    <!-- Settings 页面负责 Google OAuth 的入口和连接状态展示。 -->
    <div class="section-header">
      <div>
        <h2>Google 连接</h2>
        <p>用于授权 Gmail 只读权限，系统会读取最近 Inbox 邮件。</p>
      </div>
      <el-button :loading="loading" @click="loadStatus">刷新状态</el-button>
    </div>

    <div class="settings-panel">
      <!-- 已连接时展示 Google 用户信息，并提供断开本地连接按钮。 -->
      <div v-if="status?.connected" class="account-row">
        <el-avatar :src="status.picture || undefined" :size="56">{{ avatarText }}</el-avatar>
        <div class="account-main">
          <strong>{{ status.name || status.email }}</strong>
          <span>{{ status.email }}</span>
          <small>已授权 {{ status.scopes.length }} 个 scope</small>
        </div>
        <el-button type="danger" plain @click="handleDisconnect">断开连接</el-button>
      </div>

      <!-- 未连接时展示 OAuth 登录入口。 -->
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

const emit = defineEmits<{
  'google-status-change': []
}>()

const loading = ref(false)
const status = ref<GoogleConnectionStatus | null>(null)
const avatarText = computed(() => status.value?.email?.slice(0, 1).toUpperCase() ?? 'G')

async function loadStatus() {
  // 查询后端状态，并通知全局布局刷新顶部连接标签。
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
  // 只删除本地 token，不会调用 Gmail 删除或修改任何内容。
  await disconnectGoogle()
  ElMessage.success('已断开本地 Google 连接')
  await loadStatus()
}

onMounted(loadStatus)
</script>
