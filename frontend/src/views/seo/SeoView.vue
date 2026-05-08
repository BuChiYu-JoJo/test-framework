<template>
  <div class="seo-view">
    <PageHeader title="SEO 检测" :crumbs="['首页', 'SEO 检测']">
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
      <el-table :data="seoStore.tasks" v-loading="seoStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="target_url" label="目标URL" min-width="220" show-overflow-tooltip>
          <template #default="{ row }"><el-link :href="row.target_url" target="_blank" type="primary" style="font-size:12px">{{ row.target_url }}</el-link></template>
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
            <span v-if="row.score > 0" class="score-badge" :class="scoreClass(row.score)">{{ row.score }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="问题统计" width="150">
          <template #default="{ row }">
            <span v-if="row.status === 'completed'" class="issue-counts">
              <span class="critical">{{ row.critical_count || 0 }}</span> /
              <span class="warning">{{ row.warning_count || 0 }}</span> /
              <span class="info">{{ row.info_count || 0 }}</span>
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row.id)">查看详情</el-button>
            <el-button size="small" type="warning" link @click="handleRun(row.id)" v-if="row.status !== 'running'">重新执行</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建任务弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建 SEO 检测任务" width="500px">
      <el-form :model="createForm" label-width="90px" ref="createFormRef">
        <el-form-item label="任务名称" prop="name" :rules="[{ required: true, message: '请输入任务名称' }]">
          <el-input v-model="createForm.name" placeholder="如：官网首页 SEO 检测" />
        </el-form-item>
        <el-form-item label="所属项目" prop="project_id" :rules="[{ required: true, message: '请选择项目' }]">
          <el-select v-model="createForm.project_id" placeholder="请选择项目" style="width:100%">
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标URL" prop="target_url" :rules="[{ required: true, message: '请输入URL' }]">
          <el-input v-model="createForm.target_url" placeholder="https://www.example.com" />
        </el-form-item>
        <el-form-item label="检测URLs">
          <el-input v-model="urlsInput" type="textarea" :rows="3" placeholder="可选，每行一个URL，留空则只检测目标URL" />
        </el-form-item>
        <el-form-item label="SPA 等待">
          <el-input-number v-model="createForm.config.spaw_wait" :min="1000" :max="10000" :step="1000" /> ms
          <span class="form-tip">（等待 SPA 渲染完成）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建并执行</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情抽屉 -->
    <el-drawer v-model="detailDrawer" title="SEO 详情" size="800px" direction="rtl">
      <div v-if="seoStore.currentTask" class="seo-detail">
        <!-- 概览卡片 -->
        <el-row :gutter="12" class="overview-cards">
          <el-col :span="6">
            <div class="overview-card score-card">
              <div class="card-label">SEO 评分</div>
              <div class="card-value large" :class="scoreClass(seoStore.currentTask.score)">
                {{ seoStore.currentTask.score || '-' }}
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="overview-card critical-card">
              <div class="card-label">Critical</div>
              <div class="card-value critical">{{ seoStore.currentTask.critical_count || 0 }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="overview-card warning-card">
              <div class="card-label">Warning</div>
              <div class="card-value warning">{{ seoStore.currentTask.warning_count || 0 }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="overview-card info-card">
              <div class="card-label">Info</div>
              <div class="card-value info">{{ seoStore.currentTask.info_count || 0 }}</div>
            </div>
          </el-col>
        </el-row>

        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" class="basic-info">
          <el-descriptions-item label="任务名称">{{ seoStore.currentTask.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ seoStore.currentTask.status }}</el-descriptions-item>
          <el-descriptions-item label="目标URL" :span="2">
            <el-link :href="seoStore.currentTask.target_url" target="_blank" type="primary">
              {{ seoStore.currentTask.target_url }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(seoStore.currentTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(seoStore.currentTask.finished_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 问题筛选 -->
        <div class="issues-filter">
          <el-radio-group v-model="issueFilter" size="small">
            <el-radio-button label="">全部 ({{ seoStore.issues.length }})</el-radio-button>
            <el-radio-button label="critical">Critical ({{ seoStore.issues.filter(i => i.severity === 'critical').length }})</el-radio-button>
            <el-radio-button label="warning">Warning ({{ seoStore.issues.filter(i => i.severity === 'warning').length }})</el-radio-button>
            <el-radio-button label="info">Info ({{ seoStore.issues.filter(i => i.severity === 'info').length }})</el-radio-button>
          </el-radio-group>
          <el-button size="small" type="primary" plain @click="showReport" style="margin-left: 12px">生成报告</el-button>
        </div>

        <!-- 问题列表 -->
        <div class="issues-list">
          <div
            v-for="issue in filteredIssues"
            :key="issue.id"
            class="issue-item"
            :class="'issue-' + issue.severity"
          >
            <div class="issue-header">
              <el-tag :type="severityType(issue.severity)" size="small">{{ issue.severity.toUpperCase() }}</el-tag>
              <span class="issue-category">[{{ issue.category }}]</span>
              <span class="issue-rule">{{ issue.rule_id }}</span>
            </div>
            <div class="issue-desc">{{ issue.description }}</div>
            <div class="issue-suggestion" v-if="issue.suggestion">
              <strong>建议：</strong>{{ issue.suggestion }}
            </div>
            <div class="issue-url">
              <el-link :href="issue.url" target="_blank" type="primary" style="font-size:12px">{{ issue.url }}</el-link>
            </div>
          </div>
          <el-empty v-if="filteredIssues.length === 0" description="暂无问题" />
        </div>
      </div>
    </el-drawer>

    <!-- 报告弹窗 -->
    <el-dialog v-model="reportDialogVisible" title="SEO 检测报告" width="900px">
      <div v-if="reportHtml" class="report-content" v-html="reportHtml"></div>
      <div v-else>加载中...</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProjectsStore } from '../../stores/projects'
import { useSeoStore } from '../../stores/seo'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'

const projectsStore = useProjectsStore()
const seoStore = useSeoStore()

const filters = ref({ project_id: null, status: '' })
const createDialogVisible = ref(false)
const creating = ref(false)
const detailDrawer = ref(false)
const reportDialogVisible = ref(false)
const createFormRef = ref(null)
const urlsInput = ref('')
const reportHtml = ref('')
const issueFilter = ref('')

const createForm = ref({
  name: '',
  project_id: null,
  target_url: '',
  config: { spa_wait: 3000 },
})

let autoRefreshTimer = null

const filteredIssues = computed(() => {
  if (!issueFilter.value) return seoStore.issues
  return seoStore.issues.filter(i => i.severity === issueFilter.value)
})

onMounted(async () => {
  await projectsStore.fetchProjects()
  await loadData()
  autoRefreshTimer = setInterval(loadData, 15000)
})

onUnmounted(() => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
})

async function loadData() {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.status) params.status = filters.value.status
  await seoStore.fetchTasks(params)
}

function showCreateDialog() {
  createForm.value = { name: '', project_id: null, target_url: '', config: { spa_wait: 3000 } }
  urlsInput.value = ''
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
    const urls = urlsInput.value
      ? urlsInput.value.split('\n').map(u => u.trim()).filter(u => u)
      : []
    await seoStore.createTask({
      ...createForm.value,
      urls,
    })
    createDialogVisible.value = false
    ElMessage.success('任务已创建')
    await loadData()
  } finally {
    creating.value = false
  }
}

async function viewDetail(taskId) {
  detailDrawer.value = true
  await seoStore.fetchTask(taskId)
}

async function handleRun(taskId) {
  try {
    await seoStore.runTask(taskId)
    ElMessage.success('任务已重新触发')
    await loadData()
  } catch (e) {
    ElMessage.error('触发失败')
  }
}

async function handleDelete(taskId) {
  try {
    await ElMessageBox.confirm('确认删除该任务?', '删除确认', { type: 'warning' })
    await seoStore.deleteTask(taskId)
    ElMessage.success('删除成功')
  } catch {
    // 取消
  }
}

async function showReport() {
  if (!seoStore.currentTask) return
  try {
    const result = await seoStore.fetchReport(seoStore.currentTask.id)
    reportHtml.value = result.html || ''
    reportDialogVisible.value = true
  } catch {
    ElMessage.error('生成报告失败')
  }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function scoreClass(score) {
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-medium'
  return 'score-poor'
}

function severityType(sev) {
  if (sev === 'critical') return 'danger'
  if (sev === 'warning') return 'warning'
  return 'info'
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
.score-good { background: #e3f4e8; color: #67c23a; }
.score-medium { background: #fdf6ec; color: #e6a23c; }
.score-poor { background: #fde2e2; color: #f56c6c; }
.issue-counts { font-size: 13px; }
.issue-counts .critical { color: #f56c6c; font-weight: bold; }
.issue-counts .warning { color: #e6a23c; font-weight: bold; }
.issue-counts .info { color: #909399; font-weight: bold; }
.form-tip { margin-left: 8px; color: #999; font-size: 12px; }

/* 详情抽屉 */
.overview-cards { margin-bottom: 20px; }
.overview-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.card-label { font-size: 12px; color: #666; margin-bottom: 8px; }
.card-value { font-size: 24px; font-weight: bold; }
.card-value.large { font-size: 36px; }
.card-value.critical { color: #f56c6c; }
.card-value.warning { color: #e6a23c; }
.card-value.info { color: #909399; }
.score-good { color: #67c23a; }
.score-medium { color: #e6a23c; }
.score-poor { color: #f56c6c; }

.basic-info { margin-bottom: 20px; }
.issues-filter { margin: 16px 0; display: flex; align-items: center; }

.issues-list { max-height: 500px; overflow-y: auto; }
.issue-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}
.issue-item.issue-critical { border-left: 4px solid #f56c6c; }
.issue-item.issue-warning { border-left: 4px solid #e6a23c; }
.issue-item.issue-info { border-left: 4px solid #909399; }
.issue-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.issue-category { font-weight: bold; color: #333; }
.issue-rule { color: #666; font-size: 12px; }
.issue-desc { color: #333; margin-bottom: 6px; }
.issue-suggestion { color: #666; font-size: 13px; margin-bottom: 6px; background: #f5f7fa; padding: 6px 10px; border-radius: 4px; }
.issue-url { font-size: 12px; color: #999; }

.report-content { max-height: 600px; overflow-y: auto; }
</style>