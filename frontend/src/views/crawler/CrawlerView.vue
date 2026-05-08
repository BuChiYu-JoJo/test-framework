<template>
  <div class="crawler-view">
    <PageHeader title="爬虫巡检" :crumbs="['首页', '爬虫巡检']">
      <template #actions>
        <el-button type="primary" @click="showAddDialog"><el-icon><Plus /></el-icon>添加爬虫</el-button>
        <el-button @click="loadData"><el-icon><Refresh /></el-icon>刷新</el-button>
      </template>
    </PageHeader>

    <!-- 统计卡片 -->
    <el-row :gutter="12" class="mt-16" v-if="crawlerStore.stats">
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value">{{ crawlerStore.stats.total }}</div>
          <div class="stat-label">总数</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card active">
          <div class="stat-value" style="color:#67c23a">{{ crawlerStore.stats.passed }}</div>
          <div class="stat-label">通过</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card warning">
          <div class="stat-value" style="color:#e6a23c">{{ crawlerStore.stats.warning }}</div>
          <div class="stat-label">警告</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value" style="color:#f56c6c">{{ crawlerStore.stats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value">{{ crawlerStore.stats.avg_success_rate }}%</div>
          <div class="stat-label">平均成功率</div>
        </div>
      </el-col>
    </el-row>

    <!-- 爬虫列表 -->
    <el-card shadow="never" class="mt-16">
      <el-table :data="crawlerStore.configs" v-loading="crawlerStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="爬虫名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="entry_url" label="入口URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link v-if="row.entry_url" :href="row.entry_url" target="_blank" type="primary" style="font-size:12px">
              {{ row.entry_url }}
            </el-link>
            <span v-else style="color:#999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="interval" label="巡检间隔" width="100">
          <template #default="{ row }">{{ row.interval }}s</template>
        </el-table-column>
        <el-table-column prop="expected_count" label="预期量" width="80" />
        <el-table-column prop="last_status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.last_status === 'passed'" size="small" type="success">通过</el-tag>
            <el-tag v-else-if="row.last_status === 'warning'" size="small" type="warning">警告</el-tag>
            <el-tag v-else-if="row.last_status === 'failed'" size="small" type="danger">失败</el-tag>
            <el-tag v-else size="small" type="info">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="最后巡检" width="150">
          <template #default="{ row }">{{ formatTime(row.last_run_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewInspections(row)">巡检记录</el-button>
            <el-button size="small" type="warning" link @click="handleRun(row.id)">立即巡检</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加爬虫配置" width="600px">
      <el-form :model="addForm" label-width="90px" ref="addFormRef">
        <el-form-item label="名称" prop="name" :rules="[{ required: true }]">
          <el-input v-model="addForm.name" placeholder="爬虫名称" />
        </el-form-item>
        <el-form-item label="入口URL" prop="entry_url">
          <el-input v-model="addForm.entry_url" placeholder="https://example.com/crawl" />
        </el-form-item>
        <el-form-item label="脚本路径">
          <el-input v-model="addForm.script_path" placeholder="/path/to/crawler.py（本地脚本，可选）" />
        </el-form-item>
        <el-form-item label="巡检间隔">
          <el-input-number v-model="addForm.interval" :min="300" :step="3600" /> 秒
        </el-form-item>
        <el-form-item label="预期抓取量">
          <el-input-number v-model="addForm.expected_count" :min="1" />
        </el-form-item>
        <el-form-item label="新鲜度阈值">
          <el-input-number v-model="addForm.freshness_threshold" :min="3600" :step="86400" /> 秒（默认24h）
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="addForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="adding">添加</el-button>
      </template>
    </el-dialog>

    <!-- 巡检记录抽屉 -->
    <el-drawer v-model="inspDrawer" title="巡检记录" size="700px" direction="rtl">
      <el-table :data="crawlerStore.inspections" stripe size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'passed'" size="small" type="success">通过</el-tag>
            <el-tag v-else-if="row.status === 'warning'" size="small" type="warning">警告</el-tag>
            <el-tag v-else-if="row.status === 'failed'" size="small" type="danger">失败</el-tag>
            <el-tag v-else size="small" type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="items_count" label="抓取量" width="80" />
        <el-table-column prop="error_count" label="错误数" width="70" />
        <el-table-column prop="completeness" label="完整率" width="80">
          <template #default="{ row }">{{ row.completeness || 0 }}%</template>
        </el-table-column>
        <el-table-column prop="anti_crawl_detected" label="反爬" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.anti_crawl_detected" size="small" type="danger">是</el-tag>
            <span v-else style="color:#999">否</span>
          </template>
        </el-table-column>
        <el-table-column prop="checked_at" label="时间" width="150">
          <template #default="{ row }">{{ formatTime(row.checked_at) }}</template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCrawlerStore } from '../../stores/crawler'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'

const crawlerStore = useCrawlerStore()
const addDialogVisible = ref(false)
const inspDrawer = ref(false)
const adding = ref(false)
const addFormRef = ref(null)

const addForm = ref({
  name: '', entry_url: '', script_path: '',
  interval: 3600, expected_count: 100, freshness_threshold: 86400, enabled: true
})

onMounted(() => loadData())

async function loadData() {
  await Promise.all([crawlerStore.fetchConfigs(), crawlerStore.fetchStats()])
}

function showAddDialog() {
  addForm.value = { name: '', entry_url: '', script_path: '', interval: 3600, expected_count: 100, freshness_threshold: 86400, enabled: true }
  addDialogVisible.value = true
}

async function handleAdd() {
  try { await addFormRef.value.validate() } catch { return }
  adding.value = true
  try {
    await crawlerStore.createConfig(addForm.value)
    addDialogVisible.value = false
    ElMessage.success('添加成功')
  } finally { adding.value = false }
}

async function handleRun(id) {
  await crawlerStore.runNow(id)
  ElMessage.success('巡检已触发')
}

async function handleDelete(id) {
  await crawlerStore.deleteConfig(id)
  ElMessage.success('已删除')
}

async function viewInspections(crawler) {
  inspDrawer.value = true
  await crawlerStore.fetchInspections(crawler.id)
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
.stat-card { background: #f5f7fa; border-radius: 8px; padding: 16px; text-align: center; }
.stat-value { font-size: 24px; font-weight: bold; color: #333; }
.stat-label { font-size: 12px; color: #666; margin-top: 4px; }
</style>