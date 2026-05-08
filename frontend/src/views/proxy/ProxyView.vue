<template>
  <div class="proxy-view">
    <PageHeader title="代理管理" :crumbs="['首页', '代理管理']">
      <template #actions>
        <el-button type="primary" @click="showAddDialog"><el-icon><Plus /></el-icon>添加代理</el-button>
        <el-button @click="showBatchDialog"><el-icon><Upload /></el-icon>批量导入</el-button>
        <el-button @click="handleRefresh"><el-icon><Refresh /></el-icon>刷新健康</el-button>
        <el-button @click="loadData"><el-icon><Refresh /></el-icon>刷新</el-button>
      </template>
    </PageHeader>

    <!-- 统计卡片 -->
    <el-row :gutter="12" class="mt-16" v-if="proxyStore.stats">
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value">{{ proxyStore.stats.total }}</div>
          <div class="stat-label">总数</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card active">
          <div class="stat-value" style="color:#67c23a">{{ proxyStore.stats.active }}</div>
          <div class="stat-label">可用</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value" style="color:#909399">{{ proxyStore.stats.unknown }}</div>
          <div class="stat-label">未知</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value" style="color:#f56c6c">{{ proxyStore.stats.inactive }}</div>
          <div class="stat-label">不可用</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value">{{ proxyStore.stats.avg_success_rate }}%</div>
          <div class="stat-label">平均可用率</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-value">{{ proxyStore.stats.avg_latency_ms }}ms</div>
          <div class="stat-label">平均延迟</div>
        </div>
      </el-col>
    </el-row>

    <!-- 代理列表 -->
    <el-card shadow="never" class="mt-16">
      <el-table :data="proxyStore.proxies" v-loading="proxyStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="protocol" label="协议" width="80">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.protocol.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="地址" min-width="160">
          <template #default="{ row }">{{ row.host }}:{{ row.port }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'active'" size="small" type="success">可用</el-tag>
            <el-tag v-else-if="row.status === 'inactive'" size="small" type="danger">不可用</el-tag>
            <el-tag v-else size="small" type="info">未知</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success_rate" label="可用率" width="80">
          <template #default="{ row }">
            <span :style="{ color: row.success_rate >= 80 ? '#67c23a' : row.success_rate >= 50 ? '#e6a23c' : '#f56c6c' }">
              {{ row.success_rate }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="avg_latency_ms" label="延迟" width="80">
          <template #default="{ row }">{{ row.avg_latency_ms || '-' }}ms</template>
        </el-table-column>
        <el-table-column prop="use_count" label="使用次数" width="90" />
        <el-table-column prop="last_check_at" label="最后检测" width="150">
          <template #default="{ row }">{{ formatTime(row.last_check_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="handleTest(row.id)">检测</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加代理弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加代理" width="500px">
      <el-form :model="addForm" label-width="80px" ref="addFormRef">
        <el-form-item label="名称" prop="name" :rules="[{ required: true }]">
          <el-input v-model="addForm.name" placeholder="代理名称" />
        </el-form-item>
        <el-form-item label="协议" prop="protocol">
          <el-select v-model="addForm.protocol" style="width:100%">
            <el-option label="HTTP" value="http" />
            <el-option label="HTTPS" value="https" />
            <el-option label="SOCKS5" value="socks5" />
          </el-select>
        </el-form-item>
        <el-form-item label="Host" prop="host" :rules="[{ required: true }]">
          <el-input v-model="addForm.host" placeholder="例: 1.2.3.4" />
        </el-form-item>
        <el-form-item label="端口" prop="port" :rules="[{ required: true }]">
          <el-input-number v-model="addForm.port" :min="1" :max="65535" style="width:100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="addForm.username" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="addForm.password" type="password" show-password placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="adding">添加</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入弹窗 -->
    <el-dialog v-model="batchDialogVisible" title="批量导入代理" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px">
        支持 JSON 数组格式，每项包含 host 和 port
        <br>例: [{"host":"1.2.3.4","port":8080},{"host":"5.6.7.8","port":3128}]
      </el-alert>
      <el-input v-model="batchInput" type="textarea" :rows="8" placeholder='[{"host":"1.2.3.4","port":8080}]' />
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProxyStore } from '../../stores/proxy'
import { ElMessage } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'

const proxyStore = useProxyStore()
const addDialogVisible = ref(false)
const batchDialogVisible = ref(false)
const adding = ref(false)
const addFormRef = ref(null)
const batchInput = ref('')

const addForm = ref({ name: '', protocol: 'http', host: '', port: 8080, username: '', password: '' })

onMounted(() => loadData())

async function loadData() {
  await Promise.all([proxyStore.fetchProxies(), proxyStore.fetchStats(), proxyStore.fetchGroups()])
}

function showAddDialog() {
  addForm.value = { name: '', protocol: 'http', host: '', port: 8080, username: '', password: '' }
  addDialogVisible.value = true
}

function showBatchDialog() {
  batchInput.value = ''
  batchDialogVisible.value = true
}

async function handleAdd() {
  try {
    await addFormRef.value.validate()
  } catch { return }
  adding.value = true
  try {
    await proxyStore.addProxy(addForm.value)
    addDialogVisible.value = false
    ElMessage.success('添加成功')
  } finally {
    adding.value = false
  }
}

async function handleBatchImport() {
  try {
    const proxies = JSON.parse(batchInput.value)
    if (!Array.isArray(proxies)) throw new Error('not array')
    const res = await proxyStore.batchImport(proxies)
    batchDialogVisible.value = false
    ElMessage.success(`成功 ${res.data.success}，失败 ${res.data.failed}`)
    await loadData()
  } catch {
    ElMessage.error('格式错误，请输入正确 JSON 数组')
  }
}

async function handleTest(id) {
  try {
    const d = await proxyStore.testProxy(id)
    ElMessage.success(`可用: ${d.available}, 延迟: ${d.latency_ms}ms`)
    await loadData()
  } catch {
    ElMessage.error('检测失败')
  }
}

async function handleDelete(id) {
  await proxyStore.deleteProxy(id)
  ElMessage.success('已删除')
}

async function handleRefresh() {
  await proxyStore.refreshAll()
  ElMessage.info('健康检查已触发')
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
.stat-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.stat-value { font-size: 24px; font-weight: bold; color: #333; }
.stat-label { font-size: 12px; color: #666; margin-top: 4px; }
</style>