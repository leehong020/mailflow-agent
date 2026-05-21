<template>
  <div class="email-operation-bar">
    <el-tooltip :content="email.is_read ? '标记未读' : '标记已读'">
      <el-button size="small" :loading="busy === 'read'" @click.stop="toggleRead">
        <component :is="email.is_read ? Mail : MailOpen" :size="15" />
      </el-button>
    </el-tooltip>
    <el-tooltip :content="email.is_starred ? '取消星标' : '加星标'">
      <el-button size="small" :loading="busy === 'star'" @click.stop="toggleStar">
        <Star :size="15" />
      </el-button>
    </el-tooltip>
    <el-tooltip content="归档，需确认">
      <el-button size="small" :loading="busy === 'archive'" @click.stop="archive">
        <Archive :size="15" />
      </el-button>
    </el-tooltip>
    <el-tooltip content="移动到垃圾箱，需确认">
      <el-button size="small" type="danger" plain :loading="busy === 'trash'" @click.stop="trash">
        <Trash2 :size="15" />
      </el-button>
    </el-tooltip>
    <el-popover trigger="click" width="320" placement="bottom" @show="loadLabels">
      <template #reference>
        <el-button size="small" @click.stop>
          <Tag :size="15" />
        </el-button>
      </template>
      <div class="label-action-popover">
        <strong>修改 Gmail 标签</strong>
        <el-select v-model="addLabels" multiple filterable placeholder="添加标签">
          <el-option v-for="label in labels" :key="label.id" :label="label.name" :value="label.id" />
        </el-select>
        <el-select v-model="removeLabels" multiple filterable placeholder="移除标签">
          <el-option v-for="label in labels" :key="label.id" :label="label.name" :value="label.id" />
        </el-select>
        <el-button type="primary" :loading="busy === 'labels'" @click.stop="submitLabels">加入待确认</el-button>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Archive, Mail, MailOpen, Star, Tag, Trash2 } from 'lucide-vue-next'

import {
  createArchiveAction,
  createLabelsAction,
  createTrashAction,
  getGmailLabels,
  markEmailRead,
  markEmailUnread,
  starEmail,
  unstarEmail,
} from '@/api/emails'
import type { EmailListItem, GmailLabelInfo } from '@/types/email'

const props = defineProps<{
  email: EmailListItem
}>()

const emit = defineEmits<{
  updated: [email: EmailListItem]
  pending: [message: string]
  error: [message: string]
}>()

const busy = ref('')
const labels = ref<GmailLabelInfo[]>([])
const addLabels = ref<string[]>([])
const removeLabels = ref<string[]>([])

async function toggleRead() {
  busy.value = 'read'
  try {
    const { data } = props.email.is_read
      ? await markEmailUnread(props.email.id)
      : await markEmailRead(props.email.id)
    if (data.email) emit('updated', data.email)
    emit('pending', data.message)
  } catch (caught: any) {
    emit('error', caught?.response?.data?.detail ?? '邮件读写状态修改失败。')
  } finally {
    busy.value = ''
  }
}

async function toggleStar() {
  busy.value = 'star'
  try {
    const { data } = props.email.is_starred
      ? await unstarEmail(props.email.id)
      : await starEmail(props.email.id)
    if (data.email) emit('updated', data.email)
    emit('pending', data.message)
  } catch (caught: any) {
    emit('error', caught?.response?.data?.detail ?? '星标修改失败。')
  } finally {
    busy.value = ''
  }
}

async function archive() {
  busy.value = 'archive'
  try {
    const { data } = await createArchiveAction(props.email.id)
    emit('pending', data.message)
  } catch (caught: any) {
    emit('error', caught?.response?.data?.detail ?? '创建归档待确认操作失败。')
  } finally {
    busy.value = ''
  }
}

async function trash() {
  busy.value = 'trash'
  try {
    const { data } = await createTrashAction(props.email.id)
    emit('pending', data.message)
  } catch (caught: any) {
    emit('error', caught?.response?.data?.detail ?? '创建垃圾箱待确认操作失败。')
  } finally {
    busy.value = ''
  }
}

async function submitLabels() {
  if (!addLabels.value.length && !removeLabels.value.length) {
    emit('error', '请至少选择一个要添加或移除的标签。')
    return
  }
  busy.value = 'labels'
  try {
    const { data } = await createLabelsAction(props.email.id, {
      add_label_ids: addLabels.value,
      remove_label_ids: removeLabels.value,
    })
    addLabels.value = []
    removeLabels.value = []
    emit('pending', data.message)
  } catch (caught: any) {
    emit('error', caught?.response?.data?.detail ?? '创建标签修改待确认操作失败。')
  } finally {
    busy.value = ''
  }
}

async function loadLabels() {
  if (labels.value.length) return
  try {
    const { data } = await getGmailLabels()
    labels.value = data.items
  } catch {
    labels.value = []
  }
}
</script>
