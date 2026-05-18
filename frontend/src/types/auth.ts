// Settings 页面使用的 Google 连接状态类型。
export interface GoogleConnectionStatus {
  connected: boolean
  email?: string | null
  name?: string | null
  picture?: string | null
  scopes: string[]
}
