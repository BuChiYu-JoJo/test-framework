<template>
  <div class="ai-tools-view">
    <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
      <el-select v-model="currentProjectId" placeholder="选择项目" style="width: 160px" @change="onProjectChange">
        <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" class="ai-tabs">
        <!-- Tab1: AI 生成 Locators -->
        <el-tab-pane label="AI 生成 Locators" name="locators">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              输入页面 URL，AI 将分析页面元素并生成最优的定位符（支持 CSS/XPath）
            </el-alert>

            <el-form label-width="130px" style="max-width: 800px">
              <el-form-item label="页面 URL">
                <el-input v-model="locatorForm.url" placeholder="https://example.com/order/list" clearable />
              </el-form-item>
              <el-form-item label="页面名称">
                <el-input v-model="locatorForm.pageName" placeholder="order_list" clearable style="width: 200px" />
              </el-form-item>
              <el-form-item label="登录用例">
                <el-select v-model="locatorForm.loginCaseId" placeholder="选择登录用例（可选）" clearable style="width: 300px">
                  <el-option v-for="c in loginCases" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
                <span style="margin-left: 12px; color: #999; font-size: 12px">留空则无需登录</span>
              </el-form-item>
              <el-form-item label="目标意图">
                <el-input
                  v-model="locatorForm.intent"
                  placeholder="如：点击新建订单按钮、搜索框"
                  style="width: 300px"
                />
              </el-form-item>
              <el-form-item label="视口">
                <el-input-number v-model="locatorForm.width" :min="800" :max="3840" style="width: 120px" />
                <span style="margin: 0 8px">×</span>
                <el-input-number v-model="locatorForm.height" :min="600" :max="2160" style="width: 120px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="locatorLoading" @click="generateLocators">
                  <el-icon><MagicStick /></el-icon>
                  生成 Locators
                </el-button>
                <el-button v-if="generatedLocators && Object.keys(generatedLocators).length" type="success" @click="saveLocators">
                  <el-icon><Download /></el-icon>
                  一键保存到项目
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 生成结果 -->
            <div v-if="generatedLocators && Object.keys(generatedLocators).length" class="result-section">
              <div class="result-title">生成的 Locators（{{ Object.keys(generatedLocators).length }} 个）</div>
              <el-table :data="locatorTableData" stripe size="small" max-height="400">
                <el-table-column prop="key" label="Key" width="200" />
                <el-table-column prop="type" label="Type" width="80">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.type === 'css' ? 'success' : 'warning'">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="Selector" min-width="300">
                  <template #default="{ row }">
                    <code class="selector-code">{{ row.value }}</code>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="confidenceType(row.confidence)">{{ row.confidence }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab2: AI 生成用例 -->
        <el-tab-pane label="AI 生成用例" name="cases">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              输入自然语言需求描述，AI 将生成结构化的 YAML 测试用例
            </el-alert>

            <el-form label-width="120px" style="max-width: 700px">
              <el-form-item label="需求描述">
                <el-input
                  v-model="caseForm.description"
                  type="textarea"
                  :rows="4"
                  placeholder="用户输入正确的账号密码后，点击登录按钮，系统跳转至首页"
                />
              </el-form-item>
              <el-form-item label="模块">
                <el-input v-model="caseForm.module" placeholder="login" clearable style="width: 200px" />
              </el-form-item>
              <el-form-item label="优先级">
                <el-select v-model="caseForm.priority" style="width: 200px">
                  <el-option label="P0 - 核心流程" value="P0" />
                  <el-option label="P1 - 重要功能" value="P1" />
                  <el-option label="P2 - 一般功能" value="P2" />
                  <el-option label="P3 - 边缘情况" value="P3" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="caseLoading" @click="generateCase">
                  <el-icon><MagicStick /></el-icon>
                  生成用例
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 生成结果 -->
            <div v-if="generatedYaml" class="result-section">
              <div class="result-title">生成的用例 YAML（ID: {{ generatedCaseId }}）</div>
              <div class="yaml-editor">
                <el-input
                  v-model="generatedYaml"
                  type="textarea"
                  :rows="15"
                  style="font-family: monospace; font-size: 13px"
                />
              </div>
              <div style="margin-top: 12px">
                <el-button type="success" @click="saveCase">
                  <el-icon><Download /></el-icon>
                  保存到项目
                </el-button>
                <el-button @click="copyYaml">
                  <el-icon><CopyDocument /></el-icon>
                  复制 YAML
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab3: 智能回归 -->
        <el-tab-pane label="智能回归" name="regression">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              输入变更文件列表，AI 将智能分析影响范围并推荐需要回归的用例
            </el-alert>

            <el-form label-width="120px" style="max-width: 700px">
              <el-form-item label="变更文件">
                <div class="file-list-editor">
                  <div v-for="(file, idx) in regressionForm.changedFiles" :key="idx" class="file-item">
                    <el-input v-model="regressionForm.changedFiles[idx]" placeholder="pages/login.vue" clearable />
                    <el-button type="danger" link @click="removeFile(idx)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button type="primary" link @click="addFile">
                    <el-icon><Plus /></el-icon> 添加文件
                  </el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="regressionLoading" @click="selectRegression">
                  <el-icon><MagicStick /></el-icon>
                  分析影响并选用例
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 分析结果 -->
            <div v-if="regressionResult.selected_cases && regressionResult.selected_cases.length" class="result-section">
              <el-alert :type="riskLevelType(regressionResult.risk_level)" :closable="false" style="margin-bottom: 12px">
                <template #title>
                  <strong>风险等级：{{ regressionResult.risk_level }}</strong>
                  &nbsp;&nbsp;影响模块：{{ regressionResult.impact_modules.join(', ') || '未知' }}
                </template>
                <div style="margin-top: 4px">{{ regressionResult.reason }}</div>
              </el-alert>

              <div class="result-title">推荐回归用例（{{ regressionResult.selected_cases.length }} 个）</div>
              <el-table :data="regressionResult.selected_cases" stripe size="small">
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
                <el-table-column prop="risk_score" label="风险评分" width="100">
                  <template #default="{ row }">
                    <el-progress
                      :percentage="Math.round((row.risk_score || 0.5) * 100)"
                      :color="riskScoreColor(row.risk_score)"
                      :stroke-width="10"
                    />
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-empty v-else-if="!regressionLoading && regressionResult.reason" description="暂未生成分析结果" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProjectsStore } from '../../stores/projects'
import { aiApi, casesApi, locatorsApi } from '../../api'
import { MagicStick, Download, Delete, Plus, CopyDocument } from '@element-plus/icons-vue'

const projectsStore = useProjectsStore()

const activeTab = ref('locators')
const currentProjectId = ref(null)

const onProjectChange = async () => {
  // 加载项目的登录用例供选择
  loginCases.value = []
  if (!currentProjectId.value) return
  try {
    const cases = await aiApi.listLoginCases(currentProjectId.value)
    loginCases.value = cases
  } catch (e) {
    console.warn('加载登录用例失败', e)
  }
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (projectsStore.projects.length && !currentProjectId.value) {
    currentProjectId.value = projectsStore.projects[0].id
    onProjectChange()
  }
})

// ─── Locators Tab ────────────────────────────────────────────────
const loginCases = ref([])

const locatorForm = ref({
  url: '',
  pageName: '',
  intent: '',
  loginCaseId: null,
  width: 1920,
  height: 1080,
})
const locatorLoading = ref(false)
const generatedLocators = ref(null)

const locatorTableData = computed(() => {
  if (!generatedLocators.value) return []
  return Object.entries(generatedLocators.value).map(([key, loc]) => ({
    key,
    type: loc.type || 'css',
    value: loc.value || loc.selector || '',
    confidence: loc.ai_confidence || loc.confidence || 'N/A',
  }))
})

async function generateLocators() {
  if (!locatorForm.value.url) {
    ElMessage.warning('请输入页面 URL')
    return
  }
  locatorLoading.value = true
  generatedLocators.value = null
  try {
    let result
    if (locatorForm.value.loginCaseId) {
      // 带登录态：先登录再分析
      result = await aiApi.generateLocatorsWithAuth({
        target_url: locatorForm.value.url,
        page_name: locatorForm.value.pageName,
        login_case_id: locatorForm.value.loginCaseId,
        project_id: currentProjectId.value,
        intent: locatorForm.value.intent,
        viewport_width: locatorForm.value.width,
        viewport_height: locatorForm.value.height,
      })
    } else {
      // 无登录：直接分析
      result = await aiApi.generateLocators({
        url: locatorForm.value.url,
        page_name: locatorForm.value.pageName,
        intent: locatorForm.value.intent,
        viewport_width: locatorForm.value.width,
        viewport_height: locatorForm.value.height,
      })
    }
    generatedLocators.value = result.locators || {}
    ElMessage.success(`生成了 ${Object.keys(generatedLocators.value).length} 个 locators`)
  } catch (e) {
    ElMessage.error(e.message || e.detail || '生成失败')
  } finally {
    locatorLoading.value = false
  }
}

async function saveLocators() {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!generatedLocators.value) return

  try {
    const pageName = locatorForm.value.pageName || new URL(locatorForm.value.url).pathname.replace('/', '')
    let saved = 0
    for (const [key, loc] of Object.entries(generatedLocators.value)) {
      await locatorsApi.create({
        project_id: currentProjectId.value,
        page_name: pageName,
        element_key: key,
        selector: loc.value || loc.selector || '',
        selector_type: loc.type || 'css',
        description: loc.description || '',
      })
      saved++
    }
    ElMessage.success(`已保存 ${saved} 个定位符到项目`)
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

function confidenceType(conf) {
  const v = parseFloat(conf)
  if (isNaN(v)) return 'info'
  if (v >= 0.9) return 'success'
  if (v >= 0.7) return 'warning'
  return 'danger'
}

// ─── Cases Tab ──────────────────────────────────────────────────
const caseForm = ref({
  description: '',
  module: 'default',
  priority: 'P2',
})
const caseLoading = ref(false)
const generatedYaml = ref('')
const generatedCaseId = ref('')

async function generateCase() {
  if (!caseForm.value.description) {
    ElMessage.warning('请输入需求描述')
    return
  }
  caseLoading.value = true
  try {
    const result = await aiApi.generateCase({
      description: caseForm.value.description,
      module: caseForm.value.module,
      priority: caseForm.value.priority,
    })
    generatedYaml.value = result.yaml_content || ''
    generatedCaseId.value = result.case_id || ''
    ElMessage.success('用例生成成功')
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    caseLoading.value = false
  }
}

async function saveCase() {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!generatedYaml.value) return

  try {
    await casesApi.create({
      project_id: currentProjectId.value,
      name: generatedCaseId.value,
      case_id: generatedCaseId.value,
      module: caseForm.value.module,
      priority: caseForm.value.priority,
      content: generatedYaml.value,
    })
    ElMessage.success('用例已保存到项目')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

function copyYaml() {
  navigator.clipboard.writeText(generatedYaml.value).then(() => {
    ElMessage.success('YAML 已复制到剪贴板')
  })
}

// ─── Regression Tab ──────────────────────────────────────────────
const regressionForm = ref({
  changedFiles: [''],
})
const regressionLoading = ref(false)
const regressionResult = ref({
  selected_cases: [],
  reason: '',
  impact_modules: [],
  risk_level: '',
})

function addFile() {
  regressionForm.value.changedFiles.push('')
}

function removeFile(idx) {
  regressionForm.value.changedFiles.splice(idx, 1)
}

async function selectRegression() {
  const files = regressionForm.value.changedFiles.filter(f => f.trim())
  if (!files.length) {
    ElMessage.warning('请至少输入一个变更文件')
    return
  }
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  regressionLoading.value = true
  try {
    const result = await aiApi.selectRegression({
      changed_files: files,
      project_id: currentProjectId.value,
    })
    regressionResult.value = result
    ElMessage.success(`分析完成，发现 ${result.selected_cases?.length || 0} 个相关用例`)
  } catch (e) {
    ElMessage.error(e.message || '分析失败')
  } finally {
    regressionLoading.value = false
  }
}

function riskLevelType(level) {
  if (level === 'HIGH') return 'error'
  if (level === 'MEDIUM') return 'warning'
  return 'info'
}

function riskScoreColor(score) {
  if (!score) return '#909399'
  if (score >= 0.8) return '#67C23A'
  if (score >= 0.5) return '#E6A23C'
  return '#F56C6C'
}

function priorityType(p) {
  if (p === 'P0') return 'danger'
  if (p === 'P1') return 'warning'
  if (p === 'P2') return 'primary'
  return 'info'
}
</script>

<style scoped>
.ai-tools-view {
  padding: 0;
}

.ai-tabs :deep(.el-tabs__item) {
  font-size: 15px;
}

.tab-content {
  padding: 16px 4px;
}

.result-section {
  margin-top: 20px;
  border-top: 1px solid var(--el-border-color-light);
  padding-top: 16px;
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.selector-code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

.file-list-editor {
  width: 100%;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-item .el-input {
  flex: 1;
}

.yaml-editor :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
