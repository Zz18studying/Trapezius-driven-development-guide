<template>
  <el-container style="height: 100vh; background: var(--bg-page);">
    <!-- 侧边栏 -->
    <el-aside width="260px" style="background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); border-right: 1px solid var(--border-light); box-shadow: var(--shadow-sm);">
      <div class="logo-area">
        <span class="logo-icon">🏞️</span>
        <span class="logo-text">智游景区</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="transparent"
        text-color="var(--text-gray)"
        active-text-color="var(--primary-color)"
        router
        style="border-right: none;"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>数据大屏</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Document /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/sentiment">
          <el-icon><PieChart /></el-icon>
          <span>游客感受度报告</span>
        </el-menu-item>
        <el-menu-item index="/dhconfig">
          <el-icon><User /></el-icon>
          <span>数字人形象管理</span>
        </el-menu-item>
        <el-menu-item index="/conversations">
          <el-icon><ChatLineSquare /></el-icon>
          <span>对话查询</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background: rgba(255,255,255,0.8); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border-light); display: flex; align-items: center; justify-content: space-between; padding: 0 24px;">
        <div class="header-title">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ routeName }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="user-info">
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          <el-dropdown @command="handleCommand">
            <span class="username">管理员</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main style="padding: 24px;">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  DataLine, 
  Document, 
  PieChart, 
  User, 
  ChatLineSquare 
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)

const routeName = computed(() => {
  const map = {
    '/dashboard': '数据大屏',
    '/knowledge': '知识库管理',
    '/sentiment': '游客感受度报告',
    '/dhconfig': '数字人形象管理',
    '/conversations': '对话查询'
  }
  return map[route.path] || ''
})

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-weight: bold;
  font-size: 18px;
  border-bottom: 1px solid var(--border-light);
}
.logo-icon {
  font-size: 24px;
}
.logo-text {
  background: linear-gradient(135deg, #10b981, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.username {
  margin-left: 10px;
  cursor: pointer;
}
.header-title {
  font-size: 14px;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>