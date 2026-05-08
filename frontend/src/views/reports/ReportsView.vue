<template>
  <div class="reports-view">
    <PageHeader title="报告中心" :crumbs="['首页', '报告中心']" />
    <el-card shadow="never" class="mt-16">
      <el-table :data="reports" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="报告名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目" width="140" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'completed' || row.status === 'passed'" size="small" type="success">完成</el-tag>
            <el-tag v-else-if="row.status === 'failed'" size="small" type="danger">失败</el-tag>
            <el-tag v-else size="small" type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="passed" label="通过/总数" width="100">
          <template #default="{ row }">
            <span style="color:#67c23a">{{ row.passed || 0 }}</span> /
            <span>{{ (row.passed || 0) + (row.failed || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openUnifiedReport(row)">统一报告</el-button>
            <el-button size="small" link @click="viewReport(row)">HTML</el-button>
            <el-button size="small" type="success" link @click="downloadReport(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Unified Report Drawer (B-04 / B-08) -->
    <el-drawer v-model="reportDrawerVisible" title="统一报告详情" size="900px" direction="rtl">
      <div v-if="reportLoading" v-loading="true" style="min-height:200px" />
      <UnifiedReport
        v-else-if="unifiedReportData"
        :report="unifiedReportData"
        @repair-step="goRepairStep"
      />
      <el-empty v-else description="报告数据为空" />

      <!-- B-04: Failed → AI repair + rerun shortcut -->
      <template v-if="unifiedReportData && hasFailedSteps">
        <el-divider />
        <div style="display:flex;gap:12px;justify-content:flex-end">
          <el-button type="warning" @click="goRepairAudit">
            前往修复审计
          </el-button>
          <el-button type="primary" @click="rerunExecution">
            重新执行此用例
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { reportsApi, executionsApi } from '../../api/index'
import PageHeader from '../../components/PageHeader.vue'
import UnifiedReport from '../../components/UnifiedReport.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const reports = ref([])
const loading = ref(false)
const reportDrawerVisible = ref(false)
const reportLoading = ref(false)
const unifiedReportData = ref(null)
const currentReportRow = ref(null)

const hasFailedSteps = computed(() => {
  if (!unifiedReportData.value?.steps) return false
  return unifiedReportData.value.steps.some(s => s.status === 'failed')
})

onMounted(() => loadReports())

async function loadReports() {
  loading.value = true
  try {
    const res = await api.get('/reports')
    reports.value = res.data?.data || res.data || res || []
    if (!Array.isArray(reports.value)) reports.value = []
  } catch {
    reports.value = []
  } finally {
    loading.value = false
  }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function viewReport(row) {
  if (row.html_path) {
    window.open(row.html_path, '_blank')
  } else {
    ElMessage.info('报告路径未配置')
  }
}

function downloadReport(row) {
  if (row.download_url) {
    window.open(row.download_url, '_blank')
  } else {
    ElMessage.info('暂不支持下载')
  }
}

async function openUnifiedReport(row) {
  currentReportRow.value = row
  reportDrawerVisible.value = true
  reportLoading.value = true
  unifiedReportData.value = null
  try {
    const executionId = row.execution_id || row.id
    const data = await reportsApi.get(executionId)
    unifiedReportData.value = data
  } catch {
    unifiedReportData.value = null
    ElMessage.error('报告加载失败')
  } finally {
    reportLoading.value = false
  }
}

function goRepairStep(step) {
  router.push({
    path: '/ai-tools',
    query: { tab: 'repair-audit', locator_key: step.target },
  })
}

function goRepairAudit() {
  router.push({
    path: '/ai-tools',
    query: { tab: 'repair-audit' },
  })
}

async function rerunExecution() {
  if (!currentReportRow.value) return
  const row = currentReportRow.value
  try {
    const result = await executionsApi.create({
      case_ids: [row.case_id || row.id],
      project_id: row.project_id,
      env: row.env || 'test',
    })
    ElMessage.success(`重新执行已触发：${result.execution_ids?.[0] || ''}`)
    reportDrawerVisible.value = false
    router.push({ path: '/execution' })
  } catch (e) {
    ElMessage.error('重新执行失败：' + (e.message || ''))
  }
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
</style>
