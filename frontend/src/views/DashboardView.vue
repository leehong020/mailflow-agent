<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>办公状态概览</h2>
        <p>汇总邮件分析、日程建议、草稿审核和待确认操作。</p>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="router.push(summary?.google_connected ? '/inbox' : '/settings')">
          {{ summary?.google_connected ? '进入 Inbox' : '连接 Google' }}
        </el-button>
      </div>
    </div>

    <div class="stats-grid">
      <div v-for="item in stats" :key="item.label" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />

    <div class="dashboard-grid">
      <section class="content-band">
        <div class="panel-head">
          <h3>邮件分类分布</h3>
          <el-button text @click="router.push('/inbox')">查看</el-button>
        </div>
        <div v-if="summary?.category_breakdown.length" class="breakdown-list">
          <div v-for="item in summary.category_breakdown" :key="item.label" class="breakdown-row">
            <span>{{ categoryLabel(item.label) }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <p v-else>暂无分类数据。</p>
      </section>

      <section class="content-band">
        <div class="panel-head">
          <h3>优先级分布</h3>
          <el-button text @click="router.push('/inbox')">处理</el-button>
        </div>
        <div v-if="summary?.priority_breakdown.length" class="breakdown-list">
          <div v-for="item in summary.priority_breakdown" :key="item.label" class="breakdown-row">
            <span>{{ priorityLabel(item.label) }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <p v-else>暂无优先级数据。</p>
      </section>

      <section class="content-band">
        <div class="panel-head">
          <h3>最近邮件</h3>
          <el-button text @click="router.push('/inbox')">Inbox</el-button>
        </div>
        <div class="recent-list">
          <button v-for="item in summary?.recent_emails || []" :key="item.id" class="recent-row" @click="router.push(`/emails/${item.id}`)">
            <strong>{{ item.title }}</strong>
            <span>{{ item.subtitle }} · {{ categoryLabel(item.status) }}</span>
          </button>
          <p v-if="!summary?.recent_emails.length">暂无邮件。</p>
        </div>
      </section>

      <section class="content-band">
        <div class="panel-head">
          <h3>待确认与轨迹</h3>
          <el-button text @click="router.push('/pending-actions')">Actions</el-button>
        </div>
        <div class="recent-list">
          <button v-for="item in summary?.recent_actions || []" :key="item.id" class="recent-row" @click="router.push('/pending-actions')">
            <strong>{{ actionLabel(item.title) }}</strong>
            <span>{{ item.subtitle }} · {{ item.status }}</span>
          </button>
          <button v-for="item in summary?.recent_traces || []" :key="item.id" class="recent-row" @click="router.push('/traces')">
            <strong>{{ item.title }}</strong>
            <span>{{ item.status }} · {{ item.subtitle || 'Agent workflow' }}</span>
          </button>
          <p v-if="!summary?.recent_actions.length && !summary?.recent_traces.length">暂无待确认操作或轨迹。</p>
        </div>
      </section>
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
const error = ref('')

// 把后端统计结果转换成卡片数组，模板可以直接循环渲染。
const stats = computed(() => [
  { label: 'Google 连接', value: summary.value?.google_connected ? '已连接' : '未连接', hint: 'OAuth 状态' },
  { label: '邮件总数', value: summary.value?.email_count_today ?? 0, hint: `${summary.value?.analyzed_email_count ?? 0} 封已分析` },
  { label: '高优先级', value: summary.value?.high_priority_count ?? 0, hint: `${summary.value?.need_reply_count ?? 0} 封需回复` },
  { label: '会议请求', value: summary.value?.meeting_request_count ?? 0, hint: `${summary.value?.calendar_suggestion_count ?? 0} 条日程建议` },
  { label: '待办事项', value: summary.value?.task_count ?? 0, hint: 'Task Extraction 输出' },
  { label: '待确认操作', value: summary.value?.pending_action_count ?? 0, hint: 'Human-in-the-loop' },
  { label: '草稿预览', value: summary.value?.draft_preview_count ?? 0, hint: 'Reply Draft Agent' },
  { label: 'Agent 轨迹', value: summary.value?.trace_count ?? 0, hint: 'Trace records' },
])

async function loadSummary() {
  try {
    const { data } = await getDashboardSummary()
    summary.value = data
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取 Dashboard 数据失败。'
  }
}

function categoryLabel(value: string) {
  const labels: Record<string, string> = {
    urgent_reply: '紧急回复',
    normal_reply: '普通回复',
    calendar_related: '会议相关',
    task_required: '待办事项',
    newsletter: '订阅邮件',
    notification: '通知类',
    ignore: '可忽略',
    unanalyzed: '未分析',
  }
  return labels[value] ?? value
}

function priorityLabel(value: string) {
  const labels: Record<string, string> = { high: '高优先级', medium: '中优先级', low: '低优先级' }
  return labels[value] ?? value
}

function actionLabel(value: string) {
  const labels: Record<string, string> = {
    create_gmail_draft: '创建 Gmail 草稿',
    create_calendar_event: '创建 Calendar 日程',
  }
  return labels[value] ?? value
}

onMounted(loadSummary)
</script>
