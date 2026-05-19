<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Agent Trace</h2>
        <p>这里展示多 Agent 工作流的执行轨迹，帮助你在课程演示时说明系统不是单次 LLM 调用。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="loading" @click="loadTraces">刷新轨迹</el-button>
      </div>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <div class="trace-layout">
      <section class="trace-list-panel">
        <h3>轨迹列表</h3>
        <div v-if="traces.length" class="trace-list">
          <button
            v-for="trace in traces"
            :key="trace.id"
            class="trace-card"
            :class="{ active: selectedTraceId === trace.id }"
            @click="selectTrace(trace.id)"
          >
            <strong>{{ trace.task_type }}</strong>
            <span>{{ formatTime(trace.created_at) }}</span>
            <small>{{ trace.status }}</small>
          </button>
        </div>
        <div v-else class="empty-block compact">
          <h3>暂无轨迹</h3>
          <p>先到 Inbox 触发一次“同步并分析邮件”，这里才会出现执行轨迹。</p>
        </div>
      </section>

      <section class="trace-detail-panel">
        <template v-if="traceDetail">
          <div class="trace-summary-card">
            <div>
              <h3>{{ traceDetail.task_type }}</h3>
              <p>{{ traceDetail.input_summary || '暂无输入摘要' }}</p>
            </div>
            <div class="trace-summary-meta">
              <span>状态：{{ traceDetail.status }}</span>
              <span>开始：{{ formatTime(traceDetail.created_at) }}</span>
              <span v-if="traceDetail.completed_at">结束：{{ formatTime(traceDetail.completed_at) }}</span>
            </div>
          </div>

          <div class="analysis-block">
            <strong>输出摘要</strong>
            <p>{{ traceDetail.output_summary || '暂无输出摘要' }}</p>
          </div>

          <div class="timeline">
            <div v-for="event in traceDetail.events" :key="event.id" class="timeline-item">
              <div class="timeline-step">{{ event.step }}</div>
              <div class="timeline-content">
                <div class="timeline-head">
                  <strong>{{ event.agent_name }}</strong>
                  <el-tag size="small" :type="eventTagType(event.status)" effect="plain">{{ event.status }}</el-tag>
                </div>
                <p>{{ event.message }}</p>
                <small v-if="event.input_preview">输入：{{ event.input_preview }}</small>
                <small v-if="event.output_preview">输出：{{ event.output_preview }}</small>
                <small>{{ formatTime(event.created_at) }}</small>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="empty-block">
          <h3>请选择一条轨迹</h3>
          <p>左侧列表会显示最近一次 Agent 执行记录。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getTrace, getTraces } from '@/api/traces'
import type { TraceInfo, TraceListItem } from '@/types/trace'

const loading = ref(false)
const error = ref('')
const traces = ref<TraceListItem[]>([])
const traceDetail = ref<TraceInfo | null>(null)
const selectedTraceId = ref('')

async function loadTraces() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getTraces({ limit: 20 })
    traces.value = data.items
    if (!selectedTraceId.value && traces.value.length) {
      await selectTrace(traces.value[0].id)
    }
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取 Agent 轨迹失败。'
  } finally {
    loading.value = false
  }
}

async function selectTrace(traceId: string) {
  selectedTraceId.value = traceId
  error.value = ''
  try {
    const { data } = await getTrace(traceId)
    traceDetail.value = data
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取轨迹详情失败。'
  }
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

function eventTagType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

onMounted(loadTraces)
</script>
