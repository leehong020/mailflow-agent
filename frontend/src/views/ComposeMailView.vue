<template>
  <div class="stack">
    <div class="section-header">
      <div>
        <h2>Compose Mail</h2>
        <p>左侧是主动写邮件编辑器，右侧通过对话生成或修改内容。</p>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="saving" :disabled="!previewId" @click="saveDraft">保存修改</el-button>
        <el-button type="danger" :loading="sending" :disabled="!previewId" @click="sendMail">发送邮件</el-button>
        <el-button @click="router.push('/drafts')">Draft Review</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false" />
    <el-alert v-if="message" :title="message" type="success" show-icon :closable="false" />

    <div v-if="loading" class="empty-block">
      <h3>正在载入写信工作台</h3>
      <p>正在准备本地草稿编辑器。</p>
    </div>

    <div v-else class="ai-reply-workspace">
      <section class="workspace-left">
        <section class="source-mail-strip">
          <strong>主动写邮件</strong>
          <span>{{ previewId ? '已保存为本地草稿，会出现在 Draft Review 中。' : '先在右侧说明写信目标，AI 会生成左侧内容。' }}</span>
          <p>发送前请检查收件人、主题和正文；点击发送后仍会进入 Pending Actions 二次确认。</p>
        </section>
        <MailEditor v-model="editor" />
      </section>

      <ComposeAssistantPanel
        title="AI 写信助手"
        description="告诉 AI 你要给谁写、想表达什么，它会把结果写到左侧。"
        empty-example="例如：帮我给导师写一封中文邮件，说明我周五前提交项目报告。"
        placeholder="输入写信目标，或要求 AI 修改左侧内容"
        submit-label="生成 / 修改"
        :messages="assistantMessages"
        :loading="composing"
        :can-undo="Boolean(lastSnapshot)"
        @revise="composeWithAI"
        @undo="undoLastRevision"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { generateComposeDraft, reviseComposeDraft } from '@/api/compose'
import { createSendActionForDraft, getDraftPreview, updateDraftPreview } from '@/api/drafts'
import { addDraftMemoryMessage, getDraftMemorySession } from '@/api/memory'
import ComposeAssistantPanel from '@/components/ComposeAssistantPanel.vue'
import MailEditor from '@/components/MailEditor.vue'
import type { MailEditorState } from '@/types/draft'
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
const composing = ref(false)
const sending = ref(false)
const error = ref('')
const message = ref('')
const previewId = ref('')
const lastSnapshot = ref<MailEditorState | null>(null)
const assistantMessages = ref<AssistantMessage[]>([])

const editor = ref<MailEditorState>({
  to: '',
  subject: '',
  body: '',
  tone: 'compose',
  language: 'auto',
})

async function initializeComposeWorkspace() {
  loading.value = true
  error.value = ''
  try {
    const routePreviewId = String(route.params.previewId || '')
    if (!routePreviewId) {
      assistantMessages.value = [
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '告诉我你要写什么邮件，我会生成主题和正文，并保存到 Draft Review。',
        },
      ]
      return
    }

    previewId.value = routePreviewId
    const { data } = await getDraftPreview(routePreviewId)
    editor.value = {
      to: data.to,
      subject: data.subject,
      body: data.body,
      tone: data.tone || 'compose',
      language: data.language || 'auto',
    }
    await loadMemorySession(routePreviewId, data)
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '载入主动写邮件工作台失败。'
  } finally {
    loading.value = false
  }
}

async function loadMemorySession(draftId: string, draft: { generation_reason?: string }) {
  const { data } = await getDraftMemorySession(draftId, 'compose')
  applyMemoryMessages(data, draft)
}

function applyMemoryMessages(session: ComposeSessionInfo, draft: { generation_reason?: string }) {
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
          content: draft.generation_reason || '已载入主动写邮件草稿，可以继续让我修改。',
        },
      ]
}

async function composeWithAI(instruction: string) {
  composing.value = true
  error.value = ''
  message.value = ''
  lastSnapshot.value = { ...editor.value }
  const userMessage = { id: crypto.randomUUID(), role: 'user' as const, content: instruction }
  assistantMessages.value.push(userMessage)

  try {
    const hadPreview = Boolean(previewId.value)
    const payload = {
      to: editor.value.to,
      subject: editor.value.subject,
      body: editor.value.body,
      tone: 'compose',
      language: 'auto',
    }

    if (hadPreview) {
      await addDraftMemoryMessage(previewId.value, 'compose', {
        role: 'user',
        content: instruction,
        editor_snapshot: editor.value,
      })
    }

    const { data } = hadPreview
      ? await reviseComposeDraft(previewId.value, { ...payload, instruction })
      : await generateComposeDraft({ ...payload, goal: instruction })

    previewId.value = data.draft_preview_id
    editor.value = {
      to: data.to,
      subject: data.subject,
      body: data.body,
      tone: data.tone,
      language: data.language,
    }
    const assistantMessage = {
      id: crypto.randomUUID(),
      role: 'assistant' as const,
      content: data.generation_reason || '已更新左侧邮件内容。',
    }
    assistantMessages.value.push(assistantMessage)
    if (!hadPreview) {
      await addDraftMemoryMessage(data.draft_preview_id, 'compose', {
        role: 'user',
        content: instruction,
        editor_snapshot: lastSnapshot.value || editor.value,
      })
    }
    await addDraftMemoryMessage(data.draft_preview_id, 'compose', {
      role: 'assistant',
      content: assistantMessage.content,
      editor_snapshot: editor.value,
    })
    if (route.params.previewId !== data.draft_preview_id) {
      await router.replace(`/compose/${data.draft_preview_id}`)
    }
  } catch (caught: any) {
    lastSnapshot.value = null
    error.value = caught?.response?.data?.detail ?? 'AI 写信失败。'
  } finally {
    composing.value = false
  }
}

async function saveDraft() {
  if (!previewId.value) return
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    await updateDraftPreview(previewId.value, editor.value)
    message.value = '本地草稿已保存。'
  } catch (caught: any) {
    error.value = caught?.response?.data?.detail ?? '保存草稿失败。'
  } finally {
    saving.value = false
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

async function sendMail() {
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

onMounted(initializeComposeWorkspace)
</script>
