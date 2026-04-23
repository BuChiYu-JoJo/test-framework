<template>
  <div class="performance-view">
    <PageHeader title="性能检测" :crumbs="['首页', '性能检测']">
      <template #actions>
        <el-select v-model="filters.project_id" placeholder="选择项目" clearable size="default" style="width: 160px" @change="loadData">
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="filters.status" placeholder="任务状态" clearable size="default" style="width: 140px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="待执行" value="pending" />
          <el-option label="执行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button type="primary" @click="showCreateDialog"><el-icon><Plus /></el-icon>新建任务</el-button>
        <el-button @click="loadData"><el-icon><Refresh /></el-icon>刷新</el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" class="mt-16">
      <el-table :data="performanceStore.tasks" v-loading="performanceStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="target_url" label="目标URL" min-width="220" show-overflow-tooltip>
          <template #default="{ row }"><el-link :href="row.target_url" target="_blank" type="primary" style="font-size:12px">{{ row.target_url }}</el-link></template>
        </el-table-column>
        <el-table-column prop="device" label="设备" width="80">
          <template #default="{ row }"><el-tag size="small">{{ row.device }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="network" label="网络" width="80">
          <template #default="{ row }"><el-tag size="small" type="info">{{ row.network }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" size="small" type="info">待执行</el-tag>
            <el-tag v-else-if="row.status === 'running'" size="small" type="warning">执行中</el-tag>
            <el-tag v-else-if="row.status === 'completed'" size="small" type="success">已完成</el-tag>
            <el-tag v-else-if="row.status === 'failed'" size="small" type="danger">失败</el-tag>
            <el-tag v-else size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="评分" width="80">
          <template #default="{ row }">
            <span v-if="row.score > 0" class="score-badge" :class="scoreClass(row.score)">{{ row.score.toFixed(1) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row.id)">查看详情</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建任务弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建性能检测任务" width="500px">
      <el-form :model="createForm" label-width="90px" ref="createFormRef">
        <el-form-item label="任务名称" prop="name" :rules="[{ required: true, message: '请输入任务名称' }]">
          <el-input v-model="createForm.name" placeholder="如：官网首页性能" />
        </el-form-item>
        <el-form-item label="所属项目" prop="project_id" :rules="[{ required: true, message: '请选择项目' }]">
          <el-select v-model="createForm.project_id" placeholder="请选择项目" style="width:100%">
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标URL" prop="target_url" :rules="[{ required: true, message: '请输入URL' }]">
          <el-input v-model="createForm.target_url" placeholder="https://www.example.com" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-radio-group v-model="createForm.device">
            <el-radio label="desktop">桌面端</el-radio>
            <el-radio label="mobile">移动端</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="网络类型">
          <el-select v-model="createForm.network" style="width:100%">
            <el-option label="WiFi" value="wifi" />
            <el-option label="4G" value="4g" />
            <el-option label="Slow 2G" value="slow2g" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建并执行</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情抽屉 -->
    <el-drawer v-model="detailDrawer" title="任务详情" size="700px" direction="rtl">
      <div v-if="performanceStore.currentTask" class="task-detail">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务名称">{{ performanceStore.currentTask.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="performanceStore.currentTask.status === 'completed'" size="small" type="success">已完成</el-tag>
            <el-tag v-else-if="performanceStore.currentTask.status === 'running'" size="small" type="warning">执行中</el-tag>
            <el-tag v-else-if="performanceStore.currentTask.status === 'failed'" size="small" type="danger">失败</el-tag>
            <el-tag v-else size="small" type="info">{{ performanceStore.currentTask.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="设备">{{ performanceStore.currentTask.device }}</el-descriptions-item>
          <el-descriptions-item label="网络">{{ performanceStore.currentTask.network }}</el-descriptions-item>
          <el-descriptions-item label="评分" :span="2">
            <span v-if="performanceStore.currentTask.score > 0" class="score-badge large" :class="scoreClass(performanceStore.currentTask.score)">
              {{ performanceStore.currentTask.score.toFixed(1) }}
            </span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="目标URL" :span="2">
            <el-link :href="performanceStore.currentTask.target_url" target="_blank" type="primary">
              {{ performanceStore.currentTask.target_url }}
            </el-link>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 错误信息 -->
        <div v-if="performanceStore.currentTask.error_msg" class="error-block">
          <el-alert type="error" :title="performanceStore.currentTask.error_msg" :closable="false" />
        </div>

        <!-- 性能指标 -->
        <div v-if="performanceStore.currentTask.metrics && Object.keys(performanceStore.currentTask.metrics).length > 0" class="metrics-block">
          <h4 class="section-title">性能指标</h4>
          <el-row :gutter="12">
            <el-col :span="8" v-for="(value, key) in formatMetrics(performanceStore.currentTask.metrics)" :key="key">
              <div class="metric-card" :class="'metric-' + key">
                <div class="metric-label">{{ metricLabel(key) }}</div>
                <div class="metric-value">{{ value }}</div>
                <div class="metric-score" v-if="metricScore(key, performanceStore.currentTask.metrics)">
                  评分: <span :class="scoreClass(metricScore(key, performanceStore.currentTask.metrics))">{{ metricScore(key, performanceStore.currentTask.metrics).toFixed(0) }}</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 资源列表 -->
        <div v-if="performanceStore.currentTask.resources && performanceStore.currentTask.resources.entries && performanceStore.currentTask.resources.entries.length > 0" class="resources-block">
          <h4 class="section-title">资源请求 ({{ performanceStore.currentTask.resources.entries.length }})</h4>
          <el-table :data="performanceStore.currentTask.resources.entries" stripe size="small" max-height="300">
            <el-table-column prop="name" label="资源" min-width="200" show-overflow-tooltip>
              <template #default="{ row }"><el-link :href="row.name" target="_blank" type="primary" style="font-size:12px">{{ row.name }}</el-link></template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时(ms)" width="100">
              <template #default="{ row }">{{ row.duration?.toFixed(2) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 时间信息 -->
        <el-descriptions :column="2" border size="small" class="time-info">
          <el-descriptions-item label="创建时间">{{ formatTime(performanceStore.currentTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(performanceStore.currentTask.finished_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '../../stores/projects'
import { usePerformanceStore } from '../../stores/performance'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'

const projectsStore = useProjectsStore()
const performanceStore = usePerformanceStore()

const filters = ref({ project_id: null, status: '' })
const createDialogVisible = ref(false)
const creating = ref(false)
const detailDrawer = ref(false)
const createFormRef = ref(null)

const createForm = ref({
  name: '',
  project_id: null,
  target_url: '',
  device: 'desktop',
  network: 'wifi',
})

let autoRefreshTimer = null

onMounted(async () => {
  await projectsStore.fetchProjects()
  await loadData()
  autoRefreshTimer = setInterval(loadData, 10000)
})

async function loadData() {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.status) params.status = filters.value.status
  await performanceStore.fetchTasks(params)
}

function showCreateDialog() {
  createForm.value = { name: '', project_id: null, target_url: '', device: 'desktop', network: 'wifi' }
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    await performanceStore.createTask(createForm.value)
    createDialogVisible.value = false
    ElMessage.success('任务已创建')
    await loadData()
  } finally {
    creating.value = false
  }
}

async function viewDetail(taskId) {
  detailDrawer.value = true
  await performanceStore.fetchTask(taskId)
}

async function handleDelete(taskId) {
  try {
    await ElMessageBox.confirm('确认删除该任务?', '删除确认', { type: 'warning' })
    await performanceStore.deleteTask(taskId)
    ElMessage.success('删除成功')
  } catch {
    // 取消
  }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatMetrics(metrics) {
  const result = {}
  const exclude = ['_error']
  for (const [k, v] of Object.entries(metrics)) {
    if (exclude.includes(k)) continue
    if (k === 'cls') {
      result[k] = v.toFixed(4)
    } else if (typeof v === 'number') {
      result[k] = v.toFixed(2) + ' ms'
    } else {
      result[k] = v
    }
  }
  return result
}

function metricLabel(key) {
  const labels = {
    fcp: 'FCP 首内容绘制',
    lcp: 'LCP 最大内容绘制',
    fid: 'FID 首次输入延迟',
    cls: 'CLS 累积布局偏移',
    ttfb: 'TTFB 首字节时间',
    render: '渲染耗时',
  }
  return labels[key] || key
}

function metricScore(key, metrics) {
  if (!metrics || !metrics[key] || metrics[key] === 0) return null
  const thresholds = {
    fcp: [1800, 3000], lcp: [2500, 4000], fid: [100, 300],
    cls: [0.1, 0.25], ttfb: [800, 1800], render: [2000, 5000],
  }
  if (!thresholds[key]) return null
  const [good, poor] = thresholds[key]
  const val = metrics[key]
  if (key === 'cls') {
    if (val <= good) return 100
    if (val >= poor) return 0
    return 100 * (1 - (val - good) / (poor - good))
  }
  if (val <= good) return 100
  if (val >= poor) return 0
  return 100 * (1 - (val - good) / (poor - good))
}

function scoreClass(score) {
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-medium'
  return 'score-poor'
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
.score-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 12px;
}
.score-badge.large { font-size: 16px; padding: 4px 12px; }
.score-good { background: #e3f4e8; color: #67c23a; }
.score-medium { background: #fdf6ec; color: #e6a23c; }
.score-poor { background: #fde2e2; color: #f56c6c; }
.error-block { margin: 16px 0; }
.metrics-block { margin-top: 20px; }
.section-title { font-size: 14px; color: #333; margin-bottom: 12px; }
.metric-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  text-align: center;
}
.metric-label { font-size: 12px; color: #666; margin-bottom: 6px; }
.metric-value { font-size: 18px; font-weight: bold; color: #333; }
.metric-score { font-size: 12px; color: #999; margin-top: 4px; }
.resources-block { margin-top: 20px; }
.time-info { margin-top: 16px; }
</style>