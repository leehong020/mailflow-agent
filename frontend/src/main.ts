import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles.css'

// 前端入口：
// 1. 创建 Vue 应用；
// 2. 注册 Pinia、Vue Router、Element Plus；
// 3. 挂载到 index.html 中的 #app。
createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
