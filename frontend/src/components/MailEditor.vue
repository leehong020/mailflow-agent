<template>
  <div class="mail-editor">
    <div class="editor-row">
      <label>To</label>
      <el-input v-model="state.to" placeholder="收件人" />
    </div>
    <div class="editor-row">
      <label>Subject</label>
      <el-input v-model="state.subject" placeholder="邮件主题" />
    </div>
    <div class="editor-row">
      <label>Body</label>
      <el-input v-model="state.body" type="textarea" :rows="16" placeholder="邮件正文" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MailEditorState } from '@/types/draft'

const model = defineModel<MailEditorState>({ required: true })
const state = computed({
  get: () => model.value,
  set: (value) => {
    model.value = value
  },
})
</script>
