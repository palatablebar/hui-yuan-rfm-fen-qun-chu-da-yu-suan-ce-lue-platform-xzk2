import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/segments' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/segments',
      name: 'segments',
      component: () => import('../pages/SegmentsPage.vue'),
      meta: { title: '分群总览' },
    },
    {
      path: '/members',
      name: 'members',
      component: () => import('../pages/MembersPage.vue'),
      meta: { title: 'RFM 明细' },
    },
    {
      path: '/strategy',
      name: 'strategy',
      component: () => import('../pages/StrategyPage.vue'),
      meta: { title: '策略配置' },
    },
    {
      path: '/outreach',
      name: 'outreach',
      component: () => import('../pages/OutreachPage.vue'),
      meta: { title: '名单导出与触达' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/segments' },
  ],
})

setupGuards(router)

export default router
