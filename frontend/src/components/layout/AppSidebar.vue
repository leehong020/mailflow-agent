<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">M</div>
      <div>
        <strong>MailFlow</strong>
        <span>Agent Workspace</span>
      </div>
    </div>

    <nav class="nav-list" aria-label="主导航">
      <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { Activity, CalendarDays, Inbox, LayoutDashboard, MailPlus, PenSquare, Settings, SquareCheckBig } from 'lucide-vue-next'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/compose', label: 'Compose Mail', icon: MailPlus },
  { path: '/calendar', label: 'Calendar Planner', icon: CalendarDays },
  { path: '/drafts', label: 'Draft Review', icon: PenSquare },
  { path: '/pending-actions', label: 'Pending Actions', icon: SquareCheckBig },
  { path: '/traces', label: 'Agent Trace', icon: Activity },
  { path: '/settings', label: 'Settings', icon: Settings },
]
</script>
