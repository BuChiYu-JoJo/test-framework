<template>
  <div class="execution-view">
    <PageHeader title="执行记录" :crumbs="['首页', '执行记录']">
      <template #actions>
        <el-select v-model="filters.project_id" placeholder="选择项目" clearable size="default" style="width: 160px" @change="loadData">
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="filters.status" placeholder="执行状态" clearable size="default" style="width: 140px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="进行中" value="running" />
          <el-option label="成功" value="passed" />
          <el-option label="失败" value="failed" />
          <el-option label="待执行" value="pending" />
        </el-select>
        <el-button @click="loadData"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" class="mt-16">
      <el-table :data="executionStore.executions" v-loading="executionStore.loading" stripe>
        <el-table-column prop="execution_id" label="执行ID" width="180">
          <template #default="{ row }"><code style="font-size:12px">{{ row.execution_id }}</code></template>
        </el-table-column>
        <el-table-column prop="case_id" label="用例ID" width="80" />
        <el-table-column prop="env" label="环境" width="80">
          <template #default="{ row }"><el-tag size="small">{{ row.env }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }"><StatusBadge :status="row.status" /></template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="100">
          <template #default="{ row }">
            <StatusBadge v-if="row.result" :status="row.result" />
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="100">
          <template #default="{ row }">{{ row.duration_ms }}ms</template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row.execution_id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="detailDrawer" title="执行详情" size="650px" direction="rtl" @close="closeDetail">
      <div v-if="executionStore.currentExecution" class="execution-detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="执行ID"><code>{{ executionStore.currentExecution.execution_id }}</code></el-descriptions-item>
          <el-descriptions-item label="状态">
            <StatusBadge :status="executionStore.currentExecution.result || executionStore.currentExecution.status" />
          </el-descriptions-item>
          <el-descriptions-item label="用例ID">{{ executionStore.currentExecution.case_id }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ executionStore.currentExecution.duration_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="开始" :span="2">{{ formatTime(executionStore.currentExecution.started_at) }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="executionStore.currentExecution.error_msg" class="error-block">
          <el-alert type="error" :title="executionStore.currentExecution.error_msg" :closable="false" />
        </div>

        <el-tabs v-model="activeTab" class="detail-tabs">
          <el-tab-pane label="执行步骤" name="steps">
            <el-table :data="executionStore.currentSteps" stripe size="small">
              <el-table-column prop="step_no" label="#" width="50" />
              <el-table-column prop="action" label="动作" width="110" />
              <el-table-column prop="target" label="目标" min-width="140" show-overflow-tooltip />
              <el-table-column label="命中策略" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <div v-if="row.matched_strategy_type" class="matched-strategy-cell">
                    <el-tag size="small" type="success">{{ row.matched_strategy_type }}</el-tag>
                    <span v-if="row.matched_strategy_priority" class="matched-priority">
                      P{{ row.matched_strategy_priority }}
                    </span>
                  </div>
                  <span v-else class="matched-empty">-</span>
                </template>
              </el-table-column>
              <el-table-column label="命中值" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                  <code v-if="row.matched_strategy_value" class="matched-value">
                    {{ row.matched_strategy_value }}
                  </code>
                  <span v-else class="matched-empty">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="value" label="值" width="100" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }"><StatusBadge :status="row.status" /></template>
              </el-table-column>
              <el-table-column prop="duration_ms" label="耗时" width="70">
                <template #default="{ row }">{{ row.duration_ms }}ms</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="调试日志" name="debug">
            <div class="debug-panel">
              <div class="debug-toolbar">
                <span class="debug-hint">实时接收后端调试信息</span>
                <el-tag size="small" type="info">{{ executionStore.debugLogs.length }} 条</el-tag>
              </div>
              <div class="debug-log-view" ref="logContainer">
                <div v-for="(log, i) in executionStore.debugLogs" :key="i" class="debug-line">
                  <span class="debug-ts">{{ log.ts ? new Date(log.ts * 1000).toLocaleTimeString('zh-CN', { hour12: false }) : '' }}</span>
                  <span class="debug-level" :class="'level-' + log.level">{{ log.level === 'error' ? '❌' : '📌' }}</span>
                  <span class="debug-msg">{{ log.message }}</span>
                </div>
                <div v-if="executionStore.debugLogs.length === 0" class="debug-empty">
                  暂无日志，等待执行中...
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '../../stores/projects'
import { useExecutionStore } from '../../stores/execution'
import StatusBadge from '../../components/StatusBadge.vue'
import PageHeader from '../../components/PageHeader.vue'

const route = useRoute()
const projectsStore = useProjectsStore()
const executionStore = useExecutionStore()

const detailDrawer = ref(false)
const activeTab = ref('steps')
const filters = ref({ project_id: null, status: '' })
let autoRefreshTimer = null

onMounted(async () => {
  await projectsStore.fetchProjects()
  await loadData()
  autoRefreshTimer = setInterval(loadData, 10000)
})

onUnmounted(() => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
  executionStore.stopStreaming()
  executionStore.stopDebugStreaming()
})

watch(() => route.path, () => {
  if (route.path === '/execution') loadData()
})

async function loadData() {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.status) params.status = filters.value.status
  await executionStore.fetchExecutions(params)
}

async function viewDetail(executionId) {
  detailDrawer.value = true
  activeTab.value = 'steps'
  // 先加载已有数据（已完成的从 DB 取，正在运行的取当前已收集的）
  await executionStore.fetchExecution(executionId)
  // 启动 SSE 实时追加步骤 + 调试日志
  executionStore.startStreaming(executionId)
  executionStore.startDebugStreaming(executionId)
}

function closeDetail() {
  detailDrawer.value = false
  executionStore.stopStreaming()
  executionStore.stopDebugStreaming()
}

function statusType(s) {
  return { pending: 'info', running: 'warning', passed: 'success', failed: 'danger', error: 'danger' }[s] || 'info'
}

function resultType(r) {
  return { passed: 'success', failed: 'danger', error: 'danger' }[r] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
.error-block { margin: 16px 0; }
.steps-block { margin-top: 20px; }
.steps-block h4 { margin-bottom: 12px; font-size: 14px; color: #333; }
.detail-tabs { margin-top: 16px; }
.debug-panel { display: flex; flex-direction: column; height: 400px; }
.debug-toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
.debug-hint { font-size: 12px; color: #999; }
.debug-log-view { flex: 1; background: #1e1e1e; border-radius: 6px; padding: 12px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6; }
.debug-line { display: flex; gap: 8px; color: #d4d4d4; }
.debug-ts { color: #666; flex-shrink: 0; }
.debug-level { flex-shrink: 0; width: 16px; }
.level-error { color: #f48771; }
.debug-msg { word-break: break-all; color: #9cdcfe; }
.debug-empty { color: #555; text-align: center; padding-top: 40px; }
.matched-strategy-cell { display: flex; align-items: center; gap: 6px; }
.matched-priority { font-size: 12px; color: #909399; }
.matched-value { font-size: 12px; color: var(--el-color-primary); background: var(--el-fill-color-light); padding: 2px 6px; border-radius: 4px; word-break: break-all; }
.matched-empty { color: #c0c4cc; }
</style>
