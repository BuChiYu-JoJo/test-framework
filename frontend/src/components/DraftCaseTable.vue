<template>
  <div class="draft-case-table">
    <div v-if="title" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div class="table-title">{{ title }}（{{ drafts.length }} 条）</div>
      <slot name="actions" />
    </div>
    <el-table :data="drafts" stripe size="small" @selection-change="onSelect" :max-height="maxHeight">
      <el-table-column v-if="selectable" type="selection" width="45" />
      <el-table-column type="index" width="50" label="#" />
      <el-table-column prop="title" label="用例名称" min-width="220">
        <template #default="{ row }">{{ row.title || row.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="module" label="模块" width="120">
        <template #default="{ row }"><el-tag size="small">{{ row.module || 'default' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="pType(row.priority)">{{ row.priority || 'P2' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="showSource" prop="source_test_point" label="来源" min-width="160" show-overflow-tooltip />
      <el-table-column label="步骤" width="70">
        <template #default="{ row }">{{ row.steps?.length || row.draft_steps?.length || 0 }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
const props = defineProps({
  drafts: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  selectable: { type: Boolean, default: true },
  showSource: { type: Boolean, default: false },
  maxHeight: { type: Number, default: 400 },
})

const emit = defineEmits(['selection-change'])

function onSelect(rows) {
  emit('selection-change', rows)
}

function pType(p) {
  if (p === 'P0') return 'danger'
  if (p === 'P1') return 'warning'
  if (p === 'P2') return 'primary'
  return 'info'
}
</script>

<style scoped>
.table-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
