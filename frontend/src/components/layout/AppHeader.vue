<template>
  <header class="app-header">
    <div>
      <p class="eyebrow">FastAPI + LangGraph + Vue</p>
      <h1>{{ title }}</h1>
    </div>
    <!-- 顶部直接展示 Google 连接状态，方便用户知道 Inbox 是否可同步。 -->
    <el-tag :type="connected ? 'success' : 'info'" effect="plain">
      {{ connected ? 'Google 已连接' : 'Google 未连接' }}
    </el-tag>
  </header>
</template>

<script setup lang="ts">
// 标题来自当前路由，connected 来自 AppLayout 调用后端状态接口。
defineProps<{
  title: string
  connected: boolean
}>()
</script>
