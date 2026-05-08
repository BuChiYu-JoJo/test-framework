<template>
  <div class="page-header">
    <!-- 标题行 -->
    <div class="header-main">
      <!-- 面包屑 -->
      <el-breadcrumb v-if="crumbs.length > 0" separator="/" class="header-breadcrumb">
        <el-breadcrumb-item v-for="(crumb, idx) in crumbs" :key="idx">
          <span v-if="idx === crumbs.length - 1" class="breadcrumb-current">{{ crumb }}</span>
          <span v-else>{{ crumb }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>

      <div class="header-title-row">
        <h2 class="header-title">{{ title }}</h2>
        <div v-if="$slots.extra" class="header-extra">
          <slot name="extra" />
        </div>
      </div>
    </div>

    <!-- 操作按钮区（默认插槽） -->
    <div v-if="$slots.actions" class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  /** 页面大标题 */
  title: {
    type: String,
    default: '',
  },
  /**
   * 面包屑路径数组
   * @example ['首页', '用户管理']
   */
  crumbs: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 12px;
}

.header-main {
  flex: 1;
  min-width: 0;
}

.header-breadcrumb {
  margin-bottom: 6px;
}

.breadcrumb-current {
  color: var(--el-text-color-secondary);
  font-weight: normal;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  line-height: 1.4;
}

.header-extra {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
