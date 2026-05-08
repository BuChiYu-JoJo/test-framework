<template>
  <div class="projects-view">
    <PageHeader title="项目管理" :crumbs="['首页', '项目']">
      <template #actions>
        <el-button type="primary" @click="showDialog('create')">
          <el-icon><Plus /></el-icon> 新建项目
        </el-button>
      </template>
    </PageHeader>

    <ConfirmDialog
      v-model="deleteDialogVisible"
      title="删除项目"
      :message="`确认删除项目「${deleteTarget.name}」？删除后将无法恢复。`"
      type="danger"
      confirm-text="删除"
      @confirm="confirmDelete"
    />

    <el-card shadow="never" class="mt-16">
      <el-table :data="projectsStore.projects" v-loading="projectsStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="项目名称" min-width="150">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="env_config" label="Base URL" min-width="180">
          <template #default="{ row }">
            <span v-if="row.env_config?.base_url" class="base-url-text">{{ row.env_config.base_url }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="goToCases(row.id)">用例</el-button>
            <el-button size="small" type="primary" link @click="showDialog('edit', row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="如：dataify" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input
            v-model="form.base_url"
            placeholder="如：https://xxx.com（执行用例时拼接的默认域名）"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="项目描述..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useProjectsStore } from '../../stores/projects'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import PageHeader from '../../components/PageHeader.vue'

const router = useRouter()
const projectsStore = useProjectsStore()

const dialogVisible = ref(false)
const dialogMode = ref('create')
const saving = ref(false)
const form = ref({ name: '', description: '', base_url: '' })
const deleteDialogVisible = ref(false)
const deleteTarget = ref({ id: null, name: '' })

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建项目' : '编辑项目'))

onMounted(() => {
  projectsStore.fetchProjects()
})

function showDialog(mode, row = null) {
  dialogMode.value = mode
  if (row) {
    form.value = {
      name: row.name,
      description: row.description,
      base_url: row.env_config?.base_url || '',
    }
  } else {
    form.value = { name: '', description: '', base_url: '' }
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      env_config: form.value.base_url ? { base_url: form.value.base_url } : {},
    }
    if (dialogMode.value === 'create') {
      await projectsStore.createProject(payload)
    } else {
      const row = projectsStore.projects.find((p) => p.name === form.value.name)
      if (row) await projectsStore.updateProject(row.id, payload)
    }
    dialogVisible.value = false
    ElMessage.success('保存成功')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  const row = projectsStore.projects.find((p) => p.id === id)
  deleteTarget.value = { id, name: row?.name || '' }
  deleteDialogVisible.value = true
}

async function confirmDelete({ done }) {
  try {
    await projectsStore.deleteProject(deleteTarget.value.id)
    ElMessage.success('删除成功')
    done()
  } catch {
    done()
  }
}

function goToCases(projectId) {
  router.push({ path: '/cases', query: { project_id: projectId } })
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.mt-16 { margin-top: 16px; }
.base-url-text {
  font-family: monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.text-muted {
  color: var(--el-text-color-placeholder);
}
</style>
