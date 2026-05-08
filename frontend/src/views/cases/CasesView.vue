<template>
  <div class="cases-view">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="filters.project_id"
          placeholder="选择项目"
          clearable
          style="width: 160px"
          @change="loadCases"
        >
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用例名称/ID"
          clearable
          style="width: 220px"
          @keyup.enter="loadCases"
        >
          <template #append>
            <el-button :icon="Search" @click="loadCases" />
          </template>
        </el-input>
      </div>

      <div class="toolbar-right">
        <el-button v-if="selectedCases.length > 0" type="success" @click="handleBatchRun">
          <el-icon><VideoPlay /></el-icon>
          批量执行 ({{ selectedCases.length }})
        </el-button>
        <el-button @click="showImportDialog">
          <el-icon><Upload /></el-icon>
          导入 Excel
        </el-button>
        <el-button @click="downloadTemplate">
          <el-icon><Download /></el-icon>
          下载模板
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新建用例
        </el-button>
      </div>
    </div>

    <el-card shadow="never" class="mt-16">
      <el-table
        :data="casesStore.cases"
        v-loading="casesStore.loading"
        stripe
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="case_id" label="用例 ID" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.case_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="用例名称" min-width="220" />
        <el-table-column prop="module" label="模块" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.module }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="priorityType(row.priority)">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="180">
          <template #default="{ row }">
            <div class="tag-wrap">
              <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small">{{ tag }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" link @click="handleRun(row)">
              <el-icon><VideoPlay /></el-icon>
              执行
            </el-button>
            <el-button size="small" type="warning" link @click="handleQuickRun(row)">立即运行</el-button>
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="info" link @click="handleDuplicate(row.id)">复制</el-button>
            <el-button size="small" link @click="handleSelfCheck(row)">AI体检</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="1100px" destroy-on-close>
      <el-form :model="formData" label-width="96px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用例名称" required>
              <el-input v-model="formData.name" placeholder="如：登录-正确账号密码跳转仪表盘" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用例 ID" required>
              <el-input v-model="formData.case_id" placeholder="如：TC001" :disabled="dialogMode === 'edit'" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属项目" required>
              <el-select v-model="formData.project_id" placeholder="选择项目" style="width: 100%">
                <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="模块">
              <el-input v-model="formData.module" placeholder="如：login" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="优先级">
              <el-select v-model="formData.priority" style="width: 100%">
                <el-option label="P0 冒烟" value="P0" />
                <el-option label="P1 核心" value="P1" />
                <el-option label="P2 一般" value="P2" />
                <el-option label="P3 低" value="P3" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="标签">
          <el-select
            v-model="formData.tags"
            multiple
            placeholder="选择或创建标签"
            style="width: 100%"
            allow-create
            filterable
            default-first-option
          >
            <el-option label="冒烟" value="冒烟" />
            <el-option label="核心流程" value="核心流程" />
            <el-option label="登录" value="登录" />
            <el-option label="任务" value="任务" />
            <el-option label="接口" value="接口" />
          </el-select>
        </el-form-item>

        <div class="editor-layout">
          <div class="editor-pane">
            <div class="panel-title-row">
              <span class="panel-title">YAML 用例内容</span>
              <div class="panel-actions">
                <el-button text size="small" @click="applyTemplate('login')">插入登录模板</el-button>
                <el-button text size="small" @click="applyTemplate('crud')">插入通用模板</el-button>
              </div>
            </div>
            <el-input
              v-model="formData.content"
              type="textarea"
              :rows="20"
              placeholder="在这里编辑 YAML 用例内容"
              class="yaml-editor"
            />
            <div class="editor-hint">
              建议把一个步骤写成一件事：`action / target / value / description`，结构化预览会在右侧实时更新。
            </div>
          </div>

          <div class="preview-pane">
            <div class="panel-title">结构化预览</div>
            <el-alert
              v-if="casePreview.errors.length"
              type="warning"
              :closable="false"
              class="mb-12"
              :title="casePreview.errors[0]"
            />

            <div class="preview-block">
              <div class="preview-title">{{ casePreview.name || formData.name || '未命名用例' }}</div>
              <div class="preview-meta">
                <el-tag size="small">{{ casePreview.id || formData.case_id || 'CASE_ID' }}</el-tag>
                <el-tag size="small" effect="plain">{{ casePreview.module || formData.module || 'default' }}</el-tag>
                <el-tag size="small" :type="priorityType(casePreview.priority || formData.priority)">
                  {{ casePreview.priority || formData.priority || 'P2' }}
                </el-tag>
              </div>
              <div v-if="casePreview.url" class="preview-line">
                <span class="label">URL</span>
                <code>{{ casePreview.url }}</code>
              </div>
              <div class="preview-line" v-if="casePreview.tags.length">
                <span class="label">标签</span>
                <div class="tag-wrap">
                  <el-tag v-for="tag in casePreview.tags" :key="tag" size="small">{{ tag }}</el-tag>
                </div>
              </div>
            </div>

            <div class="preview-block">
              <div class="preview-subtitle">步骤列表</div>
              <el-empty v-if="casePreview.steps.length === 0" description="还没有识别到步骤" />
              <div v-for="(step, index) in casePreview.steps" :key="`${index}-${step.action}`" class="preview-step">
                <div class="preview-step-header">
                  <span class="step-no">#{{ step.no || index + 1 }}</span>
                  <strong>{{ step.action || 'unknown' }}</strong>
                </div>
                <div v-if="step.target" class="preview-line">
                  <span class="label">target</span>
                  <code>{{ step.target }}</code>
                </div>
                <div v-if="step.value" class="preview-line">
                  <span class="label">value</span>
                  <code>{{ step.value }}</code>
                </div>
                <div v-if="step.description" class="preview-desc">{{ step.description }}</div>
              </div>
            </div>

            <div class="preview-block">
              <div class="preview-subtitle">预期结果</div>
              <div class="preview-desc">{{ casePreview.expected || '未填写 expected' }}</div>
            </div>
          </div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <ConfirmDialog
      v-model="deleteDialogVisible"
      title="删除用例"
      message="确认删除该用例？删除后将无法恢复。"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="runDialogVisible"
      title="执行确认"
      :message="`立即执行用例「${runTarget.name}」？`"
      type="info"
      confirm-text="执行"
      @confirm="confirmRun"
    />

    <ConfirmDialog
      v-model="batchDialogVisible"
      title="批量执行确认"
      :message="`确定批量执行以下 ${batchTarget.count} 个用例？\n\n${batchTarget.names}`"
      type="info"
      confirm-text="执行"
      @confirm="confirmBatchRun"
    />

    <el-dialog v-model="importDialogVisible" title="导入 Excel 用例" width="500px" destroy-on-close>
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="所属项目" required>
          <el-select v-model="importForm.project_id" placeholder="选择项目" style="width: 100%">
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls"
            :on-change="onFileChange"
            :file-list="fileList"
          >
            <el-button>选择 Excel 文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 .xlsx / .xls 格式，每个 Sheet 为一个用例。</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="executionDrawer" title="执行结果" size="760px" direction="rtl">
      <div v-if="executionStore.currentExecution" class="execution-detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="执行 ID">
            <code>{{ executionStore.currentExecution.execution_id }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="结果">
            <StatusBadge :status="executionStore.currentExecution.result || executionStore.currentExecution.status" />
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ formatDuration(executionStore.currentExecution.duration_ms) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatTime(executionStore.currentExecution.started_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="executionStore.currentExecution.error_msg"
          type="error"
          :title="executionStore.currentExecution.error_msg"
          :closable="false"
          class="mt-16"
        />

        <el-tabs v-model="executionActiveTab" class="mt-16">
          <el-tab-pane :label="`执行步骤 (${executionStore.currentSteps.length})`" name="steps">
            <div class="step-preview-list">
              <div v-for="step in executionStore.currentSteps" :key="step.step_no" class="step-preview-card">
                <div class="step-preview-head">
                  <strong>#{{ step.step_no }} {{ step.action }}</strong>
                  <StatusBadge :status="step.status" />
                </div>
                <div class="preview-line"><span class="label">target</span><code>{{ step.target || '-' }}</code></div>
                <div class="preview-line" v-if="step.actual"><span class="label">actual</span><code>{{ step.actual }}</code></div>
                <div class="preview-line" v-if="step.error_msg"><span class="label">error</span><code>{{ step.error_msg }}</code></div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane :label="`调试日志 (${executionStore.debugLogs.length})`" name="debug">
            <LogViewer :logs="normalizedDebugLogs" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, Plus, Search, Upload, VideoPlay } from '@element-plus/icons-vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import LogViewer from '../../components/LogViewer.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import { casesApi } from '../../api'
import { useCasesStore } from '../../stores/cases'
import { useExecutionStore } from '../../stores/execution'
import { useProjectsStore } from '../../stores/projects'

const route = useRoute()
const router = useRouter()
const casesStore = useCasesStore()
const projectsStore = useProjectsStore()
const executionStore = useExecutionStore()

const dialogVisible = ref(false)
const dialogMode = ref('create')
const saving = ref(false)
const executionDrawer = ref(false)
const executionActiveTab = ref('steps')
const selectedCases = ref([])
const importDialogVisible = ref(false)
const importing = ref(false)
const uploadRef = ref(null)
const fileList = ref([])

const deleteDialogVisible = ref(false)
const deleteTarget = ref({ id: null })
const runDialogVisible = ref(false)
const runTarget = ref({ name: '', case_ids: [], project_id: null })
const batchDialogVisible = ref(false)
const batchTarget = ref({ names: '', count: 0, case_ids: [], project_id: null })

const filters = ref({ project_id: null, keyword: '' })
const importForm = ref({ project_id: null })

const defaultForm = () => ({
  id: null,
  name: '',
  case_id: '',
  project_id: null,
  module: 'default',
  priority: 'P2',
  tags: [],
  content: '',
})

const formData = ref(defaultForm())

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建用例' : '编辑用例'))

const normalizedDebugLogs = computed(() =>
  (executionStore.debugLogs || []).map((log) => ({
    timestamp: log.ts ? new Date(log.ts * 1000).toISOString() : '',
    level: String(log.level || 'info').toUpperCase(),
    message: log.message || '',
    meta: log.meta || {},
  })),
)

const casePreview = computed(() => parseCaseContent(formData.value.content))

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (route.query.project_id) {
    filters.value.project_id = parseInt(route.query.project_id, 10)
  }
  await loadCases()
})

watch(executionDrawer, (visible) => {
  if (!visible) stopEventSource()
})

onUnmounted(() => {
  stopEventSource()
})

async function loadCases() {
  const params = {}
  if (filters.value.project_id) params.project_id = filters.value.project_id
  if (filters.value.keyword) params.keyword = filters.value.keyword
  await casesStore.fetchCases(params)
}

function openCreateDialog() {
  dialogMode.value = 'create'
  formData.value = defaultForm()
  if (filters.value.project_id) formData.value.project_id = filters.value.project_id
  dialogVisible.value = true
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  formData.value = {
    id: row.id,
    name: row.name,
    case_id: row.case_id,
    project_id: row.project_id,
    module: row.module,
    priority: row.priority,
    tags: [...(row.tags || [])],
    content: row.content,
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!formData.value.name || !formData.value.case_id || !formData.value.project_id || !formData.value.content) {
    ElMessage.warning('请填写必填项（名称、ID、项目、内容）')
    return
  }
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await casesStore.createCase(formData.value)
    } else {
      await casesStore.updateCase(formData.value.id, formData.value)
    }
    dialogVisible.value = false
    ElMessage.success('保存成功')
    await loadCases()
  } finally {
    saving.value = false
  }
}

function handleDelete(id) {
  deleteTarget.value = { id }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  try {
    await casesStore.deleteCase(deleteTarget.value.id)
    ElMessage.success('删除成功')
    await loadCases()
    done()
  } catch {
    done()
  }
}

async function handleDuplicate(id) {
  try {
    await casesStore.duplicateCase(id)
    ElMessage.success('复制成功')
    await loadCases()
  } catch {}
}

function handleRun(row) {
  runTarget.value = { name: row.name, case_ids: [row.id], project_id: row.project_id }
  runDialogVisible.value = true
}

function handleQuickRun(row) {
  router.push({
    path: '/execution',
    query: { project_id: row.project_id, case_id: row.id, auto_run: 1 },
  })
}

function handleSelfCheck(row) {
  router.push({
    path: '/ai-tools',
    query: { tab: 'self-check', case_id: row.id, project_id: row.project_id },
  })
}

async function confirmRun({ done }) {
  try {
    const result = await executionStore.createExecution({
      case_ids: runTarget.value.case_ids,
      project_id: runTarget.value.project_id,
      env: 'test',
    })
    ElMessage.success(`执行已触发，执行 ID：${result.execution_ids[0]}`)
    done()
    executionDrawer.value = true
    await pollExecution(result.execution_ids[0])
  } catch {
    done()
  }
}

function handleBatchRun() {
  if (selectedCases.value.length === 0) {
    ElMessage.warning('请先选择要执行的用例')
    return
  }
  batchTarget.value = {
    names: selectedCases.value.map((item) => item.name).join('、'),
    count: selectedCases.value.length,
    case_ids: selectedCases.value.map((item) => item.id),
    project_id: selectedCases.value[0].project_id,
  }
  batchDialogVisible.value = true
}

async function confirmBatchRun({ done }) {
  try {
    const result = await executionStore.createExecution({
      case_ids: batchTarget.value.case_ids,
      project_id: batchTarget.value.project_id,
      env: 'test',
    })
    ElMessage.success(`批量执行已触发，共 ${batchTarget.value.case_ids.length} 个用例`)
    done()
    selectedCases.value = []
    executionDrawer.value = true
    await pollExecution(result.execution_ids[result.execution_ids.length - 1])
  } catch {
    done()
  }
}

let activeEventSource = null

function stopEventSource() {
  if (activeEventSource) {
    activeEventSource.close()
    activeEventSource = null
  }
  executionStore.stopDebugStreaming()
}

async function startExecutionStream(executionId) {
  stopEventSource()
  await executionStore.fetchExecution(executionId)
  executionDrawer.value = true
  executionActiveTab.value = 'steps'
  executionStore.startDebugStreaming(executionId)

  activeEventSource = new EventSource(`/api/v1/executions/${executionId}/stream`)

  activeEventSource.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'step') {
        executionStore.addStep(data)
      } else if (data.type === 'done') {
        executionStore.updateExecutionStatus(data)
        stopEventSource()
      }
    } catch {}
  })

  activeEventSource.onerror = async () => {
    stopEventSource()
    await fallbackPoll(executionId)
  }
}

async function fallbackPoll(executionId) {
  for (let i = 0; i < 30; i += 1) {
    await executionStore.fetchExecution(executionId)
    const status = executionStore.currentExecution?.status
    if (['passed', 'failed', 'error', 'blocked'].includes(status)) break
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
}

async function pollExecution(executionId) {
  await startExecutionStream(executionId)
}

function onSelectionChange(rows) {
  selectedCases.value = rows
}

function showImportDialog() {
  importForm.value.project_id = filters.value.project_id || null
  fileList.value = []
  importDialogVisible.value = true
}

function onFileChange(file, files) {
  fileList.value = files.slice(-1)
}

async function handleImport() {
  if (!importForm.value.project_id) {
    ElMessage.warning('请选择所属项目')
    return
  }
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择要导入的 Excel 文件')
    return
  }
  const file = fileList.value[0].raw
  if (!file) {
    ElMessage.warning('文件无效，请重新选择')
    return
  }
  importing.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const result = await casesApi.import(importForm.value.project_id, form)
    ElMessage.success(result.message || `导入成功，共 ${result.total || 1} 个用例`)
    importDialogVisible.value = false
    await loadCases()
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  try {
    const data = await casesApi.downloadTemplate()
    const blob = new Blob([data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '用例模板_v1.0.xlsx'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch {}
}

function priorityType(priority) {
  return { P0: 'danger', P1: 'warning', P2: 'info', P3: '' }[priority] || 'info'
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

function parseCaseContent(content) {
  const lines = String(content || '').split(/\r?\n/)
  const result = {
    id: '',
    name: '',
    module: '',
    priority: '',
    url: '',
    tags: [],
    expected: '',
    steps: [],
    errors: [],
  }

  let inTags = false
  let inSteps = false
  let currentStep = null

  const normalizeScalar = (value) => String(value || '').trim().replace(/^['"]|['"]$/g, '')
  const topLevelKeys = new Set(['id', 'name', 'module', 'priority', 'url', 'expected'])

  for (const rawLine of lines) {
    const line = rawLine.replace(/\t/g, '    ')
    const trimmed = line.trim()
    if (!trimmed) continue

    const indent = line.length - line.trimStart().length
    const topLevelMatch = trimmed.match(/^([A-Za-z_][\w-]*):\s*(.*)$/)
    if (indent === 0 && topLevelMatch && topLevelKeys.has(topLevelMatch[1])) {
      const [, key, value] = topLevelMatch
      result[key] = normalizeScalar(value)
      inTags = false
      if (key !== 'expected') inSteps = false
      continue
    }

    if (indent === 0 && trimmed === 'tags:') {
      inTags = true
      inSteps = false
      continue
    }

    if (indent === 0 && trimmed === 'steps:') {
      inSteps = true
      inTags = false
      currentStep = null
      continue
    }

    if (inTags && trimmed.startsWith('- ')) {
      result.tags.push(trimmed.slice(2).trim())
      continue
    }

    if (inSteps) {
      if (trimmed.startsWith('- ')) {
        currentStep = {
          no: result.steps.length + 1,
          action: '',
          target: '',
          value: '',
          description: '',
        }
        result.steps.push(currentStep)

        const inlineField = trimmed.slice(2).match(/^([A-Za-z_][\w-]*):\s*(.*)$/)
        if (inlineField) {
          const [, key, value] = inlineField
          if (key === 'no') currentStep.no = normalizeScalar(value)
          if (key === 'action') currentStep.action = normalizeScalar(value)
          if (key === 'target') currentStep.target = normalizeScalar(value)
          if (key === 'value') currentStep.value = normalizeScalar(value)
          if (key === 'description') currentStep.description = normalizeScalar(value)
        }
        continue
      }

      if (currentStep) {
        if (trimmed.startsWith('action:')) currentStep.action = normalizeScalar(trimmed.slice(7))
        if (trimmed.startsWith('target:')) currentStep.target = normalizeScalar(trimmed.slice(7))
        if (trimmed.startsWith('value:')) currentStep.value = normalizeScalar(trimmed.slice(6))
        if (trimmed.startsWith('description:')) currentStep.description = normalizeScalar(trimmed.slice(12))
        if (trimmed.startsWith('no:')) currentStep.no = normalizeScalar(trimmed.slice(3))
      }
    }
  }

  if (!result.id) result.errors.push('预览未识别到 id 字段')
  if (!result.name) result.errors.push('预览未识别到 name 字段')
  if (result.steps.length === 0) result.errors.push('预览未识别到 steps 列表')

  return result
}

function applyTemplate(type) {
  const templates = {
    login: `id: TC_LOGIN_001
name: 登录成功跳转首页
module: login
priority: P1
url: https://example.com/login
tags:
- 登录
- 冒烟
steps:
- action: navigate
  target: https://example.com/login
  description: 打开登录页面
- action: type
  target: input[placeholder="请输入账号"]
  value: test_user
  description: 输入账号
- action: type
  target: input[placeholder="请输入密码"]
  value: 123456
  description: 输入密码
- action: click
  target: button:has-text("登录")
  description: 点击登录按钮
expected: 登录成功并进入首页
`,
    crud: `id: TC_GENERIC_001
name: 通用页面操作示例
module: default
priority: P2
url: https://example.com/page
tags:
- 核心流程
steps:
- action: navigate
  target: https://example.com/page
  description: 打开目标页面
- action: wait_for
  target: .page-ready
  description: 等待页面加载完成
- action: click
  target: button:has-text("新建")
  description: 点击新建按钮
expected: 页面出现新增表单
`,
  }
  formData.value.content = templates[type]
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mt-16 {
  margin-top: 16px;
}

.mb-12 {
  margin-bottom: 12px;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: 16px;
  align-items: start;
}

.editor-pane,
.preview-pane {
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 14px;
  background: #fff;
}

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.yaml-editor :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.editor-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-block {
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--el-fill-color-blank);
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
}

.preview-subtitle {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}

.preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.preview-line {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-line code,
.step-preview-card code {
  display: block;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 8px 10px;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
}

.preview-step {
  padding: 10px 0;
  border-top: 1px dashed var(--el-border-color);
}

.preview-step:first-of-type {
  border-top: none;
  padding-top: 0;
}

.preview-step-header {
  display: flex;
  gap: 8px;
  align-items: center;
}

.step-no {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.preview-desc {
  margin-top: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.6;
}

.step-preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-preview-card {
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 12px;
}

.step-preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

@media (max-width: 960px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
