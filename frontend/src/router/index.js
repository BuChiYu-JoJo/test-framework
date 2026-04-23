import { createRouter, createWebHistory } from 'vue-router'

import CasesView from '../views/cases/CasesView.vue'
import ProjectsView from '../views/projects/ProjectsView.vue'
import ExecutionView from '../views/execution/ExecutionView.vue'
import ReportsView from '../views/reports/ReportsView.vue'
import LocatorsView from '../views/locators/LocatorsView.vue'
import SchedulerView from '../views/scheduler/SchedulerView.vue'
import SettingsView from '../views/settings/SettingsView.vue'
import AiToolsView from '../views/ai/AiToolsView.vue'
import PerformanceView from '../views/performance/PerformanceView.vue'
import ApiTestView from '../views/api-test/ApiTestView.vue'
import SeoView from '../views/seo/SeoView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/cases',
    },
    {
      path: '/cases',
      name: 'Cases',
      component: CasesView,
    },
    {
      path: '/projects',
      name: 'Projects',
      component: ProjectsView,
    },
    {
      path: '/locators',
      name: 'Locators',
      component: LocatorsView,
    },
    {
      path: '/execution',
      name: 'Execution',
      component: ExecutionView,
    },
    {
      path: '/reports',
      name: 'Reports',
      component: ReportsView,
    },
    {
      path: '/scheduler',
      name: 'Scheduler',
      component: SchedulerView,
    },
    {
      path: '/settings',
      name: 'Settings',
      component: SettingsView,
    },
    {
      path: '/ai-tools',
      name: 'AiTools',
      component: AiToolsView,
    },
    {
      path: '/performance',
      name: 'Performance',
      component: PerformanceView,
    },
    {
      path: '/api-test',
      name: 'ApiTest',
      component: ApiTestView,
    },
    {
      path: '/seo',
      name: 'SEO',
      component: SeoView,
    },
  ],
})

export default router