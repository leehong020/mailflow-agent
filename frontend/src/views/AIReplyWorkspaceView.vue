<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>AI Reply Workspace</h2>
        <p>左侧是回复邮件，右侧通过对话生成和修改内容。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="saving" @click="saveDraft">保存修改</el-button>
        <el-button type="danger" :loading="sending" @click="confirmSend">发送邮件</el-button>
        <el-button @click="router.push('/inbox')">返回 Inbox</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div v-if="loading" class="empty-block">
      <h3>正在准备回复工作台</h3>
      <p>正在载入原邮件和回复编辑器。</p>
    </div>

    <div v-else-if="previewId" class="ai-reply-workspace">
      <section class="workspace-left">
        <div v-if="sourceEmail" class="source-mail-strip">
          <strong>{{ sourceEmail.subject }}</strong>
          <span>{{ sourceEmail.sender }}</span>
          <p>{{ sourceEmail.analysis?.summary || sourceEmail.snippet || sourceEmail.body_preview }}</p>
        </div>
        <MailEditor v-model="editor" />
      </section>

      <ComposeAssistantPanel
        :messages="assistantMessages"
        :loading="revising"
        :can-undo="Boolean(lastSnapshot)"
        @revise="reviseWithAI"
        @undo="undoLastRevision"
      />
    </div>

    <div v-else class="empty-block">
      <h3>没有可编辑的回复草稿</h3>
      <p>请从邮件详情页点击“AI 回复”。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ComposeAssistantPanel from '@/components/ComposeAssistantPanel.vue'
import MailEditor from '@/components/MailEditor.vue'
import {
  createSendActionForDraft,
  createReplyWorkspacePreview,
  getDraftPreview,
  getLatestDraftPreview,
  reviseDraftPreview,
  updateDraftPreview,
} from '@/api/drafts'
import { getEmailDetail } from '@/api/emails'
import { addDraftMemoryMessage, getDraftMemorySession } from '@/api/memory'
import type { DraftPreviewInfo, MailEditorState } from '@/types/draft'
import type { EmailDetail } from '@/types/email'
import type { ComposeSessionInfo } from '@/types/memory'

interface AssistantMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const revising = ref(false)
const sending = ref(false)
const error = ref('')
const message = ref('')
const previewId = ref('')
const sourceEmail = ref<EmailDetail | null>(null)
const lastSnapshot = ref<MailEditorState | null>(null)
const assistantMessages = ref<AssistantMessage[]>([])

const editor = ref<MailEditorState>({
  to: '',
  subject: '',
  body: '',
  tone: 'polite',
  language: 'auto',
})

async function initializeWorkspace() {
  loading.value = true
  error.value = ''
  try {
    const routePreviewId = String(route.params.previewId || route.query.preview || '')
    const emailId = String(route.query.email || '')

    if (emailId) {
      const { data } = await getEmailDetail(emailId)
      sourceEmail.value = data
    }

    if (routePreviewId) {
      previewId.value = routePreviewId
      const { data } = await getDraftPreview(routePreviewId)
      applyPreview(data)
      await loadMemorySession(routePreviewId, data)
      if (data.source_email_id && !sourceEmail.value) {
        await loadSourceEmail(data.source_email_id)
      }
      return
    }

    if (emailId) {
      const existing = await getLatestDraftPreview(emailId)
      if (existing.data) {
        previewId.value = existing.data.id
        applyPreview(existing.data)
        await loadMemorySession(existing.data.id, existing.data)
        router.replace(`/reply-workspace/${existing.data.id}`)
        return
      }

      const { data } = await createReplyWorkspacePreview(emailId)
      previewId.value = data.draft_preview_id
      editor.value = responseToEditor(data, 'workspace', 'auto')
      await loadMemorySession(data.draft_preview_id, {
        id: data.draft_preview_id,
        source_email_id: emailId,
        to: data.to,
        subject: data.subject,
        body: data.body,
        tone: 'workspace',
        language: 'auto',
        status: 'preview',
        generation_reason: data.generation_reason,
      })
      router.replace(`/reply-workspace/${data.draft_preview_id}`)
    }
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '准备 AI 回复工作台失败。'
  } finally {
    loading.value = false
  }
}

async function loadSourceEmail(emailId: string) {
  try {
    const { data } = await getEmailDetail(emailId)
    sourceEmail.value = data
  } catch {
  }
}

function applyPreview(data: DraftPreviewInfo) {
  editor.value = {
    to: data.to,
    subject: data.subject,
    body: data.body,
    tone: data.tone || 'polite',
    language: data.language || 'auto',
  }
  assistantMessages.value = []
}

async function loadMemorySession(draftId: string, draft: DraftPreviewInfo) {
  const { data } = await getDraftMemorySession(draftId, 'reply')
  applyMemoryMessages(data, draft)
}

function applyMemoryMessages(session: ComposeSessionInfo, draft: DraftPreviewInfo) {
  if (Object.keys(session.editor_snapshot || {}).length) {
    editor.value = {
      to: String(session.editor_snapshot.to ?? editor.value.to),
      subject: String(session.editor_snapshot.subject ?? editor.value.subject),
      body: String(session.editor_snapshot.body ?? editor.value.body),
      tone: String(session.editor_snapshot.tone ?? editor.value.tone),
      language: String(session.editor_snapshot.language ?? editor.value.language),
    }
  }
  assistantMessages.value = session.messages.length
    ? session.messages.map((item) => ({ id: item.id, role: item.role, content: item.content }))
    : [
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: draft.generation_reason || '工作台已准备好。你可以直接告诉我想怎么回复，我会把内容写到左侧。',
        },
      ]
}

function responseToEditor(data: { to: string; subject: string; body: string }, tone: string, language: string) {
  return {
    to: data.to,
    subject: data.subject,
    body: data.body,
    tone,
    language,
  }
}

async function saveDraft() {
  if (!previewId.value) return
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    await updateDraftPreview(previewId.value, editor.value)
    message.value = '草稿修改已保存。'
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '保存草稿失败。'
  } finally {
    saving.value = false
  }
}

async function reviseWithAI(instruction: string) {
  if (!previewId.value) return
  revising.value = true
  error.value = ''
  message.value = ''
  lastSnapshot.value = { ...editor.value }
  const userMessage = { id: crypto.randomUUID(), role: 'user' as const, content: instruction }
  assistantMessages.value.push(userMessage)
  try {
    await addDraftMemoryMessage(previewId.value, 'reply', {
      role: 'user',
      content: instruction,
      editor_snapshot: editor.value,
    })
    const { data } = await reviseDraftPreview(previewId.value, {
      ...editor.value,
      instruction,
      tone: 'workspace',
      language: 'auto',
    })
    editor.value = responseToEditor(data, data.tone, data.language)
    const assistantMessage = {
      id: crypto.randomUUID(),
      role: 'assistant' as const,
      content: data.generation_reason || '已按要求更新左侧邮件内容。',
    }
    assistantMessages.value.push(assistantMessage)
    await addDraftMemoryMessage(previewId.value, 'reply', {
      role: 'assistant',
      content: assistantMessage.content,
      editor_snapshot: editor.value,
    })
  } catch (caught: any) {
    lastSnapshot.value = null
    error.value = caught?.response?.data?.detail ?? 'AI 修改草稿失败。'
  } finally {
    revising.value = false
  }
}

async function undoLastRevision() {
  if (!lastSnapshot.value || !previewId.value) return
  editor.value = { ...lastSnapshot.value }
  lastSnapshot.value = null
  await updateDraftPreview(previewId.value, editor.value)
  assistantMessages.value.push({
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '已撤销上一次 AI 修改，并恢复左侧编辑器内容。',
  })
}

async function confirmSend() {
  if (!previewId.value) return
  sending.value = true
  error.value = ''
  try {
    await updateDraftPreview(previewId.value, editor.value)
    const { data } = await createSendActionForDraft(previewId.value)
    message.value = data.message
    await router.push('/pending-actions')
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '创建发送待确认操作失败。'
  } finally {
    sending.value = false
  }
}

onMounted(initializeWorkspace)
</script>
