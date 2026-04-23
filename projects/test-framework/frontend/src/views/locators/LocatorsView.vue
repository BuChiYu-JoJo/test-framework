<template>
  <div class="locators-view">
    <!-- 顶部工具栏 -->
    <PageHeader title="元素定位器" :crumbs="['首页', '元素定位器']">
      <template #actions>
        <el-select
          v-model="currentProjectId"
          placeholder="选择项目"
          style="width: 160px"
          @change="onProjectChange"
        >
          <el-option
            v-for="p in projectsStore.projects"
            :key="p.id"
            :label="p.name"
            :value="p.id"
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
          @click="loadSampleData"
          :loading="loadingSample"
        >
          <el-icon><MagicStick /></el-icon>
          加载示例数据
        </el-button>
        <el-button type="primary" @click="showAddPageDialog" :disabled="!currentProjectId">
          <el-icon><Plus /></el-icon>
          新建页面
        </el-button>
      </template>
    </PageHeader>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="deleteDialogVisible"
      :title="deleteTarget.type === 'page' ? '删除页面' : '删除元素'"
      :message="deleteTarget.type === 'page' ? `确认删除页面「${deleteTarget.name}」及其所有元素？` : '确认删除该元素？'"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <el-card shadow="never" class="mt-16">
      <div class="split-panel">
        <!-- 左侧：页面列表 -->
        <div class="page-list">
          <div class="panel-title">页面</div>
          <div class="page-list-items" v-if="pages.length">
            <div
              v-for="page in pages"
              :key="page"
              class="page-list-item"
              :class="{ active: currentPage === page }"
              @click="onPageSelect(page)"
            >
              <span class="page-name">{{ page }}</span>
              <div class="page-actions" @click.stop>
                <el-button
                  size="small"
                  link
                  @click="showAddElementDialog(page)"
                >
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button size="small" link @click="askDeletePage(page)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
          <el-empty
            v-else-if="currentProjectId"
            description="暂无页面"
          >
            <template #image>
              <div style="text-align:center">
                <div style="font-size:48px;margin-bottom:8px">📄</div>
                <div style="color:#999;font-size:13px">项目暂无 Locators 数据</div>
              </div>
            </template>
            <el-button type="warning" size="small" @click="loadSampleData" :loading="loadingSample">
              一键加载示例数据
            </el-button>
          </el-empty>
          <el-empty v-else description="请先选择项目" />
        </div>

        <!-- 右侧：元素列表 -->
        <div class="element-list">
          <div class="panel-title">
            {{ currentPage ? `页面：${currentPage}` : '元素列表' }}
          </div>

          <div v-if="currentPage && elements.length" class="element-table-wrap">
            <el-table :data="elements" stripe size="small">
              <el-table-column prop="element_key" label="Key" width="160">
                <template #default="{ row }">
                  <code class="key-badge">{{ row.element_key }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="selector" label="Selector" min-width="240">
                <template #default="{ row }">
                  <span class="selector-text">{{ row.selector }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="selector_type" label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.selector_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="priority" label="优先级" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="priorityType(row.priority)">
                    P{{ row.priority }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="说明" min-width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link @click="showEditElementDialog(row)">
                    编辑
                  </el-button>
                  <el-button size="small" type="danger" link @click="askDeleteElement(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-empty v-else-if="currentPage" :description="`页面「${currentPage}」暂无元素`">
            <el-button type="primary" size="small" @click="showAddElementDialog(currentPage)">
              添加元素
            </el-button>
          </el-empty>
          <el-empty v-else description="请从左侧选择一个页面" />
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑页面对话框 -->
    <el-dialog v-model="pageDialogVisible" :title="pageDialogTitle" width="400px">
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

    <!-- 新建/编辑元素对话框 -->
    <el-dialog v-model="elementDialogVisible" :title="elementDialogTitle" width="600px">
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
        <el-form-item label="Selector" required>
          <el-input
            v-model="elementForm.selector"
            placeholder="如：input[name='account']、button:has-text('登录')"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="elementForm.selector_type" style="width: 100%">
            <el-option label="CSS" value="css" />
            <el-option label="XPath" value="xpath" />
            <el-option label="Text" value="text" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="elementForm.priority" style="width: 100%">
            <el-option label="P1（最高）" :value="1" />
            <el-option label="P2" :value="2" />
            <el-option label="P3" :value="3" />
            <el-option label="P4（最低）" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="elementForm.description" placeholder="元素用途说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="elementDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveElement">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入 locators.json" width="500px" destroy-on-close>
      <el-form :model="importForm" label-width="80px">
        <el-form-item label="项目" required>
          <el-select v-model="importForm.project_id" placeholder="选择项目" style="width: 100%">
            <el-option
              v-for="p in projectsStore.projects"
              :key="p.id"
              :label="p.name"
              :value="p.id"
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
              <div class="el-upload__tip">支持从项目导出的 locators.json 格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 隐藏的文件输入（导出用） -->
    <input type="file" ref="exportFileInput" style="display:none" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Upload, Download, MagicStick } from '@element-plus/icons-vue'
import { useProjectsStore } from '../../stores/projects'
import { locatorsApi } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import PageHeader from '../../components/PageHeader.vue'

const projectsStore = useProjectsStore()

// 状态
const currentProjectId = ref(null)
const pages = ref([])
const elements = ref([])
const currentPage = ref('')
const saving = ref(false)
const loadingSample = ref(false)
const importing = ref(false)

// 删除确认
const deleteDialogVisible = ref(false)
const deleteTarget = ref({ type: '', name: '', id: null })

// 页面对话框
const pageDialogVisible = ref(false)
const pageDialogMode = ref('create')
const pageForm = ref({ page_name: '' })

// 元素对话框
const elementDialogVisible = ref(false)
const elementDialogMode = ref('create')
const elementForm = ref({
  id: null,
  page_name: '',
  element_key: '',
  selector: '',
  selector_type: 'css',
  priority: 1,
  description: '',
})

// 导入对话框
const importDialogVisible = ref(false)
const importForm = ref({ project_id: null })
const importFileRaw = ref(null)
const uploadRef = ref(null)

// 计算属性
const pageDialogTitle = computed(() => (pageDialogMode.value === 'create' ? '新建页面' : '编辑页面'))
const elementDialogTitle = computed(() =>
  elementDialogMode.value === 'create' ? '添加元素' : '编辑元素'
)

// 加载页面列表
async function loadPages(force = false) {
  if (!currentProjectId.value) {
    pages.value = []
    return
  }
  try {
    // 直接拿页面列表（后端去重），不再前端过滤
    pages.value = await locatorsApi.listPages(currentProjectId.value)

    if (pages.value.length && !pages.value.includes(currentPage.value)) {
      if (!currentPage.value) {
        currentPage.value = pages.value[0]
        await loadElements()
      }
    } else if (!force && pages.value.length && currentPage.value && elements.value.length > 0) {
      return
    }
    if (currentPage.value && pages.value.includes(currentPage.value)) {
      await loadElements()
    }
  } catch (e) {
    ElMessage.error('加载页面列表失败')
  }
}

// 加载当前页面的元素
async function loadElements() {
  if (!currentProjectId.value || !currentPage.value) {
    elements.value = []
    return
  }
  try {
    const data = await locatorsApi.list(currentProjectId.value, currentPage.value)
    // 过滤掉系统页面标记
    elements.value = data.filter(el => el.element_key !== '__page__')
  } catch (e) {
    ElMessage.error('加载元素列表失败')
  }
}

// 切换页面
async function onPageSelect(page) {
  if (currentPage.value === page && elements.value.length > 0) {
    return  // already selected, no reload needed
  }
  currentPage.value = page
  elements.value = []  // clear immediately for snappy UI
  await loadElements()  // loadElements already sets currentPage.value as query param
}

// 切换项目
async function onProjectChange() {
  currentPage.value = ''
  elements.value = []
  await loadPages()
}

// 新建页面
function showAddPageDialog() {
  pageDialogMode.value = 'create'
  pageForm.value = { page_name: '' }
  pageDialogVisible.value = true
}

async function savePage() {
  if (!pageForm.value.page_name?.trim()) {
    ElMessage.warning('请输入页面名称')
    return
  }
  const pageName = pageForm.value.page_name.trim()

  // 检查是否已存在（通过查询现有页面列表）
  if (pages.value.includes(pageName)) {
    ElMessage.warning('页面「' + pageName + '」已存在')
    return
  }

  saving.value = true
  try {
    if (pageDialogMode.value === 'create') {
      // 创建一个带特殊标记的元素，用于标识页面存在
      await locatorsApi.create({
        project_id: currentProjectId.value,
        page_name: pageName,
        element_key: '__page__',
        selector: '/',
        selector_type: 'css',
        priority: 4,
        description: '[系统页面标记]',
      })
      ElMessage.success('页面「' + pageName + '」创建成功')
    }
    pageDialogVisible.value = false
    await loadPages()
    if (!pages.value.includes(currentPage.value)) {
      currentPage.value = pageName
    }
  } catch (e) {
    if (e.response?.status === 409 || String(e.response?.data?.detail || '').includes('已存在') || String(e.response?.data?.detail || '').includes('unique')) {
      ElMessage.warning('页面「' + pageName + '」已存在')
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

// 删除页面
function askDeletePage(page) {
  deleteTarget.value = { type: 'page', name: page, page }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  const { type, name, page, id } = deleteTarget.value
  try {
    if (type === 'page') {
      const all = await locatorsApi.list(currentProjectId.value, page)
      for (const el of all) {
        await locatorsApi.delete(el.id)
      }
      if (currentPage.value === page) {
        currentPage.value = ''
        elements.value = []
      }
      await loadPages(true)  // force refresh after delete
      ElMessage.success('页面已删除')
    } else if (type === 'element') {
      await locatorsApi.delete(id)
      await loadElements()
      ElMessage.success('元素已删除')
    }
    done()
  } catch (e) {
    ElMessage.error('删除失败')
    done()
  }
}

// 新建元素
function showAddElementDialog(page) {
  elementDialogMode.value = 'create'
  elementForm.value = {
    id: null,
    page_name: page,
    element_key: '',
    selector: '',
    selector_type: 'css',
    priority: 1,
    description: '',
  }
  elementDialogVisible.value = true
}

// 编辑元素
function showEditElementDialog(row) {
  elementDialogMode.value = 'edit'
  elementForm.value = { ...row }
  elementDialogVisible.value = true
}

async function saveElement() {
  if (!elementForm.value.element_key?.trim()) {
    ElMessage.warning('请输入 Element Key')
    return
  }
  if (!elementForm.value.selector?.trim()) {
    ElMessage.warning('请输入 Selector')
    return
  }
  saving.value = true
  try {
    if (elementDialogMode.value === 'create') {
      await locatorsApi.create({
        project_id: currentProjectId.value,
        page_name: elementForm.value.page_name,
        element_key: elementForm.value.element_key.trim(),
        selector: elementForm.value.selector.trim(),
        selector_type: elementForm.value.selector_type,
        priority: elementForm.value.priority,
        description: elementForm.value.description || '',
      })
      ElMessage.success('元素添加成功')
    } else {
      await locatorsApi.update(elementForm.value.id, {
        selector: elementForm.value.selector.trim(),
        selector_type: elementForm.value.selector_type,
        priority: elementForm.value.priority,
        description: elementForm.value.description || '',
      })
      ElMessage.success('元素更新成功')
    }
    elementDialogVisible.value = false
    await loadElements()
  } catch (e) {
    if (e.response?.status === 409) {
      ElMessage.warning('Element Key 已存在')
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

function askDeleteElement(id) {
  deleteTarget.value = { type: 'element', id }
  deleteDialogVisible.value = true
}

// 导入
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
    await loadPages()
  } catch (e) {
    if (e instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误')
    } else {
      ElMessage.error('导入失败')
    }
  } finally {
    importing.value = false
  }
}

// 导出
async function handleExport() {
  if (!currentProjectId.value) return
  try {
    const data = await locatorsApi.export(currentProjectId.value)
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `locators_project${currentProjectId.value}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function loadSampleData() {
  if (!currentProjectId.value) return
  loadingSample.value = true
  try {
    const result = await locatorsApi.initSample(currentProjectId.value)
    ElMessage.success(result.message || `示例数据加载成功`)
    await loadPages()
    // Keep current page selection if already set, otherwise select first page
    if (!currentPage.value && pages.value.length > 0) {
      currentPage.value = pages.value[0]
      await loadElements()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载示例数据失败')
  } finally {
    loadingSample.value = false
  }
}

// 优先级颜色
function priorityType(p) {
  return { 1: 'danger', 2: 'warning', 3: 'info', 4: '' }[p] || 'info'
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (projectsStore.projects.length) {
    currentProjectId.value = projectsStore.projects[0].id
    await loadPages()
  }
})
// Safety net: watch currentPage to reload elements (in case el-menu @select misses)
watch(
  () => currentPage.value,
  async (newPage) => {
    if (!newPage) {
      elements.value = []
      return
    }
    // Small delay to let DOM settle
    await new Promise(r => setTimeout(r, 50))
    await loadElements()
  }
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

.selector-text {
  font-size: 12px;
  font-family: Consolas, Monaco, monospace;
  color: var(--el-text-color-regular);
}

.element-table-wrap {
  overflow-x: auto;
}

.mt-16 {
  margin-top: 0;
}
</style>
