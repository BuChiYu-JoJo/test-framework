<template>
  <el-tag :type="type" size="small" effect="light" class="ai-badge">
    <span class="ai-icon">AI</span>
    <span>{{ label }}</span>
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  kind: { type: String, default: 'heal' },
  count: { type: Number, default: 0 },
})

const type = computed(() => {
  if (props.kind === 'heal') return 'warning'
  if (props.kind === 'observe') return 'info'
  if (props.kind === 'generate') return 'success'
  return 'info'
})

const label = computed(() => {
  const names = { heal: '自愈', observe: '观察', generate: '生成', fix: '修复' }
  const name = names[props.kind] || props.kind
  return props.count > 0 ? `${name} ×${props.count}` : name
})
</script>

<style scoped>
.ai-badge { gap: 4px; }
.ai-icon { font-weight: 700; font-size: 10px; }
</style>
