<template>
  <div class="execution-view">
    <PageHeader title="执行记录" :crumbs="['首页', '执行记录']">
      <template #actions>
        <el-select
          v-model="filters.project_id"
          placeholder="选择项目"
          clearable
          style="width: 160px"
          @change="loadData"
        >
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select
          v-model="filters.status"
          placeholder="执行状态"
          clearable
          style="width: 140px"
          @change="loadData"
        >
          <el-option label="全部" value="" />
          <el-option label="进行中" value="running" />
          <el-option label="成功" value="passed" />
          <el-option label="失败" value="failed" />
          <el-option label="待执行" value="pending" />
        </el-select>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" class="mt-16">
      <el-table :data="executionStore.executions" v-loading="executionStore.loading" stripe>
        <el-table-column prop="execution_id" label="执行 ID" width="180">
          <template #default="{ row }">
            <code class="execution-id">{{ row.execution_id }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="case_id" label="用例 ID" width="90" />
        <el-table-column prop="env" label="环境" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.env }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="执行状态" width="110">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" width="110">
          <template #default="{ row }">
            <StatusBadge v-if="row.result" :status="row.result" />
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration_ms) }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row.execution_id)">
              查看详情
            </el-button>
            <el-button
              v-if="['passed','failed','error'].includes(row.status || row.result)"
              size="small" type="success" link @click="viewReport(row.execution_id)"
            >
              报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer
      v-model="detailDrawer"
      title="执行详情"
      size="760px"
      direction="rtl"
      @close="closeDetail"
    >
      <div v-if="executionStore.currentExecution" class="execution-detail">
        <el-alert
          v-if="aiHealedCount > 0"
          type="warning"
          :closable="false"
          show-icon
          class="mb-16"
        >
          <template #title>
            本次执行有 <strong>{{ aiHealedCount }}</strong> 个步骤触发了 AI 自动修复。
          </template>
        </el-alert>

        <el-descriptions :column="2" border size="small" class="mb-16">
          <el-descriptions-item label="执行 ID">
            <code class="execution-id">{{ executionStore.currentExecution.execution_id }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="结果">
            <StatusBadge :status="executionStore.currentExecution.result || executionStore.currentExecution.status" />
          </el-descriptions-item>
          <el-descriptions-item label="用例 ID">
            {{ executionStore.currentExecution.case_id }}
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ formatDuration(executionStore.currentExecution.duration_ms) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间" :span="2">
            {{ formatTime(executionStore.currentExecution.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="executionStore.currentExecution.finished_at"
            label="结束时间"
          >
            {{ formatTime(executionStore.currentExecution.finished_at) }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="['passed','failed','error'].includes(executionStore.currentExecution.status)"
            label="报告"
          >
            <el-button type="success" size="small" link
              @click="viewReport(executionStore.currentExecution.execution_id)">
              查看统一报告
            </el-button>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="executionStore.currentExecution.error_msg"
          type="error"
          :title="executionStore.currentExecution.error_msg"
          :closable="false"
          class="mb-16"
        />

        <el-tabs v-model="activeTab">
          <el-tab-pane :label="`步骤详情 (${executionStore.currentSteps.length})`" name="steps">
            <div class="step-list">
              <el-empty
                v-if="executionStore.currentSteps.length === 0"
                description="当前还没有步骤结果"
              />

              <div
                v-for="step in executionStore.currentSteps"
                :key="step.step_no"
                class="step-card"
                :class="[`step-${step.status}`, { 'step-ai-healed': step.matched_strategy_type === 'ai_healed' }]"
              >
                <div class="step-header">
                  <div class="step-heading">
                    <div class="step-index">步骤 {{ step.step_no }}</div>
                    <div class="step-action">{{ step.action || '-' }}</div>
                  </div>
                  <div class="step-summary">
                    <StatusBadge :status="step.status" />
                    <span class="step-duration">{{ formatDuration(step.duration_ms) }}</span>
                  </div>
                </div>

                <div class="step-grid">
                  <div class="field">
                    <span class="label">目标</span>
                    <code class="value-block">{{ step.target || '-' }}</code>
                  </div>
                  <div class="field">
                    <span class="label">入参</span>
                    <code class="value-block">{{ formatValue(step.value) }}</code>
                  </div>
                  <div class="field" v-if="step.actual">
                    <span class="label">实际结果</span>
                    <code class="value-block">{{ formatValue(step.actual) }}</code>
                  </div>
                  <div class="field" v-if="step.matched_strategy_type">
                    <span class="label">命中策略</span>
                    <div class="strategy-row">
                      <el-tag
                        size="small"
                        :type="step.matched_strategy_type === 'ai_healed' ? 'warning' : 'success'"
                      >
                        {{ step.matched_strategy_type }}
                      </el-tag>
                      <span v-if="step.matched_strategy_priority" class="muted">
                        P{{ step.matched_strategy_priority }}
                      </span>
                    </div>
                    <code class="value-block">{{ formatValue(step.matched_strategy_value) }}</code>
                  </div>
                  <div class="field" v-if="step.error_msg">
                    <span class="label">错误信息</span>
                    <div class="error-text">{{ step.error_msg }}</div>
                  </div>
                </div>

                <div v-if="step.screenshot" class="step-footer">
                  <el-image
                    :src="toScreenshotUrl(step.screenshot)"
                    fit="cover"
                    :preview-src-list="[toScreenshotUrl(step.screenshot)]"
                    class="step-thumb"
                    preview-teleported
                  />
                  <div class="step-footer-actions">
                    <span class="muted">失败截图</span>
                    <el-link :href="toScreenshotUrl(step.screenshot)" target="_blank" type="primary">
                      打开原图
                    </el-link>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`调试日志 (${executionStore.debugLogs.length})`" name="debug">
            <LogViewer :logs="normalizedDebugLogs" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <!-- Report Drawer (B-03) -->
    <el-drawer v-model="reportDrawer" title="统一报告" size="860px" direction="rtl">
      <UnifiedReport
        v-if="reportData"
        :report="reportData"
        @repair-step="handleRepairStep"
      />
      <el-empty v-else description="加载报告中..." />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import LogViewer from '../../components/LogViewer.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import UnifiedReport from '../../components/UnifiedReport.vue'
import { useExecutionStore } from '../../stores/execution'
import { useProjectsStore } from '../../stores/projects'
import { reportsApi } from '../../api'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const executionStore = useExecutionStore()

const detailDrawer = ref(false)
const activeTab = ref('steps')
const filters = ref({ project_id: null, status: '' })
const reportDrawer = ref(false)
const reportData = ref(null)
let autoRefreshTimer = null

onMounted(async () => {
  await projectsStore.fetchProjects()

  // B-02: auto-run from CasesView "立即运行" quick link
  if (route.query.auto_run === '1' && route.query.case_id) {
    filters.value.project_id = route.query.project_id ? parseInt(route.query.project_id) : null
    try {
      const result = await executionStore.createExecution({
        case_ids: [parseInt(route.query.case_id)],
        project_id: filters.value.project_id,
        env: 'test',
      })
      ElMessage.success(`自动执行已触发：${result.execution_ids[0]}`)
      detailDrawer.value = true
      await viewDetail(result.execution_ids[0])
    } catch (e) {
      ElMessage.error('自动执行失败：' + (e.message || '未知错误'))
    }
  }

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

const aiHealedCount = computed(() =>
  (executionStore.currentSteps || []).filter(step => step.matched_strategy_type === 'ai_healed').length,
)

const normalizedDebugLogs = computed(() =>
  (executionStore.debugLogs || []).map((log) => ({
    timestamp: log.ts ? new Date(log.ts * 1000).toISOString() : '',
    level: String(log.level || 'info').toUpperCase(),
    message: log.message || '',
    meta: log.meta || {},
  })),
)

async function loadData() {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.status) params.status = filters.value.status
  await executionStore.fetchExecutions(params)
}

async function viewDetail(executionId) {
  detailDrawer.value = true
  activeTab.value = 'steps'
  await executionStore.fetchExecution(executionId)
  executionStore.startStreaming(executionId)
  executionStore.startDebugStreaming(executionId)
}

function closeDetail() {
  detailDrawer.value = false
  executionStore.stopStreaming()
  executionStore.stopDebugStreaming()
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(durationMs) {
  const value = Number(durationMs || 0)
  if (value < 1000) return `${value}ms`
  if (value < 60000) return `${(value / 1000).toFixed(2)}s`
  const minutes = Math.floor(value / 60000)
  const seconds = ((value % 60000) / 1000).toFixed(1)
  return `${minutes}m ${seconds}s`
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '-'
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return text.length > 400 ? `${text.slice(0, 400)}...` : text
}

function toScreenshotUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//.test(path)) return path
  const normalized = String(path).replace(/\\/g, '/').replace(/^\.?\/*/, '')
  if (normalized.startsWith('screenshots/')) {
    return `/screenshots/${normalized.slice('screenshots/'.length)}`
  }
  return `/${normalized}`
}

async function viewReport(executionId) {
  reportDrawer.value = true
  reportData.value = null
  try {
    const data = await reportsApi.get(executionId)
    reportData.value = data
  } catch {
    reportData.value = null
    ElMessage.error('报告加载失败')
  }
}

function handleRepairStep(step) {
  router.push({
    path: '/ai-tools',
    query: { tab: 'repair-audit', locator_key: step.target },
  })
}
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}

.mb-16 {
  margin-bottom: 16px;
}

.execution-id {
  font-size: 12px;
}

.muted {
  color: var(--el-text-color-secondary);
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-card {
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 16px;
  background: #fff;
}

.step-passed {
  border-color: #cdecc8;
}

.step-failed {
  border-color: #f5c2c7;
  background: #fff8f8;
}

.step-ai-healed {
  box-shadow: inset 0 0 0 1px #f2c97d;
}

.step-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.step-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-index {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.step-action {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  text-transform: uppercase;
}

.step-summary {
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-duration {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.step-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.value-block {
  display: block;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.strategy-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-text {
  padding: 10px 12px;
  background: #fff1f0;
  color: #cf1322;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.step-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--el-border-color);
}

.step-thumb {
  width: 120px;
  height: 72px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  overflow: hidden;
  flex-shrink: 0;
}

.step-footer-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

@media (max-width: 768px) {
  .step-header,
  .step-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .step-thumb {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
  }
}
</style>
