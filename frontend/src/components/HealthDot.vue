<template>
  <span
    class="health-dot"
    :style="{ background: colorMap[color] || colorMap.grey }"
    :title="labelMap[color] || labelMap.grey"
  />
</template>

<script setup>
defineProps({
  color: { type: String, default: 'grey' },
})

const colorMap = { green: '#67C23A', yellow: '#E6A23C', red: '#F56C6C', grey: '#C0C4CC' }
const labelMap = { green: '健康', yellow: '注意', red: '告警', grey: '无数据' }
</script>

<style scoped>
.health-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
