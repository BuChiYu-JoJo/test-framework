<template>
  <div class="scheduler-view">
    <PageHeader title="定时任务" :crumbs="['首页', '定时任务']">
      <template #actions>
        <el-select v-model="filters.project_id" placeholder="按项目筛选" clearable size="default" style="width: 160px" @change="loadJobs">
          <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="filters.enabled" placeholder="状态" clearable size="default" style="width: 120px" @change="loadJobs">
          <el-option label="已启用" :value="true" />
          <el-option label="已禁用" :value="false" />
        </el-select>
        <el-button @click="loadJobs"><el-icon><Refresh /></el-icon> 刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建定时任务
        </el-button>
      </template>
    </PageHeader>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="deleteDialogVisible"
      title="删除定时任务"
      :message="`确定删除定时任务「${deleteTarget.name}」？`"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <el-card shadow="never" class="mt-16">
      <el-table :data="jobs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="cron_expr" label="Cron 表达式" width="160">
          <template #default="{ row }">
            <code style="font-size:12px; color: #67C23A">{{ row.cron_expr }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="case_id" label="用例ID" width="80" />
        <el-table-column prop="env" label="环境" width="80">
          <template #default="{ row }"><el-tag size="small">{{ row.env }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="90">
          <template #default="{ row }">
            <StatusBadge :status="row.enabled ? 'enabled' : 'disabled'" />
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="上次执行" width="170">
          <template #default="{ row }">{{ formatTime(row.last_run_at) }}</template>
        </el-table-column>
        <el-table-column prop="run_count" label="累计执行" width="90">
          <template #default="{ row }">{{ row.run_count || 0 }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="success" link @click="triggerJob(row)" :loading="triggeringId === row.id">
              立即执行
            </el-button>
            <el-button size="small" :type="row.enabled ? 'warning' : 'success'" link @click="toggleEnabled(row)">
              {{ row.enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button size="small" type="danger" link @click="deleteJob(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新建定时任务' : '编辑定时任务'" width="560px">
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="如：每日回归测试" maxlength="200" />
        </el-form-item>

        <el-form-item label="关联项目" prop="project_id">
          <el-select v-model="form.project_id" placeholder="选择项目" style="width: 100%">
            <el-option v-for="p in projectsStore.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="关联用例" prop="case_id">
          <el-select v-model="form.case_id" placeholder="选择用例" style="width: 100%" filterable>
            <el-option v-for="c in filteredCases" :key="c.id" :label="`[${c.id}] ${c.name}`" :value="c.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="执行环境" prop="env">
          <el-select v-model="form.env" style="width: 100%">
            <el-option label="test" value="test" />
            <el-option label="staging" value="staging" />
            <el-option label="prod" value="prod" />
          </el-select>
        </el-form-item>

        <!-- Cron 表达式 -->
        <el-form-item label="Cron 表达式" prop="cron_expr">
          <el-input v-model="form.cron_expr" placeholder="0 0 * * *" style="width: 100%" />
          <div class="cron-hint">
            格式：秒 分 时 日 月 周 &nbsp;
            <el-link type="primary" href="https://croniter.readthedocs.io/" target="_blank" :underline="false">参考文档</el-link>
          </div>
        </el-form-item>

        <!-- 快捷预设 -->
        <el-form-item label="快捷预设">
          <el-space wrap>
            <el-button v-for="preset in cronPresets" :key="preset.label" size="small" @click="applyPreset(preset)">
              {{ preset.label }}
            </el-button>
          </el-space>
        </el-form-item>

        <el-form-item label="启用任务">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <el-form-item label="执行完成通知">
          <el-switch v-model="form.notify_on_complete" />
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选描述" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { schedulerApi } from '@/api'
import { projectsApi, casesApi } from '@/api'
import { useProjectsStore } from '@/stores/projects'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const projectsStore = useProjectsStore()

const jobs = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const triggeringId = ref(null)
const formRef = ref(null)

const editingId = ref(null)
const allCases = ref([])

const deleteDialogVisible = ref(false)
const deleteTarget = ref({ id: null, name: '' })

const filters = reactive({ project_id: null, enabled: null })

const emptyForm = () => ({
  name: '',
  project_id: null,
  case_id: null,
  env: 'test',
  cron_expr: '0 0 * * *',
  cron_second: '0',
  cron_minute: '0',
  cron_hour: '*',
  cron_day: '*',
  cron_month: '*',
  cron_weekday: '*',
  enabled: true,
  notify_on_complete: false,
  description: '',
})

const form = reactive(emptyForm())

const formRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  case_id: [{ required: true, message: '请选择用例', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }],
}

const cronPresets = [
  { label: '每天凌晨', cron_expr: '0 0 * * *', cron_second: '0', cron_minute: '0', cron_hour: '*', cron_day: '*', cron_month: '*', cron_weekday: '*' },
  { label: '每小时', cron_expr: '0 0 * * * *', cron_second: '0', cron_minute: '0', cron_hour: '*', cron_day: '*', cron_month: '*', cron_weekday: '*' },
  { label: '每天 9:00', cron_expr: '0 0 9 * *', cron_second: '0', cron_minute: '0', cron_hour: '9', cron_day: '*', cron_month: '*', cron_weekday: '*' },
  { label: '每周一 9:00', cron_expr: '0 0 9 * * 1', cron_second: '0', cron_minute: '0', cron_hour: '9', cron_day: '*', cron_month: '*', cron_weekday: '1' },
  { label: '每月 1 号', cron_expr: '0 0 1 1 *', cron_second: '0', cron_minute: '0', cron_hour: '1', cron_day: '1', cron_month: '*', cron_weekday: '*' },
]

const filteredCases = computed(() => {
  if (!form.project_id) return []
  return allCases.value.filter(c => c.project_id === form.project_id)
})

function applyPreset(preset) {
  Object.assign(form, preset)
}

async function loadJobs() {
  loading.value = true
  try {
    const params = {}
    if (filters.project_id) params.project_id = filters.project_id
    if (filters.enabled !== null) params.enabled = filters.enabled
    jobs.value = await schedulerApi.list(params)
  } catch (e) {
    ElMessage.error('加载定时任务失败')
  } finally {
    loading.value = false
  }
}

async function loadCases() {
  try {
    allCases.value = await casesApi.list({ page_size: 1000 })
  } catch (e) {
    console.error('加载用例失败', e)
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    project_id: row.project_id,
    case_id: row.case_id,
    env: row.env,
    cron_expr: row.cron_expr,
    cron_second: row.cron_second,
    cron_minute: row.cron_minute,
    cron_hour: row.cron_hour,
    cron_day: row.cron_day,
    cron_month: row.cron_month,
    cron_weekday: row.cron_weekday,
    enabled: row.enabled,
    notify_on_complete: row.notify_on_complete,
    description: row.description || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await schedulerApi.create({ ...form })
      ElMessage.success('创建成功')
    } else {
      await schedulerApi.update(editingId.value, { ...form })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    await loadJobs()
  } catch (e) {
    ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
  } finally {
    submitting.value = false
  }
}

async function triggerJob(row) {
  triggeringId.value = row.id
  try {
    await schedulerApi.run(row.id)
    ElMessage.success(`任务 "${row.name}" 已触发`)
  } catch (e) {
    ElMessage.error('触发失败')
  } finally {
    triggeringId.value = null
  }
}

async function toggleEnabled(row) {
  try {
    await schedulerApi.update(row.id, { enabled: !row.enabled })
    ElMessage.success(row.enabled ? '已禁用' : '已启用')
    await loadJobs()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function deleteJob(row) {
  deleteTarget.value = { id: row.id, name: row.name }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  try {
    await schedulerApi.delete(deleteTarget.value.id)
    ElMessage.success('删除成功')
    await loadJobs()
    done()
  } catch (e) {
    ElMessage.error('删除失败')
    done()
  }
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

onMounted(async () => {
  await projectsStore.loadProjects()
  await loadCases()
  await loadJobs()
})
</script>

<style scoped>
.cron-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
