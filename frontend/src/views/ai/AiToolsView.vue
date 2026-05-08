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
                <div v-if="generatedLocatorMeta.validationSummary.total_elements" class="locator-meta-line">
                  <span>验证结果：</span>
                  <el-tag size="small" type="success">
                    元素 {{ generatedLocatorMeta.validationSummary.validated_elements }}/{{ generatedLocatorMeta.validationSummary.total_elements }}
                  </el-tag>
                  <el-tag size="small" type="warning">
                    策略 {{ generatedLocatorMeta.validationSummary.validated_strategies }}
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
                        <el-tag v-if="strategy.validated" size="small" type="success">已验证</el-tag>
                        <el-tag v-else-if="strategy.validation_error" size="small" type="danger">未命中</el-tag>
                        <el-tag v-if="strategy.match_count" size="small" type="info">命中 {{ strategy.match_count }}</el-tag>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="key" label="Key" width="220" />
                <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span>{{ row.description || '未提供说明' }}</span>
                  </template>
                </el-table-column>
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
                <el-table-column prop="validated" label="验证" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.validated ? 'success' : 'info'">{{ row.validated ? '通过' : '待确认' }}</el-tag>
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
                v-if="generatedLocatorMeta.parseDiagnostics.message"
                type="info"
                :closable="false"
                show-icon
                class="locator-meta-alert"
                style="margin-bottom: 12px"
              >
                <div class="locator-meta-line">
                  <strong>解析状态：</strong>
                  <el-tag size="small" :type="generatedLocatorMeta.parseDiagnostics.status === 'partial' ? 'warning' : 'danger'">
                    {{ generatedLocatorMeta.parseDiagnostics.status || 'failed' }}
                  </el-tag>
                </div>
                <div class="locator-meta-line">
                  <strong>解析方式：</strong>
                  <code>{{ generatedLocatorMeta.parseDiagnostics.mode || '-' }}</code>
                </div>
                <div class="locator-meta-line">
                  <strong>原因说明：</strong>
                  <span>{{ generatedLocatorMeta.parseDiagnostics.message }}</span>
                </div>
                <div v-if="generatedLocatorMeta.parseDiagnostics.salvagedCount" class="locator-meta-line">
                  <strong>抢救数量：</strong>
                  <span>{{ generatedLocatorMeta.parseDiagnostics.salvagedCount }}</span>
                </div>
              </el-alert>
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
              支持两种方式：① 单条需求描述快速生成用例；② PRD 文档批量生成草稿 → 批量保存 或 逐条 AI 跑通。
            </el-alert>

            <!-- ① 单条需求快速生成 -->
            <div class="result-section">
              <div class="result-title">单条需求 → 快速生成</div>
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

              <div v-if="generatedYaml" style="margin-top: 12px">
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

            <!-- ② PRD 文档 → 批量草稿 -->
            <div class="result-section">
              <div class="result-title">PRD 文档 → 批量生成草稿用例</div>
              <el-form label-width="120px" style="max-width: 760px">
                <el-form-item label="产品名称">
                  <el-input v-model="draftPrdForm.productName" placeholder="可选，用于增强上下文" clearable style="width: 260px" />
                </el-form-item>
                <el-form-item label="需求 Markdown">
                  <el-input
                    v-model="draftPrdForm.content"
                    type="textarea"
                    :rows="6"
                    placeholder="粘贴需求变更单 Markdown 内容，或上传文件"
                  />
                </el-form-item>
                <el-form-item label="PRD 文件">
                  <el-upload
                    :auto-upload="false"
                    :show-file-list="true"
                    :limit="1"
                    accept=".md,.markdown,.txt"
                    :on-change="onDraftPrdFileChange"
                    :on-remove="onDraftPrdFileRemove"
                  >
                    <el-button>选择 Markdown 文件</el-button>
                  </el-upload>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="draftLoading" @click="generateDraftCases">
                    <el-icon><MagicStick /></el-icon>
                    生成草稿用例
                  </el-button>
                </el-form-item>
              </el-form>

              <!-- 草稿列表：支持多选批量保存 + 单选 AI 跑通 -->
              <div v-if="draftCases.length" style="margin-top: 12px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                  <div class="result-title">草稿用例（{{ draftCases.length }} 条）</div>
                  <el-button type="success" :loading="draftBatchSaving" :disabled="!draftSelectedRows.length"
                    @click="batchSaveDrafts">
                    批量保存选中（{{ draftSelectedRows.length }}）
                  </el-button>
                </div>
                <el-table
                  :data="draftCases"
                  stripe
                  size="small"
                  @selection-change="onDraftSelectionChange"
                  @current-change="onSelectDraft"
                  highlight-current-row
                >
                  <el-table-column type="selection" width="45" />
                  <el-table-column type="index" width="50" />
                  <el-table-column prop="name" label="草稿名称" min-width="220">
                    <template #default="{ row }">{{ row.title || row.name || '-' }}</template>
                  </el-table-column>
                  <el-table-column prop="module" label="模块" width="120">
                    <template #default="{ row }"><el-tag size="small">{{ row.module || 'default' }}</el-tag></template>
                  </el-table-column>
                  <el-table-column prop="priority" label="优先级" width="90">
                    <template #default="{ row }">
                      <el-tag size="small" :type="priorityType(row.priority)">{{ row.priority || 'P2' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="source_test_point" label="来源测试点" min-width="160" show-overflow-tooltip />
                  <el-table-column label="步骤数" width="80">
                    <template #default="{ row }">{{ row.draft_steps?.length || row.steps?.length || 0 }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="110">
                    <template #default="{ row }">
                      <el-button size="small" type="primary" link @click="onSelectDraft(row)">AI 跑通</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <!-- 选中单条草稿 → AI 跑通 -->
              <div v-if="selectedDraftCase" style="margin-top: 16px">
                <el-alert type="info" :closable="false" show-icon>
                  <template #title>
                    当前草稿：{{ selectedDraftCase.name || selectedDraftCase.title }}
                  </template>
                  <div>{{ selectedDraftCase.description || '无额外描述' }}</div>
                </el-alert>
                <el-table :data="selectedDraftCase.draft_steps || []" stripe size="small" style="margin-top: 12px">
                  <el-table-column prop="step_no" label="Step" width="70" />
                  <el-table-column prop="intent" label="原始意图" min-width="220" />
                  <el-table-column prop="action_hint" label="动作提示" width="120" />
                  <el-table-column prop="target_hint" label="目标提示" min-width="180" />
                </el-table>
                <el-form label-width="120px" style="max-width: 700px; margin-top: 16px">
                  <el-form-item label="起始 URL">
                    <el-input v-model="stabilizeForm.startUrl" placeholder="https://example.com/start" clearable />
                  </el-form-item>
                  <el-form-item label="登录前置用例">
                    <el-select v-model="stabilizeForm.loginCaseId" placeholder="可选，优先复用登录态" clearable style="width: 320px">
                      <el-option v-for="c in loginCases" :key="c.id" :label="c.name" :value="c.id" />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="stabilizeLoading" @click="stabilizeDraftCase">
                      AI 跑通并生成正式用例
                    </el-button>
                  </el-form-item>
                </el-form>
              </div>

              <!-- 跑通结果 -->
              <div v-if="stabilizeResult.verified_yaml" style="margin-top: 16px">
                <el-alert
                  :type="stabilizeResult.status === 'passed' ? 'success' : stabilizeResult.status === 'partial' ? 'warning' : 'error'"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    跑通结果：{{ stabilizeResult.status }}，通过 {{ stabilizeResult.passed_steps }}/{{ stabilizeResult.total_steps }} 步
                  </template>
                  <div v-if="stabilizeResult.auth_cache_used">本次已复用登录态缓存</div>
                </el-alert>
                <div class="result-title" style="margin-top: 12px">AI 实际跑通后的正式用例</div>
                <el-input
                  v-model="stabilizeResult.verified_yaml"
                  type="textarea"
                  :rows="16"
                  style="font-family: monospace; font-size: 13px"
                />
                <div style="margin-top: 12px">
                  <el-button type="success" @click="acceptStabilizedCase">接收并保存正式用例</el-button>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        
        <el-tab-pane label="探索执行" name="explore">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              输入自然语言步骤，AI 实时分析页面并执行
            </el-alert>
            <el-form label-width="120px" style="max-width: 900px">
              <el-form-item label="起始 URL">
                <el-input v-model="exploreForm.url" placeholder="http://..." clearable style="width: 400px" />
              </el-form-item>
              <el-form-item label="用例名称">
                <el-input v-model="exploreForm.caseName" placeholder="探索用例名称" clearable style="width: 220px" />
              </el-form-item>
              <el-form-item label="模块 / 优先级">
                <el-input v-model="exploreForm.module" placeholder="模块" clearable style="width: 120px" /> /
                <el-select v-model="exploreForm.priority" style="width: 100px">
                  <el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" />
                </el-select>
              </el-form-item>
              <el-form-item label="自然语言步骤">
                <el-input v-model="exploreForm.stepsText" type="textarea" :rows="6"
                  placeholder="每行一个步骤，例如：&#10;点击账号登录Tab&#10;输入用户名 15251462424&#10;输入密码 Zxs6412915@+&#10;勾选同意条款&#10;点击立即登录按钮"
                  style="font-size: 13px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="exploreLoading" @click="doExplore">
                  {{ exploreLoading ? '探索中...' : '开始探索执行' }}
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="exploreTaskId" style="margin-top: 20px">
              <el-alert :type="exploreResult.status === 'completed' ? 'success' : exploreResult.status === 'failed' ? 'error' : 'info'" :closable="false" show-icon>
                <template #title>
                  {{ exploreResult.status === 'completed' ? '探索完成' : exploreResult.status === 'failed' ? '探索失败' : `探索中... (${exploreElapsed}s)` }}
                  <span v-if="exploreResult.total_steps"> — {{ exploreResult.passed_steps }}/{{ exploreResult.total_steps }} 步骤通过</span>
                </template>
              </el-alert>
              <el-table :data="exploreResult.steps || []" stripe size="small" style="margin-top: 12px" max-height="300">
                <el-table-column prop="step_no" label="Step" width="60" />
                <el-table-column prop="action" label="Action" width="90" />
                <el-table-column prop="target" label="Target" min-width="220">
                  <template #default="{ row }"><code style="font-size:12px">{{ row.target }}</code></template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="70">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.status === 'passed' ? 'success' : 'danger'">{{ row.status === 'passed' ? '✅' : '❌' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="duration_ms" label="耗时" width="80">
                  <template #default="{ row }">{{ row.duration_ms }}ms</template>
                </el-table-column>
              </el-table>
              <div v-if="exploreResult.yaml_case" style="margin-top: 16px">
                <el-button type="primary" @click="exploreYamlVisible = true">查看 YAML</el-button>
                <el-button type="success" @click="saveExploreCase">保存用例和定位器</el-button>
              </div>
              <div v-if="exploreResult.discovered_locators && exploreResult.discovered_locators.length" class="result-section">
                <div class="result-title">探索发现的定位器（{{ exploreResult.discovered_locators.length }} 个）</div>
                <el-table :data="exploreResult.discovered_locators" stripe size="small" max-height="240">
                  <el-table-column prop="full_key" label="Key" min-width="220" />
                  <el-table-column prop="selector_type" label="类型" width="90" />
                  <el-table-column prop="selector" label="Selector" min-width="260">
                    <template #default="{ row }"><code class="selector-code">{{ row.selector }}</code></template>
                  </el-table-column>
                  <el-table-column prop="description" label="说明" min-width="160" />
                </el-table>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 修复审计 -->
        <el-tab-pane name="repair-audit">
          <template #label>
            修复审计
            <el-badge v-if="repairPendingCount > 0" :value="repairPendingCount" class="audit-badge" />
          </template>
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              AI 自动修复的定位器策略待人工复审，接受后正式生效，拒绝则回滚。
            </el-alert>
            <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
              <el-select v-model="repairFilter.status" style="width:120px" @change="loadRepairRecords">
                <el-option label="待审核" value="pending" />
                <el-option label="已接受" value="accepted" />
                <el-option label="已拒绝" value="rejected" />
                <el-option label="全部" value="" />
              </el-select>
              <el-button @click="loadRepairRecords">刷新</el-button>
            </div>
            <el-table :data="repairRecords" v-loading="repairLoading" stripe size="small">
              <el-table-column prop="locator_key" label="Locator Key" width="200" />
              <el-table-column prop="triggered_by" label="触发方式" width="100">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.triggered_by }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="verdict" label="验证结果" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.verdict === 'verified' ? 'success' : row.verdict === 'ambiguous' ? 'warning' : 'danger'">
                    {{ row.verdict }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="新策略" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <code style="font-size:11px">{{ formatNewStrategy(row.new_strategy) }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="review_status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small"
                    :type="row.review_status === 'accepted' ? 'success' : row.review_status === 'rejected' ? 'danger' : 'warning'">
                    {{ { pending: '待审', accepted: '已接受', rejected: '已拒绝' }[row.review_status] || row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="时间" width="160">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <template v-if="row.review_status === 'pending'">
                    <el-button size="small" type="success" link @click="acceptRepair(row.id)">接受</el-button>
                    <el-button size="small" type="danger" link @click="rejectRepair(row.id)">拒绝</el-button>
                  </template>
                  <span v-else style="color:#999;font-size:12px">已审核</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 用例自检 -->
        <el-tab-pane label="用例自检" name="self-check">
          <div class="tab-content">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
              选择用例，AI 将对用例步骤进行语义检查并提出改进建议。
            </el-alert>
            <el-form label-width="120px" style="max-width: 700px">
              <el-form-item label="选择用例">
                <el-select
                  v-model="selfCheckCaseId"
                  filterable
                  clearable
                  placeholder="选择要自检的用例"
                  style="width: 360px"
                >
                  <el-option
                    v-for="c in selfCheckCases"
                    :key="c.id"
                    :label="`[${c.case_id}] ${c.name}`"
                    :value="c.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="selfCheckLoading" :disabled="!selfCheckCaseId" @click="triggerSelfCheck">
                  <el-icon><MagicStick /></el-icon>
                  触发 AI 自检
                </el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="selfCheckResult.status"
              :type="selfCheckResult.status === 'queued' ? 'info' : 'success'"
              :closable="false"
              show-icon
              style="margin-top:12px;max-width:700px"
            >
              <template #title>{{ selfCheckResult.message || `任务状态：${selfCheckResult.status}` }}</template>
            </el-alert>
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

    <el-dialog v-model="exploreYamlVisible" title="探索生成的 YAML 用例" width="760px">
      <el-input v-model="exploreResult.yaml_case" type="textarea" :rows="20" readonly style="font-family: monospace; font-size: 13px" />
      <template #footer>
        <el-button @click="exploreYamlVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveExploreCase">保存到用例库</el-button>
        <el-button @click="() => { navigator.clipboard.writeText(exploreResult.yaml_case); ElMessage.success('已复制') }">复制 YAML</el-button>
      </template>
    </el-dialog>

</template>

<script setup>

// 探索执行
const exploreForm = ref({ url: '', caseName: '', module: 'explore', priority: 'P1', stepsText: '' })
const exploreLoading = ref(false)
const exploreTaskId = ref('')
const exploreResult = ref({ status: '', total_steps: 0, passed_steps: 0, steps: [], yaml_case: '', discovered_locators: [] })
const exploreYamlVisible = ref(false)
const exploreElapsed = ref(0)
const exploreTimer = ref(null)


import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument, Delete, Download, MagicStick, Plus } from '@element-plus/icons-vue'

import { aiApi, casesApi, locatorsApi, locatorRepairApi } from '../../api'
import { useProjectsStore } from '../../stores/projects'

const route = useRoute()

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
  validationSummary: {},
  parseDiagnostics: {},
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
const draftLoading = ref(false)
const draftPrdUploadFile = ref(null)
const draftPrdForm = ref({
  productName: '',
  content: '',
})
const draftCases = ref([])
const selectedDraftIndex = ref(-1)
const draftSelectedRows = ref([])
const draftBatchSaving = ref(false)
const stabilizeForm = ref({
  startUrl: '',
  headless: true,
  loginCaseId: null,
})
const stabilizeLoading = ref(false)
const stabilizeTaskId = ref('')
const stabilizeResult = ref({
  status: '',
  draft_case: null,
  total_steps: 0,
  passed_steps: 0,
  failed_steps: 0,
  steps: [],
  verified_yaml: '',
  discovered_locators: [],
  auth_cache_used: false,
})

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
      description: loc.description || '',
      type: primary?.type || loc.primary_type || loc.type || 'css',
      value: displayValue(primary?.value ?? loc.value ?? loc.selector ?? ''),
      confidence: primary?.confidence || loc.ai_confidence || loc.confidence || 'N/A',
      strategyCount: strategies.length,
      validated: !!(primary?.validated ?? loc.validated),
      strategies,
    }
  })
})

const selectedDraftCase = computed(() => {
  if (selectedDraftIndex.value < 0) return null
  return draftCases.value[selectedDraftIndex.value] || null
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
  generatedLocatorMeta.value = { pageUrl: '', loginUsed: false, authCacheUsed: false, validationSummary: {}, parseDiagnostics: {} }
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
      validationSummary: result.validation_summary || {},
      parseDiagnostics: {
        status: result.parse_diagnostics?.status || '',
        mode: result.parse_diagnostics?.mode || '',
        message: result.parse_diagnostics?.message || '',
        salvagedCount: result.parse_diagnostics?.salvaged_count || 0,
      },
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

function onDraftPrdFileChange(uploadFile) {
  draftPrdUploadFile.value = uploadFile?.raw || null
}

function onDraftPrdFileRemove() {
  draftPrdUploadFile.value = null
}

async function generateDraftCases() {
  if (!draftPrdForm.value.content.trim() && !draftPrdUploadFile.value) {
    ElMessage.warning('请先输入需求 Markdown 或上传 PRD 文件')
    return
  }
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  draftLoading.value = true
  draftCases.value = []
  draftSelectedRows.value = []
  selectedDraftIndex.value = -1
  stabilizeResult.value = {
    status: '',
    draft_case: null,
    total_steps: 0,
    passed_steps: 0,
    failed_steps: 0,
    steps: [],
    verified_yaml: '',
    discovered_locators: [],
    auth_cache_used: false,
  }
  try {
    let result
    if (draftPrdUploadFile.value) {
      const formData = new FormData()
      formData.append('project_id', currentProjectId.value)
      formData.append('product_name', draftPrdForm.value.productName || '')
      formData.append('prd_file', draftPrdUploadFile.value)
      result = await aiApi.generateDraftsFromPrdFile(formData)
    } else {
      result = await aiApi.generateDraftsFromPrd({
        project_id: currentProjectId.value,
        prd_text: draftPrdForm.value.content,
        product_name: draftPrdForm.value.productName || '',
      })
    }
    draftCases.value = result.case_drafts || result.drafts || []
    if (draftCases.value.length) {
      selectedDraftIndex.value = 0
    }
    ElMessage.success(`已生成 ${draftCases.value.length} 条草稿用例`)
  } catch (error) {
    ElMessage.error(error.message || '草稿用例生成失败')
  } finally {
    draftLoading.value = false
  }
}

function onDraftSelectionChange(rows) {
  draftSelectedRows.value = rows
}

function onSelectDraft(row) {
  if (!row) return
  selectedDraftIndex.value = draftCases.value.findIndex(
    (item) => (item.draft_id && item.draft_id === row.draft_id) || item === row
  )
}

async function batchSaveDrafts() {
  if (!draftSelectedRows.value.length) return
  if (!currentProjectId.value) { ElMessage.warning('请先选择项目'); return }
  draftBatchSaving.value = true
  try {
    const drafts = draftSelectedRows.value.map((d) => ({
      name: d.title || d.name,
      case_id: d.case_id || `DRAFT_${Date.now()}_${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
      module: d.module || 'default',
      priority: d.priority || 'P2',
      content: d.content || '',
      automation: d.automation || 0,
    }))
    const result = await casesApi.batchCreate(currentProjectId.value, drafts)
    ElMessage.success(`已保存 ${result.created_count || drafts.length} 条用例`)
    draftCases.value = draftCases.value.filter(
      (d) => !draftSelectedRows.value.includes(d)
    )
    draftSelectedRows.value = []
  } catch (err) {
    ElMessage.error(err.message || '批量保存失败')
  } finally {
    draftBatchSaving.value = false
  }
}

async function stabilizeDraftCase() {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!selectedDraftCase.value) {
    ElMessage.warning('请先选择草稿用例')
    return
  }
  if (!stabilizeForm.value.startUrl) {
    ElMessage.warning('请输入起始 URL')
    return
  }

  stabilizeLoading.value = true
  stabilizeResult.value = {
    status: '',
    draft_case: null,
    total_steps: 0,
    passed_steps: 0,
    failed_steps: 0,
    steps: [],
    verified_yaml: '',
    discovered_locators: [],
    auth_cache_used: false,
  }
  try {
    const draft = selectedDraftCase.value
    const draftPayload = {
      draft_id: draft.draft_id || `draft_${Date.now()}`,
      name: draft.name || draft.title || '',
      module: draft.module || 'default',
      priority: draft.priority || 'P2',
      description: draft.description || '',
      source_type: draft.source_type || 'prd_draft',
      draft_steps: (draft.draft_steps || []).map((s, i) => ({
        step_no: s.step_no || i + 1,
        intent: s.intent || '',
        action_hint: s.action_hint || '',
        target_hint: s.target_hint || '',
        expected_hint: s.expected_hint || '',
      })),
    }
    const response = await aiApi.stabilizeDraft({
      draft_case: draftPayload,
      start_url: stabilizeForm.value.startUrl,
      project_id: currentProjectId.value,
      headless: true,
      login_case_id: stabilizeForm.value.loginCaseId,
    })
    stabilizeTaskId.value = response.task_id
    await pollStabilizeTask(response.task_id)
  } catch (error) {
    ElMessage.error(error.message || '稳定化执行失败')
  } finally {
    stabilizeLoading.value = false
  }
}

async function pollStabilizeTask(taskId) {
  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 5000))
    try {
      const result = await aiApi.getStabilizeTask(taskId)
      stabilizeResult.value = result
      if (['completed', 'passed', 'partial', 'failed'].includes(result.status)) {
        if (result.verified_yaml) {
          ElMessage.success(`已生成正式用例，状态：${result.status}`)
        } else if (result.status === 'failed') {
          ElMessage.error(result.error || '稳定化失败')
        }
        break
      }
    } catch (error) {
      console.error('poll stabilize error', error)
      break
    }
  }
}

async function acceptStabilizedCase() {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!stabilizeTaskId.value) {
    ElMessage.warning('缺少稳定化任务')
    return
  }
  try {
    const result = await aiApi.acceptStabilizedCase({
      task_id: stabilizeTaskId.value,
      project_id: currentProjectId.value,
      author: 'AI',
      save_discovered_locators: true,
    })
    ElMessage.success(`正式用例已保存：${result.case_id}，定位器 ${result.saved_locators} 个`)
  } catch (error) {
    ElMessage.error(error.message || '保存正式用例失败')
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

// 探索执行
async function doExplore() {
  if (!exploreForm.value.url) { ElMessage.warning('请输入起始 URL'); return }
  if (!exploreForm.value.stepsText.trim()) { ElMessage.warning('请输入自然语言步骤'); return }
  const steps = exploreForm.value.stepsText.split('\n').filter(s => s.trim())
  if (steps.length === 0) { ElMessage.warning('请输入至少一个步骤'); return }
  exploreLoading.value = true
  exploreResult.value = { status: '', total_steps: 0, passed_steps: 0, steps: [], yaml_case: '', discovered_locators: [] }
  exploreElapsed.value = 0
  exploreTimer.value = setInterval(() => { exploreElapsed.value++ }, 1000)
  try {
    const r = await aiApi.exploreExecute({ url: exploreForm.value.url, case_name: exploreForm.value.caseName || '探索用例', module: exploreForm.value.module || 'explore', priority: exploreForm.value.priority || 'P1', steps, headless: true })
    exploreTaskId.value = r.task_id
    await pollExploreResult(r.task_id)
  } catch (err) {
    ElMessage.error(err.message || err.detail || '探索执行失败')
  } finally {
    exploreLoading.value = false
    if (exploreTimer.value) clearInterval(exploreTimer.value)
  }
}

async function pollExploreResult(taskId) {
  while (true) {
    await new Promise(r => setTimeout(r, 5000))
    try {
      const r = await aiApi.exploreGetTask(taskId)
      exploreResult.value = r
      // terminal statuses: completed, failed, partial (partial = some steps passed)
      if (['completed', 'failed', 'partial', 'passed'].includes(r.status)) {
        if (r.status === 'completed') ElMessage.success(`探索完成：${r.passed_steps}/${r.total_steps} 步骤通过`)
        else if (r.status === 'failed') ElMessage.error(`探索失败：${r.error || '未知错误'}`)
        else if (r.status === 'partial') ElMessage.warning(`探索完成（部分失败）：${r.passed_steps}/${r.total_steps} 步骤通过`)
        else ElMessage.success(`探索完成：${r.passed_steps}/${r.total_steps} 步骤通过`)
        break
      }
    } catch (err) { console.error('poll error:', err); break }
  }
}

async function saveExploreCase() {
  if (!exploreResult.value.yaml_case) return
  if (!currentProjectId.value) { ElMessage.warning('请先选择项目'); return }
  try {
    const r = await aiApi.exploreSave({
      yaml_case: exploreResult.value.yaml_case,
      project_id: currentProjectId.value,
      case_name: exploreForm.value.caseName || '探索用例',
      discovered_locators: exploreResult.value.discovered_locators || [],
      save_discovered_locators: true,
    })
    ElMessage.success(`用例已保存：${r.case_id}${r.saved_locators ? `，同步保存 ${r.saved_locators} 个定位器` : ''}`)
  } catch (err) { ElMessage.error(err.detail || '保存失败') }
}

// ─── Route query → tab switching ─────────────────────────────
watch(() => route.query.tab, (tab) => {
  if (tab) activeTab.value = tab
}, { immediate: true })

watch(() => route.query.case_id, (caseId) => {
  if (caseId && route.query.tab === 'self-check') selfCheckCaseId.value = parseInt(caseId)
}, { immediate: true })

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}


// ─── 修复审计 ──────────────────────────────────────────────────
const repairRecords = ref([])
const repairLoading = ref(false)
const repairPendingCount = ref(0)
const repairFilter = ref({ status: 'pending' })

async function loadRepairRecords() {
  if (!currentProjectId.value) return
  repairLoading.value = true
  try {
    const params = { project_id: currentProjectId.value }
    if (repairFilter.value.status) params.status = repairFilter.value.status
    repairRecords.value = await locatorRepairApi.list(params)
  } catch (err) {
    console.warn('load repair records failed', err)
  } finally {
    repairLoading.value = false
  }
}

async function loadRepairPendingCount() {
  if (!currentProjectId.value) return
  try {
    const r = await locatorRepairApi.pendingCount(currentProjectId.value)
    repairPendingCount.value = r?.data?.count ?? r?.count ?? 0
  } catch {}
}

async function acceptRepair(id) {
  try {
    await locatorRepairApi.accept(id)
    ElMessage.success('已接受，新策略生效')
    await loadRepairRecords()
    await loadRepairPendingCount()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function rejectRepair(id) {
  try {
    await locatorRepairApi.reject(id)
    ElMessage.success('已拒绝，策略已回滚')
    await loadRepairRecords()
    await loadRepairPendingCount()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

function formatNewStrategy(strategy) {
  if (!strategy) return '-'
  if (typeof strategy === 'string') {
    try { strategy = JSON.parse(strategy) } catch { return strategy }
  }
  if (strategy.type && strategy.value) return `${strategy.type}: ${strategy.value}`
  return JSON.stringify(strategy)
}

// ─── 用例自检 ──────────────────────────────────────────────────
const selfCheckCaseId = ref(null)
const selfCheckCases = ref([])
const selfCheckLoading = ref(false)
const selfCheckResult = ref({ status: '', message: '' })

async function loadSelfCheckCases() {
  if (!currentProjectId.value) return
  try {
    selfCheckCases.value = await casesApi.list({ project_id: currentProjectId.value })
  } catch {}
}

async function triggerSelfCheck() {
  if (!selfCheckCaseId.value) return
  selfCheckLoading.value = true
  selfCheckResult.value = { status: '', message: '' }
  try {
    const r = await casesApi.selfCheck(selfCheckCaseId.value)
    selfCheckResult.value = r
    ElMessage.success('AI 自检任务已触发')
  } catch (err) {
    ElMessage.error(err.message || '触发失败')
  } finally {
    selfCheckLoading.value = false
  }
}

// reload tab-specific data on project or tab change
watch([currentProjectId, activeTab], async ([pid, tab]) => {
  if (!pid) return
  if (tab === 'repair-audit') { await loadRepairRecords(); await loadRepairPendingCount() }
  if (tab === 'self-check') await loadSelfCheckCases()
})

</script>

<style scoped>
.ai-tools-view {
  padding: 0;
}

.audit-badge {
  margin-left: 4px;
  vertical-align: middle;
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
