import { createRouter, createWebHistory } from 'vue-router'
import Welcome from '@/views/Welcome.vue'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/admin',
    redirect: '/admin/welcome'
  },
  {
    path: '/admin/welcome',
    name: 'Welcome',
    component: Welcome
  },
  {
    path: '/admin',
    component: MainLayout,
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'knowledge', component: () => import('@/views/Knowledge.vue') },
      { path: 'sentiment', component: () => import('@/views/Sentiment.vue') },
      { path: 'conversations', component: () => import('@/views/Conversations.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  next()
})

export default router