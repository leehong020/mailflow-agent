<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Draft Review</h2>
        <p>这里展示本地草稿记录，点击任意草稿进入对应工作台继续编辑。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="router.push('/compose')">新建邮件</el-button>
        <el-button :loading="loading" @click="loadDrafts">刷新草稿</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />

    <section v-if="drafts.length" class="draft-record-grid">
      <article
        v-for="draft in drafts"
        :key="draft.id"
        class="draft-record-card"
        @click="openWorkspace(draft)"
      >
        <div class="draft-record-head">
          <div>
            <h3>{{ draft.subject || '无主题草稿' }}</h3>
            <span>{{ draft.to || '未填写收件人' }}</span>
          </div>
          <el-tag size="small" :type="draftStatusTagType(draft.status)" effect="plain">
            {{ draftStatusLabel(draft.status) }}
          </el-tag>
        </div>
        <p>{{ draft.body || draft.generation_reason || '尚未生成正文，进入工作台后可通过右侧 AI 对话生成。' }}</p>
        <div class="draft-record-meta">
          <small>{{ draft.source_email_id ? '回复草稿' : '主动写邮件' }}</small>
          <small>{{ formatTime(draft.updated_at || draft.created_at) }}</small>
        </div>
        <div class="draft-record-actions">
          <el-button
            size="small"
            type="danger"
            plain
            :loading="deletingId === draft.id"
            @click.stop="confirmDeleteDraft(draft)"
          >
            删除草稿
          </el-button>
        </div>
      </article>
    </section>

    <div v-else-if="!loading" class="empty-block">
      <h3>暂无草稿记录</h3>
      <p>从邮件详情页点击“AI 回复”，或从 Compose Mail 主动写一封邮件后，这里会显示对应草稿。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { deleteDraftPreview, getDraftPreviews } from '@/api/drafts'
import type { DraftPreviewInfo } from '@/types/draft'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const deletingId = ref('')
const error = ref('')
const drafts = ref<DraftPreviewInfo[]>([])

async function loadDrafts() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getDraftPreviews({ limit: 50 })
    drafts.value = data.items

    const queryPreviewId = typeof route.query.preview === 'string' ? route.query.preview : ''
    if (queryPreviewId) {
      const target = drafts.value.find((item) => item.id === queryPreviewId)
      if (target) {
        await openWorkspace(target)
      }
    }
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取草稿记录失败。'
  } finally {
    loading.value = false
  }
}

async function openWorkspace(draft: DraftPreviewInfo) {
  if (draft.source_email_id) {
    await router.push(`/reply-workspace/${draft.id}`)
    return
  }
  await router.push(`/compose/${draft.id}`)
}

async function confirmDeleteDraft(draft: DraftPreviewInfo) {
  try {
    await ElMessageBox.confirm(
      `确定删除草稿「${draft.subject || '无主题草稿'}」吗？这只会删除本地草稿记录，不会删除 Gmail 邮件。`,
      '删除草稿',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deletingId.value = draft.id
  error.value = ''
  try {
    const { data } = await deleteDraftPreview(draft.id)
    ElMessage.success(data.message || '草稿已删除')
    drafts.value = drafts.value.filter((item) => item.id !== draft.id)
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '删除草稿失败。'
  } finally {
    deletingId.value = ''
  }
}

function draftStatusLabel(value: string) {
  const labels: Record<string, string> = {
    preview: '草稿',
    pending: '待确认',
    created: '已创建',
    send_pending: '发送待确认',
    sent: '已发送',
    rejected: '已拒绝',
    failed: '失败',
  }
  return labels[value] ?? value
}

function draftStatusTagType(value: string) {
  if (value === 'created' || value === 'sent') return 'success'
  if (value === 'pending' || value === 'send_pending') return 'warning'
  if (value === 'rejected' || value === 'failed') return 'info'
  return 'primary'
}

function formatTime(value?: string | null) {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(loadDrafts)
</script>
