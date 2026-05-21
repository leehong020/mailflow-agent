import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '@/views/DashboardView.vue'
import DraftReviewView from '@/views/DraftReviewView.vue'
import EmailDetailView from '@/views/EmailDetailView.vue'
import InboxView from '@/views/InboxView.vue'
import PendingActionsView from '@/views/PendingActionsView.vue'
import SettingsView from '@/views/SettingsView.vue'
import AgentTraceView from '@/views/AgentTraceView.vue'
import AIReplyWorkspaceView from '@/views/AIReplyWorkspaceView.vue'
import CalendarEventDetailView from '@/views/CalendarEventDetailView.vue'
import CalendarPlannerView from '@/views/CalendarPlannerView.vue'
import ComposeMailView from '@/views/ComposeMailView.vue'

// 第一阶段只建立基础路由：
// - Dashboard：系统首页；
// - Inbox：Gmail 最近邮件；
// - Settings：Google OAuth 连接状态。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/inbox', name: 'inbox', component: InboxView },
    { path: '/emails/:id', name: 'email-detail', component: EmailDetailView },
    { path: '/reply-workspace', name: 'ai-reply-workspace-new', component: AIReplyWorkspaceView },
    { path: '/reply-workspace/:previewId', name: 'ai-reply-workspace', component: AIReplyWorkspaceView },
    { path: '/compose', name: 'compose-mail-new', component: ComposeMailView },
    { path: '/compose/:previewId', name: 'compose-mail', component: ComposeMailView },
    { path: '/calendar', name: 'calendar-planner', component: CalendarPlannerView },
    { path: '/calendar/events/:id', name: 'calendar-event-detail', component: CalendarEventDetailView },
    { path: '/drafts', name: 'drafts', component: DraftReviewView },
    { path: '/pending-actions', name: 'pending-actions', component: PendingActionsView },
    { path: '/traces', name: 'traces', component: AgentTraceView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router
