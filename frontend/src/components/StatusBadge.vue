<template>
  <el-tag :type="tagType" :size="size" :effect="effect" :hit="hit" :disable-transitions="disableTransitions" :round="round">
    <slot>{{ displayText }}</slot>
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 执行结果或状态值：passed, failed, error, running, pending, blocked, skipped */
  status: {
    type: String,
    default: '',
  },
  /** 覆盖显示文本（可选） */
  text: {
    type: String,
    default: '',
  },
  /** Element Plus el-tag size */
  size: {
    type: String,
    default: 'small',
  },
  /** Element Plus el-tag effect */
  effect: {
    type: String,
    default: 'light',
  },
  /** Element Plus el-tag hit */
  hit: {
    type: Boolean,
    default: false,
  },
  /** Element Plus el-tag disable-transitions */
  disableTransitions: {
    type: Boolean,
    default: false,
  },
  /** Element Plus el-tag round */
  round: {
    type: Boolean,
    default: false,
  },
  /**
   * 文本映射表，默认：
   *   passed  → 通过
   *   failed  → 失败
   *   error   → 异常
   *   running → 进行中
   *   pending → 待执行
   *   blocked → 阻塞
   *   skipped → 跳过
   */
  mapping: {
    type: Object,
    default: null,
  },
})

// Element Plus tag type 映射
const TAG_TYPE_MAP = {
  passed:  'success',
  success: 'success',
  failed:  'danger',
  failure: 'danger',
  error:   'danger',
  danger:  'danger',
  running: 'warning',
  pending: 'info',
  blocked: 'warning',
  skipped: 'info',
  enabled: 'success',
  disabled:'info',
}

const TEXT_MAP = {
  passed:  '通过',
  success: '成功',
  failed:  '失败',
  failure: '失败',
  error:   '异常',
  running: '进行中',
  pending: '待执行',
  blocked: '阻塞',
  skipped: '跳过',
  enabled: '已启用',
  disabled:'已禁用',
}

const tagType = computed(() => {
  if (props.mapping) {
    return props.mapping[props.status] || 'info'
  }
  return TAG_TYPE_MAP[props.status?.toLowerCase()] || 'info'
})

const displayText = computed(() => {
  if (props.text) return props.text
  if (props.mapping) return props.status
  return TEXT_MAP[props.status?.toLowerCase()] || props.status || '-'
})
</script>
