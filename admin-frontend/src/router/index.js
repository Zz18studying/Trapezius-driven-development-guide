import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'knowledge', name: 'Knowledge', component: () => import('@/views/Knowledge.vue') },
      { path: 'sentiment', name: 'Sentiment', component: () => import('@/views/Sentiment.vue') },
      { path: 'dhconfig', name: 'DhConfig', component: () => import('@/views/DhConfig.vue') },
      { path: 'conversations', name: 'Conversations', component: () => import('@/views/Conversations.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router