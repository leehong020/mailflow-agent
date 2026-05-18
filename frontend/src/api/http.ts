import axios from 'axios'

// 后端 API 基础地址。
// 生产部署或端口变化时，可以在 frontend/.env 中配置 VITE_API_BASE_URL。
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

// Axios 实例统一配置，后续可在这里加 token、错误拦截、请求日志等。
export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
})
