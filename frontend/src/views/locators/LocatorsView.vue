<template>
  <div class="locators-view">
    <PageHeader title="元素定位器" :crumbs="['首页', '元素定位器']">
      <template #actions>
        <el-select
          v-model="currentProjectId"
          placeholder="选择项目"
          style="width: 160px"
          @change="onProjectChange"
        >
          <el-option
            v-for="project in projectsStore.projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-button @click="handleImport" :disabled="!currentProjectId">
          <el-icon><Upload /></el-icon>
          导入 JSON
        </el-button>
        <el-button @click="handleExport" :disabled="!currentProjectId">
          <el-icon><Download /></el-icon>
          导出 JSON
        </el-button>
        <el-button
          v-if="pages.length === 0 && currentProjectId"
          type="warning"
          :loading="loadingSample"
          @click="loadSampleData"
        >
          <el-icon><MagicStick /></el-icon>
          加载示例数据
        </el-button>
        <el-button type="primary" :disabled="!currentProjectId" @click="showAddPageDialog">
          <el-icon><Plus /></el-icon>
          新建页面
        </el-button>
      </template>
    </PageHeader>

    <ConfirmDialog
      v-model="deleteDialogVisible"
      :title="deleteTarget.type === 'page' ? '删除页面' : '删除元素'"
      :message="deleteMessage"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <el-card shadow="never" class="mt-16">
      <div class="split-panel">
        <div class="page-list">
          <div class="panel-title">页面</div>
          <div v-if="pages.length" class="page-list-items">
            <div
              v-for="page in pages"
              :key="page"
              class="page-list-item"
              :class="{ active: currentPage === page }"
              @click="onPageSelect(page)"
            >
              <span class="page-name">{{ page }}</span>
              <div class="page-actions" @click.stop>
                <el-button size="small" link @click="showAddElementDialog(page)">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button size="small" link @click="askDeletePage(page)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else-if="currentProjectId" description="暂无页面">
            <template #image>
              <div style="text-align: center">
                <div style="font-size: 42px; margin-bottom: 8px">Locator</div>
                <div style="color: #999; font-size: 13px">当前项目还没有可管理的定位器</div>
              </div>
            </template>
            <el-button type="warning" size="small" :loading="loadingSample" @click="loadSampleData">
              一键加载示例数据
            </el-button>
          </el-empty>
          <el-empty v-else description="请先选择项目" />
        </div>

        <div class="element-list">
          <div class="panel-title">
            {{ currentPage ? `页面：${currentPage}` : '元素列表' }}
          </div>

          <div v-if="currentPage && elements.length" class="element-table-wrap">
            <el-table :data="elements" stripe size="small">
              <el-table-column prop="element_key" label="Key" width="180">
                <template #default="{ row }">
                  <code class="key-badge">{{ row.element_key }}</code>
                </template>
              </el-table-column>
              <el-table-column label="主策略" width="120">
                <template #default="{ row }">
                  <el-tag size="small" type="success">{{ row.primary_type || row.selector_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="主值" min-width="260">
                <template #default="{ row }">
                  <span class="selector-text">{{ displayStrategyValue(getPrimaryStrategy(row)) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="策略数" width="90">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.strategies?.length || 1 }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="策略详情" min-width="260">
                <template #default="{ row }">
                  <div class="strategy-summary-list">
                    <div
                      v-for="strategy in (row.strategies || []).slice(0, 3)"
                      :key="strategyKey(strategy)"
                      class="strategy-summary-item"
                    >
                      <el-tag size="small" :type="strategy.enabled === false ? 'info' : 'warning'">
                        {{ strategy.type }}
                      </el-tag>
                      <span class="strategy-summary-text">{{ displayStrategyValue(strategy) }}</span>
                    </div>
                    <span v-if="(row.strategies || []).length > 3" class="strategy-more">
                      还有 {{ row.strategies.length - 3 }} 条...
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="说明" min-width="140" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link @click="showEditElementDialog(row)">
                    编辑
                  </el-button>
                  <el-button size="small" type="danger" link @click="askDeleteElement(row.id)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-empty v-else-if="currentPage" :description="`页面“${currentPage}”暂无元素`">
            <el-button type="primary" size="small" @click="showAddElementDialog(currentPage)">
              添加元素
            </el-button>
          </el-empty>
          <el-empty v-else description="请从左侧选择一个页面" />
        </div>
      </div>
    </el-card>

    <el-dialog v-model="pageDialogVisible" :title="pageDialogTitle" width="420px">
      <el-form :model="pageForm" label-width="80px">
        <el-form-item label="页面名称" required>
          <el-input v-model="pageForm.page_name" placeholder="如：login、task_list" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pageDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePage">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="elementDialogVisible" :title="elementDialogTitle" width="880px">
      <el-form :model="elementForm" label-width="90px">
        <el-form-item label="页面" v-if="elementForm.page_name">
          <span>{{ elementForm.page_name }}</span>
        </el-form-item>
        <el-form-item label="Element Key" required>
          <el-input
            v-model="elementForm.element_key"
            placeholder="如：username、submit_btn"
            :disabled="elementDialogMode === 'edit'"
          />
        </el-form-item>
        <el-form-item label="主策略类型">
          <el-select v-model="elementForm.primary_type" style="width: 100%">
            <el-option
              v-for="type in locatorTypes"
              :key="type"
              :label="type"
              :value="type"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="elementForm.description" placeholder="元素用途说明" />
        </el-form-item>
      </el-form>

      <div class="strategies-section">
        <div class="strategies-header">
          <div class="strategies-title">定位策略</div>
          <el-button size="small" type="primary" plain @click="addStrategy">
            <el-icon><Plus /></el-icon>
            添加策略
          </el-button>
        </div>

        <div v-if="elementForm.strategies.length" class="strategies-list">
          <div
            v-for="(strategy, index) in elementForm.strategies"
            :key="strategy.local_id"
            class="strategy-card"
            :class="{ primary: isPrimaryStrategy(strategy) }"
          >
            <div class="strategy-card-header">
              <div class="strategy-card-title">
                <el-tag size="small" type="success">优先级 {{ strategy.priority }}</el-tag>
                <el-tag v-if="isPrimaryStrategy(strategy)" size="small" type="danger">主策略</el-tag>
              </div>
              <el-button
                size="small"
                type="danger"
                link
                :disabled="elementForm.strategies.length === 1"
                @click="removeStrategy(index)"
              >
                删除
              </el-button>
            </div>

            <div class="strategy-grid">
              <el-form-item label="类型" label-width="70px">
                <el-select v-model="strategy.type" style="width: 100%">
                  <el-option
                    v-for="type in locatorTypes"
                    :key="type"
                    :label="type"
                    :value="type"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="优先级" label-width="70px">
                <el-input-number
                  v-model="strategy.priority"
                  :min="1"
                  :max="20"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="置信度" label-width="70px">
                <el-input v-model="strategy.confidence" placeholder="如：0.95" />
              </el-form-item>
              <el-form-item label="启用" label-width="70px">
                <el-switch v-model="strategy.enabled" />
              </el-form-item>
            </div>

            <el-form-item label="值" label-width="70px" class="strategy-value-item">
              <el-input
                v-model="strategy.value_text"
                type="textarea"
                :rows="strategy.type === 'role' ? 4 : 2"
                :placeholder="strategyValuePlaceholder(strategy.type)"
              />
            </el-form-item>
          </div>
        </div>

        <el-empty v-else description="请至少添加一条策略" />
      </div>

      <template #footer>
        <el-button @click="elementDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveElement">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="导入 locators.json" width="500px" destroy-on-close>
      <el-form :model="importForm" label-width="80px">
        <el-form-item label="项目" required>
          <el-select v-model="importForm.project_id" placeholder="选择项目" style="width: 100%">
            <el-option
              v-for="project in projectsStore.projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="JSON 文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".json"
            :on-change="onImportFileChange"
          >
            <el-button>选择 JSON 文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持旧版 locators.json 和新版 strategies 格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Download, MagicStick, Plus, Upload } from '@element-plus/icons-vue'

import ConfirmDialog from '../../components/ConfirmDialog.vue'
import PageHeader from '../../components/PageHeader.vue'
import { locatorsApi } from '../../api'
import { useProjectsStore } from '../../stores/projects'

const projectsStore = useProjectsStore()

const locatorTypes = ['css', 'xpath', 'text', 'label', 'placeholder', 'testid', 'role']

const currentProjectId = ref(null)
const pages = ref([])
const elements = ref([])
const currentPage = ref('')
const saving = ref(false)
const loadingSample = ref(false)
const importing = ref(false)

const deleteDialogVisible = ref(false)
const deleteTarget = ref({ type: '', name: '', id: null, page: '' })

const pageDialogVisible = ref(false)
const pageDialogMode = ref('create')
const pageForm = ref({ page_name: '' })

const elementDialogVisible = ref(false)
const elementDialogMode = ref('create')
const elementForm = ref(createEmptyElementForm())

const importDialogVisible = ref(false)
const importForm = ref({ project_id: null })
const importFileRaw = ref(null)
const uploadRef = ref(null)

const pageDialogTitle = computed(() => (pageDialogMode.value === 'create' ? '新建页面' : '编辑页面'))
const elementDialogTitle = computed(() => (elementDialogMode.value === 'create' ? '添加元素' : '编辑元素'))
const deleteMessage = computed(() => {
  if (deleteTarget.value.type === 'page') {
    return `确认删除页面“${deleteTarget.value.name}”及其所有元素？`
  }
  return '确认删除该元素？'
})

function createStrategyForm(strategy = {}, index = 0) {
  const value = strategy.value ?? ''
  return {
    local_id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
    type: strategy.type || 'css',
    priority: strategy.priority || index + 1,
    confidence: strategy.confidence ?? '',
    enabled: strategy.enabled !== false,
    value_text: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }
}

function createEmptyElementForm(pageName = '') {
  return {
    id: null,
    page_name: pageName,
    element_key: '',
    description: '',
    primary_type: 'css',
    strategies: [createStrategyForm({ type: 'css', value: '', priority: 1, enabled: true }, 0)],
  }
}

function normalizeElementStrategies(row) {
  if (Array.isArray(row?.strategies) && row.strategies.length) {
    return row.strategies
      .slice()
      .sort((a, b) => (a.priority || 999) - (b.priority || 999))
      .map((strategy, index) => createStrategyForm(strategy, index))
  }

  return [createStrategyForm({
    type: row?.selector_type || row?.primary_type || 'css',
    value: row?.selector || '',
    priority: row?.priority || 1,
    enabled: true,
  }, 0)]
}

function parseStrategyValue(strategy) {
  const raw = (strategy.value_text || '').trim()
  if (!raw) return ''
  if (strategy.type === 'role') {
    try {
      return JSON.parse(raw)
    } catch {
      return raw
    }
  }
  return raw
}

function getPrimaryStrategy(row) {
  if (Array.isArray(row?.strategies) && row.strategies.length) {
    return row.strategies
      .slice()
      .sort((a, b) => (a.priority || 999) - (b.priority || 999))
      .find((strategy) => strategy.enabled !== false) || row.strategies[0]
  }
  return {
    type: row?.primary_type || row?.selector_type || 'css',
    value: row?.selector || '',
    priority: row?.priority || 1,
    enabled: true,
  }
}

function isPrimaryStrategy(strategy) {
  return strategy.type === elementForm.value.primary_type
}

function displayStrategyValue(strategy) {
  if (!strategy) return ''
  const value = strategy.value ?? strategy.value_text ?? ''
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function strategyKey(strategy) {
  return `${strategy.type}_${strategy.priority}_${displayStrategyValue(strategy)}`
}

function strategyValuePlaceholder(type) {
  if (type === 'role') {
    return '{"role":"button","name":"立即登录"}'
  }
  if (type === 'xpath') {
    return "//button[contains(., '立即登录')]"
  }
  if (type === 'label') {
    return '我已阅读并同意'
  }
  return "如：button:has-text('立即登录')"
}

function buildElementPayload() {
  const strategies = elementForm.value.strategies
    .map((strategy, index) => ({
      type: strategy.type || 'css',
      value: parseStrategyValue(strategy),
      priority: strategy.priority || index + 1,
      confidence: strategy.confidence === '' ? null : strategy.confidence,
      enabled: strategy.enabled !== false,
    }))
    .sort((a, b) => (a.priority || 999) - (b.priority || 999))

  const primary = strategies.find((strategy) => strategy.enabled !== false) || strategies[0]
  const primaryValue = primary?.value ?? ''

  return {
    selector: typeof primaryValue === 'string' ? primaryValue : JSON.stringify(primaryValue),
    selector_type: primary?.type || elementForm.value.primary_type || 'css',
    priority: primary?.priority || 1,
    primary_type: elementForm.value.primary_type || primary?.type || 'css',
    description: elementForm.value.description || '',
    strategies,
  }
}

async function loadPages(force = false) {
  if (!currentProjectId.value) {
    pages.value = []
    return
  }
  try {
    pages.value = await locatorsApi.listPages(currentProjectId.value)

    if (pages.value.length && !pages.value.includes(currentPage.value)) {
      currentPage.value = pages.value[0]
      await loadElements()
      return
    }

    if (!force && pages.value.length && currentPage.value && elements.value.length > 0) {
      return
    }

    if (currentPage.value && pages.value.includes(currentPage.value)) {
      await loadElements()
    }
  } catch {
    ElMessage.error('加载页面列表失败')
  }
}

async function loadElements() {
  if (!currentProjectId.value || !currentPage.value) {
    elements.value = []
    return
  }
  try {
    const data = await locatorsApi.list(currentProjectId.value, currentPage.value)
    elements.value = data.filter((item) => item.element_key !== '__page__')
  } catch {
    ElMessage.error('加载元素列表失败')
  }
}

async function onPageSelect(page) {
  if (currentPage.value === page && elements.value.length > 0) {
    return
  }
  currentPage.value = page
  elements.value = []
  await loadElements()
}

async function onProjectChange() {
  currentPage.value = ''
  elements.value = []
  await loadPages(true)
}

function showAddPageDialog() {
  pageDialogMode.value = 'create'
  pageForm.value = { page_name: '' }
  pageDialogVisible.value = true
}

async function savePage() {
  const pageName = pageForm.value.page_name?.trim()
  if (!pageName) {
    ElMessage.warning('请输入页面名称')
    return
  }
  if (pages.value.includes(pageName)) {
    ElMessage.warning(`页面“${pageName}”已存在`)
    return
  }

  saving.value = true
  try {
    await locatorsApi.create({
      project_id: currentProjectId.value,
      page_name: pageName,
      element_key: '__page__',
      selector: '/',
      selector_type: 'css',
      priority: 4,
      primary_type: 'css',
      description: '[系统页面标记]',
      strategies: [
        { type: 'css', value: '/', priority: 4, enabled: true },
      ],
    })
    pageDialogVisible.value = false
    currentPage.value = pageName
    ElMessage.success(`页面“${pageName}”创建成功`)
    await loadPages(true)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function askDeletePage(page) {
  deleteTarget.value = { type: 'page', name: page, page }
  deleteDialogVisible.value = true
}

function askDeleteElement(id) {
  deleteTarget.value = { type: 'element', id }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  const { type, page, id } = deleteTarget.value
  try {
    if (type === 'page') {
      const all = await locatorsApi.list(currentProjectId.value, page)
      for (const item of all) {
        await locatorsApi.delete(item.id)
      }
      if (currentPage.value === page) {
        currentPage.value = ''
        elements.value = []
      }
      await loadPages(true)
      ElMessage.success('页面已删除')
    } else if (type === 'element') {
      await locatorsApi.delete(id)
      await loadElements()
      ElMessage.success('元素已删除')
    }
  } catch {
    ElMessage.error('删除失败')
  } finally {
    done()
  }
}

function showAddElementDialog(page) {
  elementDialogMode.value = 'create'
  elementForm.value = createEmptyElementForm(page)
  elementDialogVisible.value = true
}

function showEditElementDialog(row) {
  elementDialogMode.value = 'edit'
  elementForm.value = {
    id: row.id,
    page_name: row.page_name,
    element_key: row.element_key,
    description: row.description || '',
    primary_type: row.primary_type || row.selector_type || 'css',
    strategies: normalizeElementStrategies(row),
  }
  elementDialogVisible.value = true
}

function addStrategy() {
  elementForm.value.strategies.push(
    createStrategyForm(
      { type: elementForm.value.primary_type || 'css', value: '', priority: elementForm.value.strategies.length + 1, enabled: true },
      elementForm.value.strategies.length,
    ),
  )
}

function removeStrategy(index) {
  if (elementForm.value.strategies.length === 1) {
    ElMessage.warning('至少保留一条策略')
    return
  }
  elementForm.value.strategies.splice(index, 1)
}

async function saveElement() {
  const elementKey = elementForm.value.element_key?.trim()
  if (!elementKey) {
    ElMessage.warning('请输入 Element Key')
    return
  }

  const hasValidStrategy = elementForm.value.strategies.some((strategy) => (strategy.value_text || '').trim())
  if (!hasValidStrategy) {
    ElMessage.warning('请至少填写一条有效策略')
    return
  }

  saving.value = true
  try {
    const payload = buildElementPayload()
    if (elementDialogMode.value === 'create') {
      await locatorsApi.create({
        project_id: currentProjectId.value,
        page_name: elementForm.value.page_name,
        element_key: elementKey,
        ...payload,
      })
      ElMessage.success('元素添加成功')
    } else {
      await locatorsApi.update(elementForm.value.id, payload)
      ElMessage.success('元素更新成功')
    }
    elementDialogVisible.value = false
    await loadElements()
  } catch (error) {
    if (error.response?.status === 409) {
      ElMessage.warning('Element Key 已存在')
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

function handleImport() {
  importForm.value.project_id = currentProjectId.value
  importFileRaw.value = null
  importDialogVisible.value = true
}

function onImportFileChange(file) {
  importFileRaw.value = file.raw
}

async function doImport() {
  if (!importForm.value.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!importFileRaw.value) {
    ElMessage.warning('请选择 JSON 文件')
    return
  }
  importing.value = true
  try {
    const text = await importFileRaw.value.text()
    const json = JSON.parse(text)
    await locatorsApi.import(importForm.value.project_id, json)
    importDialogVisible.value = false
    ElMessage.success('导入成功')
    await loadPages(true)
  } catch (error) {
    if (error instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误')
    } else {
      ElMessage.error('导入失败')
    }
  } finally {
    importing.value = false
  }
}

async function handleExport() {
  if (!currentProjectId.value) return
  try {
    const data = await locatorsApi.export(currentProjectId.value)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `locators_project${currentProjectId.value}.json`
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function loadSampleData() {
  if (!currentProjectId.value) return
  loadingSample.value = true
  try {
    const result = await locatorsApi.initSample(currentProjectId.value)
    ElMessage.success(result.message || '示例数据加载成功')
    await loadPages(true)
    if (!currentPage.value && pages.value.length > 0) {
      currentPage.value = pages.value[0]
      await loadElements()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载示例数据失败')
  } finally {
    loadingSample.value = false
  }
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (projectsStore.projects.length) {
    currentProjectId.value = projectsStore.projects[0].id
    await loadPages(true)
  }
})

watch(
  () => currentPage.value,
  async (newPage) => {
    if (!newPage) {
      elements.value = []
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 50))
    await loadElements()
  },
)
</script>

<style scoped>
.locators-view {
  padding: 16px;
}

.split-panel {
  display: flex;
  gap: 0;
  min-height: 500px;
}

.page-list {
  width: 220px;
  border-right: 1px solid var(--el-border-color);
  padding-right: 0;
  flex-shrink: 0;
}

.element-list {
  flex: 1;
  padding-left: 16px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.page-list-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--el-text-color-regular);
  transition: background 0.2s, color 0.2s;
}

.page-list-item:hover {
  background: var(--el-fill-color-light);
}

.page-list-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}

.page-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}

.page-list-item:hover .page-actions {
  opacity: 1;
  pointer-events: auto;
}

.page-actions :deep(.el-button) {
  cursor: pointer;
}

.key-badge {
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 2px 6px;
  border-radius: 4px;
}

.selector-text,
.strategy-summary-text {
  font-size: 12px;
  font-family: Consolas, Monaco, monospace;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.strategy-summary-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.strategy-summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.strategy-more {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.element-table-wrap {
  overflow-x: auto;
}

.strategies-section {
  margin-top: 8px;
  border-top: 1px solid var(--el-border-color-light);
  padding-top: 16px;
}

.strategies-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.strategies-title {
  font-size: 14px;
  font-weight: 600;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-card {
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 14px;
  background: #fff;
}

.strategy-card.primary {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.strategy-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.strategy-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.strategy-value-item {
  margin-top: 4px;
  margin-bottom: 0;
}

.mt-16 {
  margin-top: 0;
}

@media (max-width: 960px) {
  .split-panel {
    flex-direction: column;
  }

  .page-list {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--el-border-color);
    padding-bottom: 16px;
    margin-bottom: 16px;
  }

  .element-list {
    padding-left: 0;
  }

  .strategy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
