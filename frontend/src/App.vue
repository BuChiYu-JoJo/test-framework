<template>
  <el-container class="app-container">
    <!-- 侧边导航 -->
    <el-aside width="220px">
      <div class="logo">Test Framework</div>
      <el-menu
        :default-active="$route.path"
        class="sidebar-menu"
        background-color="#1a1a2e"
        text-color="#a0a0b0"
        active-text-color="#ff7b54"
        router
      >
        <el-menu-item index="/cases">
          <el-icon><Document /></el-icon>
          <span>用例管理</span>
        </el-menu-item>
        <el-menu-item index="/projects">
          <el-icon><FolderOpened /></el-icon>
          <span>项目管理</span>
        </el-menu-item>
        <el-menu-item index="/locators">
          <el-icon><Connection /></el-icon>
          <span>Locators</span>
        </el-menu-item>
        <el-menu-item index="/execution">
          <el-icon><VideoPlay /></el-icon>
          <span>执行中心</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><DataAnalysis /></el-icon>
          <span>报告中心</span>
        </el-menu-item>
        <el-menu-item index="/scheduler">
          <el-icon><Timer /></el-icon>
          <span>定时任务</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item index="/ai-tools">
          <el-icon><Cpu /></el-icon>
          <span>AI 工具</span>
        </el-menu-item>
        <el-menu-item index="/performance">
          <el-icon><Odometer /></el-icon>
          <span>性能检测</span>
        </el-menu-item>
        <el-menu-item index="/api-test">
          <el-icon><Operation /></el-icon>
          <span>接口检测</span>
        </el-menu-item>
        <el-menu-item index="/seo">
          <el-icon><Search /></el-icon>
          <span>SEO 检测</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitleMap = {
  '/cases': '用例管理',
  '/projects': '项目管理',
  '/locators': 'Locators 管理',
  '/execution': '执行中心',
  '/reports': '报告中心',
  '/scheduler': '定时任务',
  '/settings': '系统设置',
  '/ai-tools': 'AI 工具',
  '/performance': '性能检测',
  '/api-test': '接口检测',
  '/seo': 'SEO 检测',
}

const pageTitle = computed(() => pageTitleMap[route.path] || '测试框架')
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
}

.app-container {
  height: 100vh;
}

.el-aside {
  background-color: #1a1a2e;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #ff7b54;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #2a2a3e;
}

.sidebar-menu {
  border-right: none !important;
}

.sidebar-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #252540 !important;
}

.header {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.main-content {
  background: #f5f6fa;
  padding: 24px;
}
</style>
