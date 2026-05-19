<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Draft Review</h2>
        <p>这里展示 Agent 生成的回复草稿，支持编辑、调整语气，并提交到待确认操作中心。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="loading" @click="loadDrafts">刷新草稿</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div class="draft-review-grid">
      <section class="draft-list-panel">
        <h3>草稿列表</h3>
        <div v-if="drafts.length" class="draft-list">
          <button
            v-for="draft in drafts"
            :key="draft.id"
            class="trace-card"
            :class="{ active: selectedDraft?.id === draft.id }"
            @click="selectDraft(draft.id)"
          >
            <strong>{{ draft.subject }}</strong>
            <span>{{ draft.to }}</span>
            <small>{{ draft.tone }} / {{ draft.language }}</small>
          </button>
        </div>
        <div v-else class="empty-block compact">
          <h3>暂无草稿</h3>
          <p>先在邮件详情页点击“生成回复草稿”。</p>
        </div>
      </section>

      <section class="draft-editor-panel" v-if="selectedDraft">
        <div class="analysis-block">
          <strong>收件人</strong>
          <p>{{ selectedDraft.to }}</p>
        </div>
        <div class="analysis-block">
          <strong>主题</strong>
          <el-input v-model="draftSubject" />
        </div>

        <div class="editor-toolbar">
          <el-select v-model="selectedTone" placeholder="选择语气" style="width: 180px">
            <el-option label="正式" value="formal" />
            <el-option label="简洁" value="concise" />
            <el-option label="友好" value="friendly" />
            <el-option label="礼貌" value="polite" />
            <el-option label="拒绝" value="decline" />
            <el-option label="确认" value="confirm" />
          </el-select>
          <el-select v-model="selectedLanguage" placeholder="选择语言" style="width: 140px">
            <el-option label="英文" value="en" />
            <el-option label="中文" value="zh" />
          </el-select>
          <el-button :loading="regenerating" @click="handleRegenerate">重新生成</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">创建待确认操作</el-button>
        </div>

        <el-input v-model="draftBody" type="textarea" :rows="14" />

        <div class="analysis-block">
          <strong>生成理由</strong>
          <p>{{ selectedDraft.generation_reason || '暂无说明' }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  createDraftPreview,
  createPendingActionForDraft,
  getDraftPreviews,
  updateDraftPreview,
} from '@/api/drafts'
import type { DraftPreviewInfo } from '@/types/draft'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const message = ref('')
const drafts = ref<DraftPreviewInfo[]>([])
const selectedDraftId = ref('')
const draftSubject = ref('')
const draftBody = ref('')
const selectedTone = ref('polite')
const selectedLanguage = ref('en')
const regenerating = ref(false)
const submitting = ref(false)

const selectedDraft = computed(() => drafts.value.find((item) => item.id === selectedDraftId.value) || null)

async function loadDrafts() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getDraftPreviews({ limit: 50 })
    drafts.value = data.items
    const queryPreviewId = typeof route.query.preview === 'string' ? route.query.preview : ''
    const nextId = queryPreviewId || selectedDraftId.value || drafts.value[0]?.id || ''
    if (nextId) {
      await selectDraft(nextId)
    }
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '读取草稿失败。'
  } finally {
    loading.value = false
  }
}

async function selectDraft(draftId: string) {
  selectedDraftId.value = draftId
  const draft = drafts.value.find((item) => item.id === draftId)
  if (draft) {
    draftSubject.value = draft.subject
    draftBody.value = draft.body
    selectedTone.value = draft.tone
    selectedLanguage.value = draft.language
  }
}

async function handleRegenerate() {
  if (!selectedDraft.value) return
  regenerating.value = true
  try {
    const { data } = await createDraftPreview(selectedDraft.value.source_email_id, {
      tone: selectedTone.value,
      language: selectedLanguage.value,
    })
    await loadDrafts()
    await selectDraft(data.draft_preview_id)
    draftSubject.value = data.subject
    draftBody.value = data.body
    message.value = '草稿已重新生成。'
  } finally {
    regenerating.value = false
  }
}

async function handleSubmit() {
  if (!selectedDraft.value) return
  submitting.value = true
  error.value = ''
  message.value = ''
  try {
    await updateDraftPreview(selectedDraft.value.id, {
      tone: selectedTone.value,
      language: selectedLanguage.value,
      subject: draftSubject.value,
      body: draftBody.value,
    })
    const { data } = await createPendingActionForDraft(selectedDraft.value.id)
    message.value = data.message
    await router.push('/pending-actions')
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建待确认操作失败。'
  } finally {
    submitting.value = false
  }
}

onMounted(loadDrafts)
</script>
