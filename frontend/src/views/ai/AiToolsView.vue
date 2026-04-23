<template>
  <div class="ai-tools-view">
    <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
      <el-select v-model="currentProjectId" placeholder="选择项目" style="width: 160px" @change="onProjectChange">
        <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
    </div>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" class="ai-tabs">
        <el-tab-pane label="AI 生成 Locators" name="locators">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              输入页面 URL，AI 将分析页面元素并生成最优的定位符，支持多策略结果编辑后再保存。
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

            <div v-if="generatedLocators && Object.keys(generatedLocators).length" class="result-section">
              <div class="result-title">生成的 Locators（{{ Object.keys(generatedLocators).length }} 个）</div>
              <el-alert
                v-if="generatedLocatorMeta.pageUrl || generatedLocatorMeta.loginUsed"
                type="success"
                :closable="false"
                show-icon
                class="locator-meta-alert"
              >
                <template #title>
                  <strong>执行信息</strong>
                </template>
                <div class="locator-meta-line">
                  <span>最终页面：</span>
                  <code>{{ generatedLocatorMeta.pageUrl || locatorForm.url }}</code>
                </div>
                <div class="locator-meta-line">
                  <span>登录用例：</span>
                  <el-tag size="small" :type="generatedLocatorMeta.loginUsed ? 'warning' : 'info'">
                    {{ generatedLocatorMeta.loginUsed ? '已使用' : '未使用' }}
                  </el-tag>
                </div>
                <div v-if="generatedLocatorMeta.loginUsed" class="locator-meta-line">
                  <span>登录态缓存：</span>
                  <el-tag size="small" :type="generatedLocatorMeta.authCacheUsed ? 'success' : 'warning'">
                    {{ generatedLocatorMeta.authCacheUsed ? '命中缓存' : '未命中缓存' }}
                  </el-tag>
                </div>
              </el-alert>
              <el-table :data="locatorTableData" stripe size="small" max-height="420">
                <el-table-column type="expand">
                  <template #default="{ row }">
                    <div class="strategy-preview">
                      <div
                        v-for="strategy in row.strategies"
                        :key="`${row.key}_${strategy.type}_${strategy.priority}_${displayValue(strategy.value)}`"
                        class="strategy-preview-item"
                      >
                        <el-tag size="small" :type="strategy.enabled === false ? 'info' : 'warning'">
                          {{ strategy.type }}
                        </el-tag>
                        <span class="strategy-priority">P{{ strategy.priority }}</span>
                        <code class="selector-code">{{ displayValue(strategy.value) }}</code>
                        <el-tag
                          v-if="strategy.confidence !== null && strategy.confidence !== undefined && strategy.confidence !== ''"
                          size="small"
                          type="success"
                        >
                          {{ strategy.confidence }}
                        </el-tag>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="key" label="Key" width="220" />
                <el-table-column prop="type" label="主策略" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.type === 'css' ? 'success' : 'warning'">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="strategyCount" label="策略数" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" type="info">{{ row.strategyCount }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="主值" min-width="280">
                  <template #default="{ row }">
                    <code class="selector-code">{{ row.value }}</code>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="confidenceType(row.confidence)">{{ row.confidence }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="140">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" link @click="editGeneratedLocator(row.key)">编辑</el-button>
                    <el-button size="small" type="danger" link @click="removeGeneratedLocator(row.key)">移除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else-if="generatedRawResponse" class="result-section">
              <el-alert
                type="warning"
                :closable="false"
                show-icon
                title="AI 已返回原始结果，但结构化 locators 解析失败"
                style="margin-bottom: 12px"
              />
              <div class="result-title">原始 AI 返回</div>
              <el-input v-model="generatedRawResponse" type="textarea" :rows="12" readonly />
            </div>
          </div>
        </el-tab-pane>

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

    <el-dialog v-model="locatorEditorVisible" title="编辑 AI 生成定位器" width="860px">
      <el-form v-if="locatorEditor" :model="locatorEditor" label-width="90px">
        <el-form-item label="Locator Key">
          <span>{{ locatorEditor.key }}</span>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="locatorEditor.description" placeholder="元素用途说明" />
        </el-form-item>
        <el-form-item label="主策略类型">
          <el-select v-model="locatorEditor.primary_type" style="width: 100%">
            <el-option v-for="type in locatorTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="locatorEditor" class="strategy-editor">
        <div class="strategy-editor-header">
          <div class="result-title">策略列表</div>
          <el-button type="primary" plain size="small" @click="addGeneratedStrategy">
            <el-icon><Plus /></el-icon>
            添加策略
          </el-button>
        </div>
        <div class="strategy-editor-list">
          <div
            v-for="(strategy, index) in locatorEditor.strategies"
            :key="strategy.local_id"
            class="strategy-editor-card"
            :class="{ primary: strategy.type === locatorEditor.primary_type }"
          >
            <div class="strategy-editor-toolbar">
              <div class="strategy-editor-badges">
                <el-tag size="small" type="info">第 {{ index + 1 }} 条</el-tag>
                <el-tag v-if="strategy.type === locatorEditor.primary_type" size="small" type="danger">主策略</el-tag>
              </div>
              <el-button
                size="small"
                type="danger"
                link
                :disabled="locatorEditor.strategies.length === 1"
                @click="removeGeneratedStrategy(index)"
              >
                删除
              </el-button>
            </div>
            <div class="strategy-editor-grid">
              <el-form-item label="类型" label-width="70px">
                <el-select v-model="strategy.type" style="width: 100%">
                  <el-option v-for="type in locatorTypes" :key="type" :label="type" :value="type" />
                </el-select>
              </el-form-item>
              <el-form-item label="优先级" label-width="70px">
                <el-input-number v-model="strategy.priority" :min="1" :max="20" style="width: 100%" />
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
                :placeholder="strategyPlaceholder(strategy.type)"
              />
            </el-form-item>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="locatorEditorVisible = false">取消</el-button>
        <el-button type="primary" @click="applyGeneratedLocatorEdit">应用修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Delete, Download, MagicStick, Plus } from '@element-plus/icons-vue'

import { aiApi, casesApi, locatorsApi } from '../../api'
import { useProjectsStore } from '../../stores/projects'

const projectsStore = useProjectsStore()

const activeTab = ref('locators')
const currentProjectId = ref(null)
const locatorTypes = ['css', 'xpath', 'text', 'label', 'placeholder', 'testid', 'role']

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
const generatedRawResponse = ref('')
const generatedLocatorMeta = ref({
  pageUrl: '',
  loginUsed: false,
  authCacheUsed: false,
})
const locatorEditorVisible = ref(false)
const locatorEditor = ref(null)

const caseForm = ref({
  description: '',
  module: 'default',
  priority: 'P2',
})
const caseLoading = ref(false)
const generatedYaml = ref('')
const generatedCaseId = ref('')

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

function displayValue(value) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function createEditableStrategy(strategy = {}, index = 0) {
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

function normalizeLocatorStrategies(loc) {
  if (Array.isArray(loc?.strategies) && loc.strategies.length) {
    return loc.strategies
      .slice()
      .sort((a, b) => (a.priority || 999) - (b.priority || 999))
      .map((strategy, index) => createEditableStrategy(strategy, index))
  }
  return [
    createEditableStrategy({
      type: loc?.primary_type || loc?.type || 'css',
      value: loc?.value ?? loc?.selector ?? '',
      priority: loc?.priority || 1,
      confidence: loc?.ai_confidence ?? loc?.confidence ?? '',
      enabled: true,
    }, 0),
  ]
}

function parseStrategyValue(type, valueText) {
  const raw = (valueText || '').trim()
  if (!raw) return ''
  if (type === 'role') {
    try {
      return JSON.parse(raw)
    } catch {
      return raw
    }
  }
  return raw
}

function strategyPlaceholder(type) {
  if (type === 'role') return '{"role":"button","name":"立即登录"}'
  if (type === 'xpath') return "//button[contains(., '立即登录')]"
  if (type === 'label') return '我已阅读并同意'
  return "如：button:has-text('立即登录')"
}

const locatorTableData = computed(() => {
  if (!generatedLocators.value) return []
  return Object.entries(generatedLocators.value).map(([key, loc]) => {
    const strategies = Array.isArray(loc.strategies) && loc.strategies.length
      ? loc.strategies
      : [{
          type: loc.primary_type || loc.type || 'css',
          value: loc.value ?? loc.selector ?? '',
          priority: loc.priority || 1,
          confidence: loc.ai_confidence || loc.confidence || null,
          enabled: true,
        }]
    const primary = strategies
      .slice()
      .sort((a, b) => (a.priority || 999) - (b.priority || 999))
      .find((strategy) => strategy.enabled !== false) || strategies[0]
    return {
      key,
      type: primary?.type || loc.primary_type || loc.type || 'css',
      value: displayValue(primary?.value ?? loc.value ?? loc.selector ?? ''),
      confidence: primary?.confidence || loc.ai_confidence || loc.confidence || 'N/A',
      strategyCount: strategies.length,
      strategies,
    }
  })
})

const onProjectChange = async () => {
  loginCases.value = []
  if (!currentProjectId.value) return
  try {
    loginCases.value = await aiApi.listLoginCases(currentProjectId.value)
  } catch (error) {
    console.warn('加载登录用例失败', error)
  }
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  if (projectsStore.projects.length && !currentProjectId.value) {
    currentProjectId.value = projectsStore.projects[0].id
    await onProjectChange()
  }
})

async function generateLocators() {
  if (!locatorForm.value.url) {
    ElMessage.warning('请输入页面 URL')
    return
  }
  locatorLoading.value = true
  generatedLocators.value = null
  generatedRawResponse.value = ''
  generatedLocatorMeta.value = { pageUrl: '', loginUsed: false, authCacheUsed: false }
  try {
    let result
    if (locatorForm.value.loginCaseId) {
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
      result = await aiApi.generateLocators({
        url: locatorForm.value.url,
        page_name: locatorForm.value.pageName,
        intent: locatorForm.value.intent,
        viewport_width: locatorForm.value.width,
        viewport_height: locatorForm.value.height,
      })
    }
    generatedLocators.value = result.locators || {}
    generatedRawResponse.value = result.raw_ai_response || ''
    generatedLocatorMeta.value = {
      pageUrl: result.page_url || '',
      loginUsed: !!result.login_used,
      authCacheUsed: !!result.auth_cache_used,
    }
    if (Object.keys(generatedLocators.value).length) {
      ElMessage.success(`生成了 ${Object.keys(generatedLocators.value).length} 个 locators`)
    } else if (generatedRawResponse.value) {
      ElMessage.warning('AI 已返回原始内容，但结构化解析失败，已在下方展示原始结果')
    } else {
      ElMessage.warning('AI 未生成可用的 locator 结果')
    }
  } catch (error) {
    ElMessage.error(error.message || error.detail || '生成失败')
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
      const strategies = Array.isArray(loc.strategies) && loc.strategies.length
        ? loc.strategies.map((strategy, index) => ({
            type: strategy.type || 'css',
            value: strategy.value ?? '',
            priority: strategy.priority || index + 1,
            confidence: strategy.confidence ?? null,
            enabled: strategy.enabled !== false,
          }))
        : []
      const primary = strategies
        .slice()
        .sort((a, b) => (a.priority || 999) - (b.priority || 999))
        .find((strategy) => strategy.enabled !== false) || strategies[0]
      await locatorsApi.create({
        project_id: currentProjectId.value,
        page_name: pageName,
        element_key: key,
        selector: typeof (primary?.value ?? loc.value ?? loc.selector ?? '') === 'string'
          ? (primary?.value ?? loc.value ?? loc.selector ?? '')
          : JSON.stringify(primary?.value ?? ''),
        selector_type: primary?.type || loc.primary_type || loc.type || 'css',
        priority: primary?.priority || loc.priority || 1,
        description: loc.description || '',
        primary_type: loc.primary_type || primary?.type || loc.type || 'css',
        strategies,
      })
      saved++
    }
    ElMessage.success(`已保存 ${saved} 个定位符到项目，完整 strategies 也已落库`)
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

function editGeneratedLocator(key) {
  const current = generatedLocators.value?.[key]
  if (!current) return
  locatorEditor.value = {
    key,
    description: current.description || '',
    primary_type: current.primary_type || current.type || 'css',
    strategies: normalizeLocatorStrategies(current),
  }
  locatorEditorVisible.value = true
}

function addGeneratedStrategy() {
  if (!locatorEditor.value) return
  locatorEditor.value.strategies.push(
    createEditableStrategy(
      {
        type: locatorEditor.value.primary_type || 'css',
        value: '',
        priority: locatorEditor.value.strategies.length + 1,
        enabled: true,
      },
      locatorEditor.value.strategies.length,
    ),
  )
}

function removeGeneratedStrategy(index) {
  if (!locatorEditor.value) return
  if (locatorEditor.value.strategies.length === 1) {
    ElMessage.warning('至少保留一条策略')
    return
  }
  locatorEditor.value.strategies.splice(index, 1)
}

function applyGeneratedLocatorEdit() {
  if (!locatorEditor.value || !generatedLocators.value) return
  const strategies = locatorEditor.value.strategies
    .map((strategy, index) => ({
      type: strategy.type || 'css',
      value: parseStrategyValue(strategy.type, strategy.value_text),
      priority: strategy.priority || index + 1,
      confidence: strategy.confidence === '' ? null : strategy.confidence,
      enabled: strategy.enabled !== false,
    }))
    .filter((strategy) => {
      const value = strategy.value
      return typeof value === 'string' ? value.trim() : value
    })
    .sort((a, b) => (a.priority || 999) - (b.priority || 999))

  if (!strategies.length) {
    ElMessage.warning('请至少保留一条有效策略')
    return
  }

  const primary = strategies.find((strategy) => strategy.enabled !== false) || strategies[0]
  generatedLocators.value[locatorEditor.value.key] = {
    ...generatedLocators.value[locatorEditor.value.key],
    description: locatorEditor.value.description || '',
    primary_type: locatorEditor.value.primary_type || primary.type || 'css',
    strategies,
    type: primary.type || 'css',
    value: primary.value ?? '',
    ai_confidence: primary.confidence ?? '',
  }
  generatedLocators.value = { ...generatedLocators.value }
  locatorEditorVisible.value = false
  ElMessage.success('已更新该 locator 的策略')
}

function removeGeneratedLocator(key) {
  if (!generatedLocators.value?.[key]) return
  delete generatedLocators.value[key]
  generatedLocators.value = { ...generatedLocators.value }
  if (locatorEditor.value?.key === key) {
    locatorEditorVisible.value = false
    locatorEditor.value = null
  }
  ElMessage.success(`已移除 ${key}`)
}

function confidenceType(conf) {
  const value = parseFloat(conf)
  if (isNaN(value)) return 'info'
  if (value >= 0.9) return 'success'
  if (value >= 0.7) return 'warning'
  return 'danger'
}

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
  } catch (error) {
    ElMessage.error(error.message || '生成失败')
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
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

function copyYaml() {
  navigator.clipboard.writeText(generatedYaml.value).then(() => {
    ElMessage.success('YAML 已复制到剪贴板')
  })
}

function addFile() {
  regressionForm.value.changedFiles.push('')
}

function removeFile(index) {
  regressionForm.value.changedFiles.splice(index, 1)
}

async function selectRegression() {
  const files = regressionForm.value.changedFiles.filter((file) => file.trim())
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
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
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

function priorityType(priority) {
  if (priority === 'P0') return 'danger'
  if (priority === 'P1') return 'warning'
  if (priority === 'P2') return 'primary'
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

.locator-meta-alert {
  margin-bottom: 12px;
}

.locator-meta-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
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

.strategy-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
}

.strategy-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.strategy-priority {
  font-size: 12px;
  color: #909399;
}

.strategy-editor {
  border-top: 1px solid var(--el-border-color-light);
  padding-top: 16px;
}

.strategy-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.strategy-editor-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-editor-card {
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 14px;
  background: #fff;
}

.strategy-editor-card.primary {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.strategy-editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.strategy-editor-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.strategy-value-item {
  margin-top: 4px;
  margin-bottom: 0;
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

@media (max-width: 960px) {
  .strategy-editor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
