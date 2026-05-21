<template>
  <section class="workspace-right">
    <div class="assistant-header">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ description }}</p>
      </div>
    </div>

    <div class="assistant-message-list">
      <div v-for="msg in messages" :key="msg.id" class="assistant-message" :class="msg.role">
        {{ msg.content }}
      </div>
    </div>

    <div class="assistant-compose-box">
      <el-input v-model="prompt" type="textarea" :rows="5" :placeholder="placeholder" />
      <div class="toolbar-actions">
        <el-button v-if="canUndo" @click="$emit('undo')">撤销上一步</el-button>
        <el-button type="primary" :loading="loading" @click="submit">{{ submitLabel }}</el-button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface AssistantMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
}

defineProps<{
  title?: string
  description?: string
  emptyExample?: string
  placeholder?: string
  submitLabel?: string
  messages: AssistantMessage[]
  loading?: boolean
  canUndo?: boolean
}>()

const emit = defineEmits<{ revise: [string]; undo: [] }>()
const prompt = ref('')

function submit() {
  if (!prompt.value.trim()) return
  emit('revise', prompt.value.trim())
  prompt.value = ''
}
</script>
