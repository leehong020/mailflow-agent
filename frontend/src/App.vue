<template>
  <!-- App 只挂载全局布局，具体页面由 router 在 AppLayout 中渲染。 -->
  <AppLayout />
</template>

<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
</script>
