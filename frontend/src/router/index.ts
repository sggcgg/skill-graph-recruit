import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { keepAlive: false }
  },
  {
    path: '/search',
    name: 'JobSearch',
    component: () => import('@/views/JobSearch.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/graph',
    name: 'SkillGraph',
    component: () => import('@/views/SkillGraph.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/match',
    name: 'MatchDashboard',
    component: () => import('@/views/MatchDashboard.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('@/views/Analytics.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/skill-management',
    name: 'SkillManagement',
    component: () => import('@/views/SkillManagement.vue'),
    meta: { keepAlive: true }
  },
  {
    path: '/monitoring',
    name: 'Monitoring',
    component: () => import('@/views/Monitoring.vue'),
    meta: { keepAlive: false }
  },
  {
    path: '/user-center',
    name: 'UserCenter',
    component: () => import('@/views/UserCenter.vue'),
    meta: { keepAlive: false, requiresAuth: true }
  },
  {
    path: '/api-test',
    name: 'ApiTest',
    component: () => import('@/views/ApiTest.vue'),
    meta: { keepAlive: false }
  },
  {
    path: '/test',
    name: 'TestAPI',
    component: () => import('@/views/TestAPI.vue'),
    meta: { keepAlive: false }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 导航守卫：需要登录的页面，未登录时拦截并提示
router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      ElMessage.warning('请先登录后再访问用户中心')
      // 触发全局事件，让 Navbar 弹出登录对话框
      window.dispatchEvent(new CustomEvent('show-login-dialog', { detail: { redirect: to.fullPath } }))
      next({ path: '/' })
      return
    }
  }
  next()
})

export default router
