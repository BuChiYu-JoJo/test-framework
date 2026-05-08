<template>
  <el-timeline v-if="steps.length">
    <el-timeline-item
      v-for="step in steps"
      :key="step.step_no"
      :type="step.status === 'passed' ? 'success' : step.status === 'failed' ? 'danger' : 'info'"
      :timestamp="`${step.duration_ms || 0}ms`"
      placement="top"
    >
      <div class="timeline-step">
        <strong>#{{ step.step_no }} {{ step.action }}</strong>
        <code v-if="step.target" class="step-target">{{ step.target }}</code>
        <el-tag v-if="step.matched_strategy_type" size="small"
          :type="step.matched_strategy_type === 'ai_healed' ? 'warning' : 'info'"
          style="margin-left:6px">
          {{ step.matched_strategy_type }}
        </el-tag>
        <div v-if="step.error_msg" class="step-error">{{ step.error_msg }}</div>
      </div>
    </el-timeline-item>
  </el-timeline>
  <el-empty v-else description="暂无步骤" />
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
})
</script>

<style scoped>
.timeline-step { line-height: 1.6; }
.step-target { font-size: 12px; color: var(--el-color-primary); margin-left: 8px; }
.step-error { font-size: 12px; color: var(--el-color-danger); margin-top: 2px; }
</style>
