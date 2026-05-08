<template>
  <div class="api-test-view">
    <div class="toolbar">
      <el-radio-group v-model="activeTab" size="default">
        <el-radio-button value="cases">用例管理</el-radio-button>
        <el-radio-button value="tasks">执行记录</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="activeTab === 'cases'">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="filters.project_id"
            placeholder="选择项目"
            clearable
            size="default"
            style="width: 160px"
            @change="loadCases"
          >
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-input
            v-model="filters.keyword"
            placeholder="搜索用例名称"
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
          <el-button v-if="selectedCases.length > 0" type="success" @click="handleBatchExecute">
            <el-icon><VideoPlay /></el-icon> 批量执行 ({{ selectedCases.length }})
          </el-button>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 新建用例
          </el-button>
        </div>
      </div>

      <el-card shadow="never" class="mt-16">
        <el-table :data="cases" v-loading="loading" stripe @selection-change="onSelectionChange">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="用例名称" min-width="180" />
          <el-table-column prop="module" label="模块" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.module }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="method" label="方法" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="methodType(row.method)">{{ row.method }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="url" label="URL" min-width="220" show-overflow-tooltip />
          <el-table-column prop="timeout" label="超时" width="80">
            <template #default="{ row }">{{ row.timeout }}s</template>
          </el-table-column>
          <el-table-column prop="tags" label="标签" width="140">
            <template #default="{ row }">
              <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="mr-4">{{ tag }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="warning" link @click="handleExecute(row)">
                <el-icon><VideoPlay /></el-icon> 执行
              </el-button>
              <el-button size="small" type="success" link @click="handleRun(row)">
                <el-icon><VideoPlay /></el-icon> 调试
              </el-button>
              <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <div v-if="activeTab === 'tasks'">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="taskFilters.project_id"
            placeholder="选择项目"
            clearable
            size="default"
            style="width: 160px"
            @change="loadTasks"
          >
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-select
            v-model="taskFilters.status"
            placeholder="状态"
            clearable
            size="default"
            style="width: 120px"
            @change="loadTasks"
          >
            <el-option label="进行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="待执行" value="pending" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button @click="loadTasks">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <el-card shadow="never" class="mt-16">
        <el-table :data="tasks" v-loading="taskLoading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="任务名称" min-width="180" />
          <el-table-column prop="env" label="环境" width="70">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.env }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total" label="用例数" width="80" />
          <el-table-column prop="passed" label="通过" width="70">
            <template #default="{ row }">
              <span style="color: #67c23a">{{ row.passed }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="failed" label="失败" width="70">
            <template #default="{ row }">
              <span style="color: #f56c6c">{{ row.failed }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="taskStatusType(row.status)">{{ taskStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时" width="90">
            <template #default="{ row }">{{ row.duration_ms }}ms</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="viewTaskResult(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="760px" destroy-on-close>
      <el-form :model="formData" label-width="100px" class="api-form">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用例名称" required>
              <el-input v-model="formData.name" placeholder="如：用户登录" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属项目" required>
              <el-select v-model="formData.project_id" placeholder="选择项目" style="width: 100%">
                <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="模块">
              <el-input v-model="formData.module" placeholder="如：auth" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="请求方法" required>
              <el-select v-model="formData.method" style="width: 100%">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="formData.timeout" :min="1" :max="300" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="URL" required>
          <el-input v-model="formData.url" placeholder="如：${base_url}/api/login" />
        </el-form-item>
        <el-form-item label="Headers">
          <el-input
            v-model="headersText"
            type="textarea"
            :rows="2"
            placeholder='JSON 格式，如：{"Content-Type":"application/json"}'
          />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Query Params">
              <el-input v-model="paramsText" type="textarea" :rows="2" placeholder="JSON 格式" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Body Type">
              <el-select v-model="formData.body_type" style="width: 100%">
                <el-option label="JSON" value="json" />
                <el-option label="Form" value="form" />
                <el-option label="Raw" value="raw" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Body">
          <el-input v-model="bodyText" type="textarea" :rows="3" placeholder="JSON 或原始文本" />
        </el-form-item>
        <el-form-item label="断言">
          <div class="assertions-list">
            <div v-for="(assertion, idx) in formData.assertions" :key="idx" class="assertion-item">
              <el-select v-model="assertion.type" size="small" style="width: 120px" @change="onAssertionTypeChange(assertion)">
                <el-option label="状态码" value="status_code" />
                <el-option label="响应时间" value="response_time" />
                <el-option label="JSON字段" value="json_field" />
              </el-select>
              <el-input
                v-if="assertion.type === 'json_field'"
                v-model="assertion.expr"
                size="small"
                placeholder="字段路径如 data.code"
                style="width: 160px"
              />
              <el-input
                v-model="assertion.expected"
                size="small"
                :placeholder="assertion.type === 'response_time' ? '阈值(ms)' : '期望值'"
                style="width: 140px"
              />
              <el-button size="small" type="danger" :icon="Delete" @click="removeAssertion(idx)" />
            </div>
          </div>
          <el-button type="default" size="small" @click="addAssertion">+ 添加断言</el-button>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="formData.tags" multiple placeholder="选择标签" style="width: 100%" allow-create filterable default-first-option>
            <el-option label="冒烟" value="冒烟" />
            <el-option label="登录" value="登录" />
            <el-option label="订单" value="订单" />
            <el-option label="核心" value="核心" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="runResultVisible" title="调试结果" width="700px" destroy-on-close>
      <div v-if="runResult" class="run-result">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="用例名称">{{ runResult.case_name }}</el-descriptions-item>
          <el-descriptions-item label="方法">{{ runResult.method }}</el-descriptions-item>
          <el-descriptions-item label="URL" :span="2">{{ runResult.url }}</el-descriptions-item>
          <el-descriptions-item label="状态码">
            <el-tag size="small" :type="runResult.response_status < 400 ? 'success' : 'danger'">
              {{ runResult.response_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            <span :style="{ color: runResult.response_time_ms > 1000 ? '#e6a23c' : '#67c23a' }">
              {{ runResult.response_time_ms }}ms
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="断言结果" :span="2">
            <span style="color: #67c23a">通过 {{ runResult.assertions_passed }}</span>
            <span style="color: #f56c6c; margin-left: 12px">失败 {{ runResult.assertions_failed }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="runResult.error_msg" class="mt-12">
          <el-alert type="error" :title="runResult.error_msg" :closable="false" />
        </div>

        <div class="result-section mt-12">
          <div class="section-title">请求 Headers</div>
          <pre class="code-block">{{ JSON.stringify(runResult.headers, null, 2) }}</pre>
        </div>

        <div v-if="runResult.request_body !== null && runResult.request_body !== undefined" class="result-section mt-12">
          <div class="section-title">请求 Body</div>
          <pre class="code-block">{{ typeof runResult.request_body === 'string' ? runResult.request_body : JSON.stringify(runResult.request_body, null, 2) }}</pre>
        </div>

        <div class="result-section mt-12">
          <div class="section-title">响应 Body</div>
          <pre class="code-block">{{ JSON.stringify(runResult.response_body, null, 2) }}</pre>
        </div>

        <div class="result-section mt-12">
          <div class="section-title">断言详情</div>
          <el-table :data="runResult.assertion_details" stripe size="small">
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="expr" label="表达式" width="160" />
            <el-table-column prop="expected" label="期望值" width="100" />
            <el-table-column prop="actual" label="实际值" width="100" />
            <el-table-column prop="message" label="说明" />
            <el-table-column label="结果" width="70">
              <template #default="{ row }">
                <el-tag size="small" :type="row.passed ? 'success' : 'danger'">
                  {{ row.passed ? '通过' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="runResultVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskDetailVisible" title="执行记录详情" width="820px" destroy-on-close>
      <div v-if="taskDetail" class="run-result">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务名称">{{ taskDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ taskDetail.env }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ taskStatusLabel(taskDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ taskDetail.duration_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="通过/失败" :span="2">
            {{ taskDetail.passed }} / {{ taskDetail.failed }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="result-section mt-12">
          <div class="section-title">执行结果</div>
          <el-empty v-if="taskResults.length === 0" description="暂无执行详情" />
          <div v-for="(item, index) in taskResults" :key="`${item.case_id || index}-${index}`" class="task-result-card">
            <div class="task-result-head">
              <strong>{{ item.case_name || `用例 ${index + 1}` }}</strong>
              <el-tag size="small" :type="item.error_msg || item.assertions_failed ? 'danger' : 'success'">
                {{ item.error_msg || item.assertions_failed ? '失败' : '通过' }}
              </el-tag>
            </div>

            <div class="task-result-meta">
              <div class="task-meta-item">
                <span class="result-label">方法</span>
                <code>{{ item.method || '-' }}</code>
              </div>
              <div class="task-meta-item">
                <span class="result-label">状态码</span>
                <code>{{ item.response_status ?? '-' }}</code>
              </div>
              <div class="task-meta-item">
                <span class="result-label">耗时</span>
                <code>{{ item.response_time_ms ?? 0 }}ms</code>
              </div>
              <div class="task-meta-item task-meta-url">
                <span class="result-label">URL</span>
                <code>{{ item.url || '-' }}</code>
              </div>
              <div v-if="item.error_msg" class="task-meta-item task-meta-full">
                <span class="result-label">错误</span>
                <code>{{ item.error_msg }}</code>
              </div>
            </div>

            <div class="result-section">
              <div class="section-title">请求 Headers</div>
              <pre class="code-block">{{ JSON.stringify(item.headers || {}, null, 2) }}</pre>
            </div>

            <div v-if="item.request_body !== null && item.request_body !== undefined" class="result-section">
              <div class="section-title">请求 Body</div>
              <pre class="code-block">{{ typeof item.request_body === 'string' ? item.request_body : JSON.stringify(item.request_body, null, 2) }}</pre>
            </div>

            <div class="result-section">
              <div class="section-title">响应 Body</div>
              <pre class="code-block">{{ JSON.stringify(item.response_body || {}, null, 2) }}</pre>
            </div>

            <div class="result-section">
              <div class="section-title">断言详情</div>
              <el-table :data="item.assertion_details || []" stripe size="small">
                <el-table-column prop="type" label="类型" width="100" />
                <el-table-column prop="expr" label="表达式" width="160" />
                <el-table-column prop="expected" label="期望值" width="100" />
                <el-table-column prop="actual" label="实际值" width="100" />
                <el-table-column prop="message" label="说明" />
              </el-table>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="taskDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <ConfirmDialog
      v-model="deleteDialogVisible"
      title="删除用例"
      message="确认删除这个接口用例？删除后将无法恢复。"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, VideoPlay, Delete, Refresh } from '@element-plus/icons-vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useProjectsStore } from '../../stores/projects'
import { apiTestApi } from '../../api'

const projectsStore = useProjectsStore()

const activeTab = ref('cases')
const cases = ref([])
const loading = ref(false)
const filters = ref({ project_id: null, keyword: '' })
const selectedCases = ref([])

const tasks = ref([])
const taskLoading = ref(false)
const taskFilters = ref({ project_id: null, status: null })

const dialogVisible = ref(false)
const dialogTitle = ref('新建用例')
const dialogMode = ref('create')
const saving = ref(false)
const formData = ref({
  name: '',
  project_id: null,
  module: 'default',
  method: 'GET',
  url: '',
  headers: {},
  params: {},
  body: {},
  body_type: 'json',
  assertions: [],
  timeout: 30,
  tags: [],
  created_by: '',
})

const headersText = ref('{}')
const paramsText = ref('{}')
const bodyText = ref('{}')

const deleteDialogVisible = ref(false)
const deleteTarget = ref(null)

const runResultVisible = ref(false)
const runResult = ref(null)
const taskDetailVisible = ref(false)
const taskDetail = ref(null)
const taskResults = ref([])

function stringifyEditorValue(value, fallback = '{}') {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return fallback
  }
}

function parseJsonEditor(text, label) {
  try {
    return JSON.parse(text || '{}')
  } catch {
    throw new Error(`${label} 不是合法的 JSON`)
  }
}

async function loadCases() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.project_id) params.project_id = filters.value.project_id
    if (filters.value.keyword) params.keyword = filters.value.keyword
    cases.value = await apiTestApi.listCases(params)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadTasks() {
  taskLoading.value = true
  try {
    const params = {}
    if (taskFilters.value.project_id) params.project_id = taskFilters.value.project_id
    if (taskFilters.value.status) params.status = taskFilters.value.status
    tasks.value = await apiTestApi.listTasks(params)
  } catch (e) {
    console.error(e)
  } finally {
    taskLoading.value = false
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  dialogTitle.value = '新建用例'
  formData.value = {
    name: '',
    project_id: filters.value.project_id || projectsStore.projects[0]?.id || null,
    module: 'default',
    method: 'GET',
    url: '',
    headers: {},
    params: {},
    body: {},
    body_type: 'json',
    assertions: [],
    timeout: 30,
    tags: [],
    created_by: '',
  }
  headersText.value = '{}'
  paramsText.value = '{}'
  bodyText.value = '{}'
  dialogVisible.value = true
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑用例'
  formData.value = {
    id: row.id,
    name: row.name,
    project_id: row.project_id,
    module: row.module,
    method: row.method,
    url: row.url,
    headers: row.headers || {},
    params: row.params || {},
    body: row.body ?? (row.body_type === 'raw' ? '' : {}),
    body_type: row.body_type || 'json',
    assertions: row.assertions || [],
    timeout: row.timeout || 30,
    tags: row.tags || [],
    created_by: row.created_by || '',
  }
  headersText.value = stringifyEditorValue(row.headers, '{}')
  paramsText.value = stringifyEditorValue(row.params, '{}')
  bodyText.value = formData.value.body_type === 'raw'
    ? (typeof row.body === 'string' ? row.body : '')
    : stringifyEditorValue(row.body, '{}')
  dialogVisible.value = true
}

async function handleSave() {
  if (!formData.value.name) {
    ElMessage.warning('请填写用例名称')
    return
  }
  if (!formData.value.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!formData.value.url) {
    ElMessage.warning('请填写 URL')
    return
  }

  saving.value = true
  try {
    formData.value.headers = parseJsonEditor(headersText.value, 'Headers')
    formData.value.params = parseJsonEditor(paramsText.value, 'Query Params')
    if (formData.value.body_type === 'raw') {
      formData.value.body = bodyText.value || ''
    } else {
      formData.value.body = parseJsonEditor(bodyText.value, 'Body')
    }

    if (dialogMode.value === 'create') {
      await apiTestApi.createCase(formData.value)
      ElMessage.success('创建成功')
    } else {
      await apiTestApi.updateCase(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    await loadCases()
  } catch (e) {
    if (e instanceof Error && e.message.includes('JSON')) {
      ElMessage.warning(e.message)
      return
    }
    console.error(e)
  } finally {
    saving.value = false
  }
}

function handleDelete(id) {
  deleteTarget.value = id
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  try {
    await apiTestApi.deleteCase(deleteTarget.value)
    ElMessage.success('删除成功')
    await loadCases()
  } catch (e) {
    console.error(e)
  }
}

function onSelectionChange(rows) {
  selectedCases.value = rows
}

async function handleExecute(row) {
  try {
    await apiTestApi.createTask({
      name: `执行 - ${row.name}`,
      project_id: row.project_id,
      case_ids: [row.id],
      env: 'dev',
    })
    ElMessage.success('已加入执行队列')
    activeTab.value = 'tasks'
    await loadTasks()
  } catch (e) {
    console.error(e)
  }
}

async function handleBatchExecute() {
  if (selectedCases.value.length === 0) {
    ElMessage.warning('请先选择要执行的用例')
    return
  }

  const projectIds = [...new Set(selectedCases.value.map((item) => item.project_id))]
  if (projectIds.length !== 1) {
    ElMessage.warning('批量执行请先筛选到同一个项目')
    return
  }

  try {
    await apiTestApi.createTask({
      name: `批量执行 - ${selectedCases.value.length} 条用例`,
      project_id: projectIds[0],
      case_ids: selectedCases.value.map((item) => item.id),
      env: 'dev',
    })
    ElMessage.success('批量执行任务已创建')
    activeTab.value = 'tasks'
    selectedCases.value = []
    await loadTasks()
  } catch (e) {
    console.error(e)
  }
}

async function handleRun(row) {
  try {
    runResult.value = await apiTestApi.runCase(row.id, 'dev')
    runResultVisible.value = true
    await loadTasks()
  } catch (e) {
    console.error(e)
  }
}

async function viewTaskResult(row) {
  try {
    const detail = await apiTestApi.getTask(row.id)
    taskDetail.value = detail
    taskResults.value = detail.result_json || []
    taskDetailVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

function addAssertion() {
  formData.value.assertions.push({ type: 'status_code', expr: '', expected: '200' })
}

function removeAssertion(idx) {
  formData.value.assertions.splice(idx, 1)
}

function onAssertionTypeChange(assertion) {
  if (assertion.type === 'status_code') {
    assertion.expected = '200'
    assertion.expr = ''
  } else if (assertion.type === 'response_time') {
    assertion.expected = '1000'
    assertion.expr = ''
  }
}

function methodType(method) {
  const map = { GET: '', POST: 'warning', PUT: 'info', DELETE: 'danger', PATCH: '' }
  return map[method?.toUpperCase()] || ''
}

function taskStatusType(status) {
  const map = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function taskStatusLabel(status) {
  const map = { pending: '待执行', running: '进行中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  projectsStore.fetchProjects()
  loadCases()
  loadTasks()
})
</script>

<style scoped>
.api-test-view {
  padding: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mt-16 {
  margin-top: 16px;
}

.mt-12 {
  margin-top: 12px;
}

.mr-4 {
  margin-right: 4px;
}

.assertions-list {
  margin-bottom: 8px;
}

.assertion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.run-result {
  padding: 0 4px;
}

.result-section {
  margin-top: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}

.task-result-card {
  padding: 14px 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
  margin-top: 12px;
}

.task-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.task-result-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 16px;
  margin-bottom: 8px;
}

.task-meta-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  line-height: 1.7;
}

.task-meta-url,
.task-meta-full {
  grid-column: 1 / -1;
}

.result-label {
  flex: 0 0 56px;
  color: #909399;
  font-size: 13px;
}

.task-meta-item code {
  flex: 1;
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-all;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 6px 10px;
  color: #303133;
}

.code-block {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 10px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.api-form :deep(.el-textarea__inner) {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

@media (max-width: 900px) {
  .task-result-meta {
    grid-template-columns: 1fr;
  }
}
</style>

<style>
.task-result-card {
  padding: 14px 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
  margin-top: 12px;
}

.task-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.task-result-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 16px;
  margin-bottom: 8px;
}

.task-meta-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  line-height: 1.7;
}

.task-meta-url,
.task-meta-full {
  grid-column: 1 / -1;
}

.result-label {
  flex: 0 0 56px;
  color: #909399;
  font-size: 13px;
}

.task-meta-item code {
  flex: 1;
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-all;
  background: rgba(64, 158, 255, 0.08);
  border-radius: 6px;
  padding: 2px 8px;
  color: #303133;
}

@media (max-width: 900px) {
  .task-result-meta {
    grid-template-columns: 1fr;
  }
}
</style>
