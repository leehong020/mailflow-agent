<template>
  <div class="stack">
    <!-- Dashboard 是第一阶段验收入口，先展示空工作台和基础统计。 -->
    <div class="section-header">
      <div>
        <h2>办公状态概览</h2>
        <p>第一阶段先展示基础工作台，邮件分析统计会在第三阶段接入 Agent 后填充。</p>
      </div>
      <el-button type="primary" @click="router.push('/settings')">连接 Google</el-button>
    </div>

    <div class="stats-grid">
      <div v-for="item in stats" :key="item.label" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <div class="content-band">
      <h3>当前阶段</h3>
      <p>
        已完成基础布局、路由、后端健康检查、Google OAuth 连接入口和 Gmail 最近邮件读取接口。
      </p>
      <el-button @click="router.push('/inbox')">查看 Inbox</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getDashboardSummary } from '@/api/dashboard'
import type { DashboardSummary } from '@/types/dashboard'

const router = useRouter()
const summary = ref<DashboardSummary | null>(null)

// 把后端统计结果转换成卡片数组，模板可以直接循环渲染。
const stats = computed(() => [
  { label: 'Google 连接', value: summary.value?.google_connected ? '已连接' : '未连接' },
  { label: '今日邮件', value: summary.value?.email_count_today ?? 0 },
  { label: '高优先级', value: summary.value?.high_priority_count ?? 0 },
  { label: '待确认操作', value: summary.value?.pending_action_count ?? 0 },
])

onMounted(async () => {
  // 页面加载时读取一次 Dashboard 汇总数据。
  const { data } = await getDashboardSummary()
  summary.value = data
})
</script>
