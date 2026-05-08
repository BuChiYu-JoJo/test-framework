<template>
  <div class="unified-report" v-if="report">
    <el-descriptions :column="2" border size="small" class="mb-16">
      <el-descriptions-item label="任务 ID">{{ report.task_id }}</el-descriptions-item>
      <el-descriptions-item label="任务类型">
        <el-tag size="small">{{ report.task_type }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag size="small" :type="statusType(report.status)">{{ report.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="耗时">{{ formatDuration(report.duration_ms) }}</el-descriptions-item>
      <el-descriptions-item label="开始时间">{{ formatTime(report.started_at) }}</el-descriptions-item>
      <el-descriptions-item label="结束时间">{{ formatTime(report.finished_at) }}</el-descriptions-item>
      <el-descriptions-item v-if="report.error_msg" label="错误" :span="2">
        <span style="color:var(--el-color-danger)">{{ report.error_msg }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <!-- UI Steps -->
    <template v-if="report.task_type === 'ui' && report.steps?.length">
      <div class="section-title">执行步骤（{{ report.steps.length }}）</div>
      <el-table :data="report.steps" stripe size="small" max-height="400">
        <el-table-column prop="step_no" label="#" width="50" />
        <el-table-column prop="action" label="操作" width="90" />
        <el-table-column prop="target" label="目标" min-width="180" show-overflow-tooltip>
          <template #default="{ row }"><code style="font-size:12px">{{ row.target }}</code></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'passed' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="matched_strategy_type" label="命中策略" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.matched_strategy_type" size="small"
              :type="row.matched_strategy_type === 'ai_healed' ? 'warning' : 'info'">
              {{ row.matched_strategy_type }}
            </el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="80">
          <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
        </el-table-column>
        <el-table-column prop="error_msg" label="错误" min-width="160" show-overflow-tooltip />
        <el-table-column label="" width="60">
          <template #default="{ row }">
            <el-button v-if="row.status === 'failed'" size="small" type="warning" link
              @click="$emit('repair-step', row)">修复</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- Repair Records -->
    <template v-if="report.repair_records?.length">
      <div class="section-title">AI 修复记录（{{ report.repair_records.length }}）</div>
      <el-table :data="report.repair_records" stripe size="small" max-height="240">
        <el-table-column prop="locator_key" label="Locator" min-width="180" />
        <el-table-column prop="verdict" label="验证" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.verdict === 'verified' ? 'success' : 'warning'">{{ row.verdict }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="审核" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.review_status === 'accepted' ? 'success' : row.review_status === 'rejected' ? 'danger' : 'warning'">
              {{ row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- API Requests -->
    <template v-if="report.task_type === 'api' && report.requests?.length">
      <div class="section-title">API 请求（{{ report.requests.length }}）</div>
      <el-table :data="report.requests" stripe size="small" max-height="300">
        <el-table-column prop="method" label="方法" width="70" />
        <el-table-column prop="url" label="URL" min-width="260" show-overflow-tooltip />
        <el-table-column prop="status_code" label="状态码" width="80" />
        <el-table-column prop="duration_ms" label="耗时" width="80">
          <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
        </el-table-column>
      </el-table>
    </template>

    <!-- SEO Issues -->
    <template v-if="report.task_type === 'seo' && report.issues?.length">
      <div class="section-title">SEO 问题（{{ report.issues.length }}）</div>
      <el-table :data="report.issues" stripe size="small" max-height="300">
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="message" label="说明" min-width="300" />
        <el-table-column prop="severity" label="严重度" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.severity === 'error' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- Performance Metrics -->
    <template v-if="report.task_type === 'performance' && report.metrics">
      <div class="section-title">性能指标</div>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="LCP">{{ report.lcp ?? '-' }} ms</el-descriptions-item>
        <el-descriptions-item label="FID">{{ report.fid ?? '-' }} ms</el-descriptions-item>
        <el-descriptions-item label="CLS">{{ report.cls ?? '-' }}</el-descriptions-item>
      </el-descriptions>
    </template>

    <!-- Screenshots -->
    <template v-if="report.screenshots?.length">
      <div class="section-title">截图</div>
      <div class="screenshot-gallery">
        <el-image v-for="(src, idx) in report.screenshots" :key="idx"
          :src="src" fit="cover" :preview-src-list="report.screenshots"
          class="screenshot-thumb" preview-teleported />
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  report: { type: Object, default: null },
})

defineEmits(['repair-step'])

function statusType(status) {
  if (['passed', 'completed', 'success'].includes(status)) return 'success'
  if (['failed', 'error'].includes(status)) return 'danger'
  if (['running', 'pending'].includes(status)) return 'warning'
  return 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(ms) {
  const v = Number(ms || 0)
  if (v < 1000) return `${v}ms`
  if (v < 60000) return `${(v / 1000).toFixed(2)}s`
  return `${Math.floor(v / 60000)}m ${((v % 60000) / 1000).toFixed(1)}s`
}
</script>

<style scoped>
.unified-report { padding: 4px 0; }
.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 16px 0 8px;
  color: var(--el-text-color-primary);
}
.mb-16 { margin-bottom: 16px; }
.muted { color: #999; }
.screenshot-gallery { display: flex; gap: 8px; flex-wrap: wrap; }
.screenshot-thumb { width: 120px; height: 80px; border-radius: 4px; border: 1px solid var(--el-border-color); }
</style>
