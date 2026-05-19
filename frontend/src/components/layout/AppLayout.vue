<template>
  <div class="app-shell">
    <AppSidebar />
    <main class="main-panel">
      <!-- Header 是全局共享区域，页面内容由 RouterView 渲染。 -->
      <AppHeader :title="routeTitle" :connected="connected" />
      <section class="page-body">
        <!-- Settings 连接/断开 Google 后，会通知布局刷新顶部状态。 -->
        <RouterView @google-status-change="loadGoogleStatus" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getGoogleStatus } from '@/api/auth'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'

const route = useRoute()
const connected = ref(false)

// 根据当前路由名生成页面标题。
const routeTitle = computed(() => {
  if (route.name === 'inbox') return 'Gmail Inbox'
  if (route.name === 'email-detail') return 'Email Detail'
  if (route.name === 'traces') return 'Agent Trace'
  if (route.name === 'settings') return 'Settings'
  return 'Dashboard'
})

async function loadGoogleStatus() {
  // 后端不可用时不阻塞页面渲染，只把状态显示为未连接。
  try {
    const { data } = await getGoogleStatus()
    connected.value = data.connected
  } catch {
    connected.value = false
  }
}

onMounted(loadGoogleStatus)
</script>
