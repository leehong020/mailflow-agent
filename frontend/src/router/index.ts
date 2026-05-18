import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '@/views/DashboardView.vue'
import InboxView from '@/views/InboxView.vue'
import SettingsView from '@/views/SettingsView.vue'

// 第一阶段只建立基础路由：
// - Dashboard：系统首页；
// - Inbox：Gmail 最近邮件；
// - Settings：Google OAuth 连接状态。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/inbox', name: 'inbox', component: InboxView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router
