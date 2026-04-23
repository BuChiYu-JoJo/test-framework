<template>
  <div class="cases-view">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filters.project_id" placeholder="选择项目" clearable size="default" style="width: 160px" @change="loadCases">
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用例名称/ID"
          clearable
          size="default"
          style="width: 200px"
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
          导入Excel
        </el-button>
        <el-button @click="downloadTemplate">
          <el-icon><Download /></el-icon>
          下载模板
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建用例
        </el-button>
      </div>
    </div>

    <!-- 用例列表 -->
    <el-card shadow="never" class="mt-16">
      <el-table
        :data="casesStore.cases"
        v-loading="casesStore.loading"
        stripe
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="case_id" label="用例ID" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.case_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="用例名称" min-width="200" />
        <el-table-column prop="module" label="模块" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.module }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="priorityType(row.priority)">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="160">
          <template #default="{ row }">
            <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small" class="mr-4">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" link @click="handleRun(row)">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="info" link @click="handleDuplicate(row.id)">复制</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑用例对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close>
      <el-form :model="formData" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用例名称" required>
              <el-input v-model="formData.name" placeholder="如：登录-正确账号密码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用例ID" required>
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
          <el-select v-model="formData.tags" multiple placeholder="选择标签" style="width: 100%" allow-create filterable default-first-option>
            <el-option label="冒烟" value="冒烟" />
            <el-option label="核心流程" value="核心流程" />
            <el-option label="登录" value="登录" />
            <el-option label="任务" value="任务" />
            <el-option label="接口" value="接口" />
          </el-select>
        </el-form-item>
        <el-form-item label="用例内容" required>
          <el-input
            v-model="formData.content"
            type="textarea"
            :rows="12"
            placeholder="YAML 格式用例内容..."
            style="font-family: 'Courier New', monospace; font-size: 13px;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="deleteDialogVisible"
      title="删除用例"
      message="确认删除该用例？删除后将无法恢复。"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <!-- 单条执行确认 -->
    <ConfirmDialog
      v-model="runDialogVisible"
      title="执行确认"
      :message="`立即执行用例「${runTarget.name}」？`"
      type="info"
      confirm-text="执行"
      @confirm="confirmRun"
    />

    <!-- 批量执行确认 -->
    <ConfirmDialog
      v-model="batchDialogVisible"
      title="批量执行确认"
      :message="`确定批量执行以下 ${batchTarget.count} 个用例？\n\n${batchTarget.names}`"
      type="info"
      confirm-text="执行"
      @confirm="confirmBatchRun"
    />

    <!-- 导入 Excel 对话框 -->
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
              <div class="el-upload__tip">支持 .xlsx / .xls 格式，每个 Sheet 为一个用例</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 执行结果抽屉 -->
    <el-drawer v-model="executionDrawer" title="执行结果" size="600px" direction="rtl">
      <div v-if="executionStore.currentExecution" class="execution-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="执行ID">{{ executionStore.currentExecution.execution_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="executionStatusType(executionStore.currentExecution.result || executionStore.currentExecution.status)">
              {{ executionStore.currentExecution.result || executionStore.currentExecution.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ executionStore.currentExecution.duration_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(executionStore.currentExecution.started_at) }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="executionStore.currentExecution.error_msg" class="error-msg">
          <el-alert type="error" :title="executionStore.currentExecution.error_msg" :closable="false" />
        </div>

        <el-tabs v-model="executionActiveTab" class="detail-tabs">
          <el-tab-pane label="执行步骤" name="steps">
            <el-table :data="executionStore.currentSteps" stripe size="small">
              <el-table-column prop="step_no" label="#" width="50" />
              <el-table-column prop="action" label="动作" width="120" />
              <el-table-column prop="target" label="目标" min-width="140" show-overflow-tooltip />
              <el-table-column prop="value" label="值" width="100" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }"><StatusBadge :status="row.status" /></template>
              </el-table-column>
              <el-table-column prop="duration_ms" label="耗时" width="80">
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
              <div class="debug-log-view">
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import { Search, Upload, Download } from '@element-plus/icons-vue'
import { useCasesStore } from '../../stores/cases'
import { useProjectsStore } from '../../stores/projects'
import { useExecutionStore } from '../../stores/execution'
import { casesApi } from '../../api'

const route = useRoute()
const casesStore = useCasesStore()
const projectsStore = useProjectsStore()
const executionStore = useExecutionStore()

const dialogVisible = ref(false)
const dialogMode = ref('create')  // 'create' | 'edit'
const saving = ref(false)
const executionDrawer = ref(false)
const executionActiveTab = ref('steps')
const selectedCases = ref([])
const importDialogVisible = ref(false)
const importing = ref(false)
const uploadRef = ref(null)
const fileList = ref([])

// Confirm dialogs
const deleteDialogVisible = ref(false)
const deleteTarget = ref({ type: '', id: null })
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

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (route.query.project_id) {
    filters.value.project_id = parseInt(route.query.project_id)
  }
  await loadCases()
})

// 抽屉关闭时断开 SSE
watch(executionDrawer, (val) => {
  if (!val) stopEventSource()
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
    ElMessage.warning('请填写必填项（名称/ID/项目/内容）')
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

async function handleDelete(id) {
  deleteTarget.value = { type: 'case', id }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  const { id } = deleteTarget.value
  try {
    await casesStore.deleteCase(id)
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

async function handleRun(row) {
  runTarget.value = { name: row.name, case_ids: [row.id], project_id: row.project_id }
  runDialogVisible.value = true
}

async function confirmRun({ done }) {
  const { name, case_ids, project_id } = runTarget.value
  try {
    const result = await executionStore.createExecution({ case_ids, project_id, env: 'test' })
    ElMessage.success(`执行已触发！执行ID：${result.execution_ids[0]}`)
    done()
    executionDrawer.value = true
    await pollExecution(result.execution_ids[0])
  } catch {
    done()
  }
}

async function handleBatchRun() {
  if (selectedCases.value.length === 0) {
    ElMessage.warning('请先选择要执行的用例')
    return
  }
  batchTarget.value = {
    names: selectedCases.value.map((c) => c.name).join('、'),
    count: selectedCases.value.length,
    case_ids: selectedCases.value.map((c) => c.id),
    project_id: selectedCases.value[0].project_id,
  }
  batchDialogVisible.value = true
}

async function confirmBatchRun({ done }) {
  const { case_ids, project_id } = batchTarget.value
  try {
    const result = await executionStore.createExecution({ case_ids, project_id, env: 'test' })
    ElMessage.success(`批量执行已触发！共 ${case_ids.length} 个用例`)
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
  // 先拉一次完整状态
  await executionStore.fetchExecution(executionId)
  executionDrawer.value = true
  executionActiveTab.value = 'steps'
  executionStore.startDebugStreaming(executionId)

  // 步骤 SSE
  const url = `/api/v1/executions/${executionId}/stream`
  activeEventSource = new EventSource(url)

  activeEventSource.addEventListener('connected', async (e) => {
    // 服务器连上了，开始实时接收步骤
  })

  activeEventSource.addEventListener('message', (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'step') {
        executionStore.addStep(data)
      } else if (data.type === 'done') {
        executionStore.updateExecutionStatus(data)
        stopEventSource()
      }
    } catch {}
  })

  activeEventSource.addEventListener('heartbeat', () => {
    // 心跳，维持连接
  })

  activeEventSource.onerror = async () => {
    stopEventSource()
    // 降级到轮询
    await fallbackPoll(executionId)
  }
}

async function fallbackPoll(executionId) {
  for (let i = 0; i < 30; i++) {
    await executionStore.fetchExecution(executionId)
    const status = executionStore.currentExecution?.status
    if (status === 'passed' || status === 'failed' || status === 'error' || status === 'blocked') break
    await new Promise((r) => setTimeout(r, 2000))
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
    const fd = new FormData()
    fd.append('file', file)
    const result = await casesApi.import(importForm.value.project_id, fd)
    ElMessage.success(result.message || `导入成功，共 ${result.total || 1} 个用例`)
    importDialogVisible.value = false
    await loadCases()
  } catch {
    // error already shown by interceptor
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
  } catch {
    // error already shown by interceptor
  }
}

function priorityType(p) {
  return { P0: 'danger', P1: 'warning', P2: 'info', P3: '' }[p] || 'info'
}

function executionStatusType(s) {
  return { passed: 'success', failed: 'danger', error: 'danger', running: 'warning' }[s] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}
.mt-16 { margin-top: 16px; }
.mr-4 { margin-right: 4px; }
.error-msg { margin: 16px 0; }
.steps-section { margin-top: 20px; }
.steps-section h4 { margin-bottom: 12px; font-size: 14px; color: #333; }
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
</style>
