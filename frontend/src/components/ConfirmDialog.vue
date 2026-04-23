<template>
  <el-dialog
    v-model="visible"
    :title="config.title"
    :width="config.width"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="onClosed"
  >
    <div class="confirm-body">
      <el-icon v-if="config.type !== 'none'" class="confirm-icon" :class="`icon-${config.type}`">
        <component :is="iconComponent" />
      </el-icon>
      <span class="confirm-message">{{ config.message }}</span>
    </div>
    <template #footer>
      <el-button @click="handleCancel">{{ config.cancelText }}</el-button>
      <el-button :type="config.confirmType" :loading="loading" @click="handleConfirm">
        {{ config.confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { WarningFilled, CircleCheckFilled, CircleCloseFilled, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  /** v-model: 控制显示 */
  modelValue: {
    type: Boolean,
    default: false,
  },
  /** 弹窗标题 */
  title: {
    type: String,
    default: '确认操作',
  },
  /** 提示内容 */
  message: {
    type: String,
    default: '确定要执行此操作吗？',
  },
  /** 弹窗类型：warning | danger | success | info | none */
  type: {
    type: String,
    default: 'warning',
  },
  /** 确认按钮文本 */
  confirmText: {
    type: String,
    default: '确定',
  },
  /** 取消按钮文本 */
  cancelText: {
    type: String,
    default: '取消',
  },
  /** 确认按钮类型 */
  confirmType: {
    type: String,
    default: 'primary',
  },
  /** 宽度 */
  width: {
    type: String,
    default: '420px',
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const loading = ref(false)
const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const config = computed(() => ({
  title: props.title,
  message: props.message,
  type: props.type,
  confirmText: props.confirmText,
  cancelText: props.cancelText,
  confirmType: props.confirmType,
  width: props.width,
}))

const iconComponent = computed(() => {
  const map = {
    warning: WarningFilled,
    danger:  CircleCloseFilled,
    success: CircleCheckFilled,
    info:    InfoFilled,
  }
  return map[props.type] || WarningFilled
})

function handleCancel() {
  visible.value = false
  emit('cancel')
}

async function handleConfirm() {
  loading.value = true
  emit('confirm', {
    done: () => { loading.value = false; visible.value = false },
    close: () => { loading.value = false; visible.value = false },
  })
}

function onClosed() {
  loading.value = false
}
</script>

<style scoped>
.confirm-body {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 4px 0;
}

.confirm-icon {
  font-size: 20px;
  margin-top: 2px;
  flex-shrink: 0;
}

.icon-warning { color: var(--el-color-warning); }
.icon-danger  { color: var(--el-color-danger); }
.icon-success { color: var(--el-color-success); }
.icon-info    { color: var(--el-color-info); }

.confirm-message {
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
}
</style>
