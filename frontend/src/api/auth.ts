import { API_BASE_URL, http } from './http'
import type { GoogleConnectionStatus } from '@/types/auth'

// 查询后端保存的 Google 授权状态，用于 Settings 和顶部状态标签。
export function getGoogleStatus() {
  return http.get<GoogleConnectionStatus>('/auth/google/status')
}

// 删除本地保存的 Google token，不会影响 Google 账号中的邮件数据。
export function disconnectGoogle() {
  return http.post('/auth/google/disconnect')
}

// OAuth 登录必须让浏览器跳转到后端，由后端再跳转到 Google 授权页。
export function redirectToGoogleLogin() {
  window.location.href = `${API_BASE_URL}/auth/google/login`
}
