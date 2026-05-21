<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Agent Trace</h2>
        <p>这里展示多 Agent 工作流的执行轨迹，支持通过 SSE 实时接收节点状态。</p>
      </div>
      <div class="toolbar-actions">
        <el-select v-model="statusFilter" clearable placeholder="状态" class="trace-filter" @change="loadTraces">
          <el-option label="running" value="running" />
          <el-option label="completed" value="completed" />
          <el-option label="failed" value="failed" />
        </el-select>
        <el-input v-model="taskTypeFilter" class="trace-filter" placeholder="任务类型" clearable @keyup.enter="loadTraces" />
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
    <el-alert
      v-if="liveMessage"
      :title="liveMessage"
      type="info"
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
            <small>{{ trace.status }} · {{ formatDuration(trace.duration_ms) }}</small>
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
              <span>耗时：{{ formatDuration(traceDetail.duration_ms) }}</span>
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
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { getTrace, getTraces, streamTrace } from '@/api/traces'
import type { TraceEventInfo, TraceInfo, TraceListItem } from '@/types/trace'

const loading = ref(false)
const error = ref('')
const traces = ref<TraceListItem[]>([])
const traceDetail = ref<TraceInfo | null>(null)
const selectedTraceId = ref('')
const statusFilter = ref('')
const taskTypeFilter = ref('')
const liveMessage = ref('')
let eventSource: EventSource | null = null

async function loadTraces() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getTraces({
      limit: 20,
      status: statusFilter.value || null,
      task_type: taskTypeFilter.value || null,
    })
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

function formatDuration(value?: number | null) {
  if (value == null) return '进行中'
  if (value < 1000) return `${value} ms`
  return `${(value / 1000).toFixed(1)} s`
}

async function selectTrace(traceId: string) {
  selectedTraceId.value = traceId
  error.value = ''
  liveMessage.value = ''
  closeStream()
  try {
    const { data } = await getTrace(traceId)
    traceDetail.value = data
    openStream(traceId)
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取轨迹详情失败。'
  }
}

function openStream(traceId: string) {
  eventSource = streamTrace(traceId)
  liveMessage.value = '已连接 Trace 实时流。'
  eventSource.addEventListener('trace_event', (event) => {
    const item = JSON.parse((event as MessageEvent).data) as TraceEventInfo
    if (!traceDetail.value) return
    const index = traceDetail.value.events.findIndex((existing) => existing.id === item.id)
    if (index >= 0) {
      traceDetail.value.events[index] = item
    } else {
      traceDetail.value.events.push(item)
      traceDetail.value.events.sort((left, right) => left.step - right.step || left.created_at.localeCompare(right.created_at))
    }
  })
  eventSource.addEventListener('trace_status', (event) => {
    const item = JSON.parse((event as MessageEvent).data) as {
      status: string
      output_summary: string
      completed_at?: string | null
      duration_ms?: number | null
    }
    if (!traceDetail.value) return
    traceDetail.value.status = item.status
    traceDetail.value.output_summary = item.output_summary
    traceDetail.value.completed_at = item.completed_at
    traceDetail.value.duration_ms = item.duration_ms
    liveMessage.value = item.status === 'running' ? 'Trace 实时流正在接收执行步骤。' : 'Trace 已完成，实时流已关闭。'
    if (item.status !== 'running') {
      closeStream()
      loadTraces()
    }
  })
  eventSource.addEventListener('error', () => {
    liveMessage.value = ''
    closeStream()
  })
}

function closeStream() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
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
onBeforeUnmount(closeStream)
</script>
