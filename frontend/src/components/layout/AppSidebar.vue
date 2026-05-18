<template>
  <aside class="sidebar">
    <!-- 左侧品牌区，强调这是工作台而不是聊天窗口。 -->
    <div class="brand">
      <div class="brand-mark">M</div>
      <div>
        <strong>MailFlow</strong>
        <span>Agent Workspace</span>
      </div>
    </div>

    <!-- 第一二阶段只放三个入口，后续再扩展 Agent Trace、Draft Review 等页面。 -->
    <nav class="nav-list" aria-label="主导航">
      <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { Inbox, LayoutDashboard, Settings } from 'lucide-vue-next'

// 导航项集中配置，后续新增页面只需要在这里添加一项。
const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/settings', label: 'Settings', icon: Settings },
]
</script>
