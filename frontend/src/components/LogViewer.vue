<template>
  <div class="log-viewer" :class="{ 'is-expanded': isExpanded }">
    <!-- 工具栏 -->
    <div class="log-toolbar">
      <span class="log-title">日志</span>
      <div class="log-controls">
        <el-select v-model="levelFilter" size="small" placeholder="日志级别" clearable style="width: 100px">
          <el-option label="INFO" value="INFO" />
          <el-option label="WARN" value="WARN" />
          <el-option label="ERROR" value="ERROR" />
          <el-option label="DEBUG" value="DEBUG" />
        </el-select>
        <el-button size="small" @click="scrollToBottom" title="滚动到底部">
          <el-icon><Bottom /></el-icon>
        </el-button>
        <el-button size="small" @click="toggleExpand" :icon="isExpanded ? 'Top' : 'Bottom'" title="折叠/展开" />
      </div>
    </div>

    <!-- 日志内容 -->
    <div v-show="isExpanded" ref="logContainerRef" class="log-container" @scroll="onScroll">
      <div v-if="filteredLogs.length === 0" class="log-empty">暂无日志</div>
      <div
        v-for="(log, idx) in filteredLogs"
        :key="idx"
        class="log-line"
        :class="`log-${log.level?.toLowerCase() || 'info'}`"
      >
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="log-level" :class="`level-${log.level?.toLowerCase() || 'info'}`">[{{ log.level || 'INFO' }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Bottom } from '@element-plus/icons-vue'

const props = defineProps({
  /** @type {{ timestamp?: string, level?: string, message: string }[]} */
  logs: {
    type: Array,
    default: () => [],
  },
  autoScroll: {
    type: Boolean,
    default: true,
  },
})

const logContainerRef = ref(null)
const levelFilter = ref('')
const isExpanded = ref(true)
const userScrolled = ref(false)

const filteredLogs = computed(() => {
  if (!levelFilter.value) return props.logs
  return props.logs.filter(log => log.level?.toUpperCase() === levelFilter.value.toUpperCase())
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`
}

async function scrollToBottom() {
  await nextTick()
  const el = logContainerRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function onScroll() {
  const el = logContainerRef.value
  if (!el) return
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10
  userScrolled.value = !atBottom
}

watch(filteredLogs, async () => {
  if (props.autoScroll && !userScrolled.value) {
    await nextTick()
    scrollToBottom()
  }
}, { deep: true })

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

// 暴露方法给父组件
defineExpose({ scrollToBottom })
</script>

<style scoped>
.log-viewer {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
}

.log-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
}

.log-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.log-controls {
  display: flex;
  gap: 6px;
  align-items: center;
}

.log-container {
  max-height: 300px;
  overflow-y: auto;
  background: #1e1e1e;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-empty {
  color: #666;
  padding: 16px;
  text-align: center;
}

.log-line {
  display: flex;
  gap: 8px;
  padding: 1px 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-time {
  color: #888;
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  font-weight: 600;
}

.level-info    { color: #4a90e2; }
.level-warn    { color: #e6a23c; }
.level-warning { color: #e6a23c; }
.level-error   { color: #f56c6c; }
.level-debug   { color: #909399; }

.log-message { color: #e0e0e0; }
.log-warn .log-message,
.log-warning .log-message { color: #e6a23c; }
.log-error .log-message   { color: #f56c6c; }
</style>
