<template>
  <el-container style="height: 100vh; background: #eef4f8;">
    <!-- 侧边栏 -->
    <el-aside width="240px" style="background: linear-gradient(180deg, #1a3a4a 0%, #2c6e8a 60%, #3a8aaa 100%); color: white; display: flex; flex-direction: column; flex-shrink: 0; box-shadow: 2px 0 20px rgba(0, 0, 0, 0.12);">
      <div class="logo-area">
        <span class="logo-icon">🏞️</span>
        <span class="logo-text">智游景区</span>
        <span class="logo-sub">管理后台</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        background-color="transparent"
        text-color="rgba(255,255,255,0.85)"
        active-text-color="#ffffff"
        router
        style="border-right: none; padding: 8px 12px; flex: 1;"
      >
        <el-menu-item index="/admin/dashboard" style="border-radius: 12px; margin-bottom: 4px; height: 48px;">
          <el-icon><DataLine /></el-icon>
          <span>数据大屏</span>
        </el-menu-item>
        <el-menu-item index="/admin/knowledge" style="border-radius: 12px; margin-bottom: 4px; height: 48px;">
          <el-icon><Document /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/sentiment" style="border-radius: 12px; margin-bottom: 4px; height: 48px;">
          <el-icon><PieChart /></el-icon>
          <span>游客感受度报告</span>
        </el-menu-item>
        <el-menu-item index="/admin/conversations" style="border-radius: 12px; margin-bottom: 4px; height: 48px;">
          <el-icon><ChatLineSquare /></el-icon>
          <span>对话查询</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">v2.0 · 智慧灵山</div>
    </el-aside>

    <el-container>
      <el-header style="background: rgba(255,255,255,0.75); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(44, 110, 138, 0.08); display: flex; align-items: center; justify-content: space-between; padding: 0 28px; height: 64px;">
        <div class="header-title">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }" style="font-weight: 500;">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ routeName }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="user-info">
          <el-avatar :size="34" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" style="border: 2px solid rgba(44, 110, 138, 0.15);" />
          <span class="username">管理员</span>
        </div>
      </el-header>

      <!-- ✅ 核心修改：添加 key 强制刷新 -->
      <el-main style="padding: 24px 28px; background: #eef4f8; overflow-y: auto;">
        <router-view :key="$route.fullPath" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { 
  DataLine, 
  Document, 
  PieChart, 
  ChatLineSquare 
} from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => route.path)

const routeName = computed(() => {
  const map = {
    '/admin/dashboard': '数据大屏',
    '/admin/knowledge': '知识库管理',
    '/admin/sentiment': '游客感受度报告',
    '/admin/conversations': '对话查询'
  }
  return map[route.path] || ''
})
</script>

<style scoped>
.logo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
}
.logo-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 4px;
}
.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #ffffff;
  display: block;
}
.logo-sub {
  font-size: 11px;
  opacity: 0.6;
  letter-spacing: 4px;
  margin-top: 2px;
  color: rgba(255, 255, 255, 0.6);
}

.sidebar-footer {
  padding: 16px 20px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
  opacity: 0.4;
  text-align: center;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.header-title {
  font-size: 14px;
  color: #1a2a3a;
}
.header-title :deep(.el-breadcrumb__inner) {
  color: #1a2a3a;
}
.header-title :deep(.el-breadcrumb__inner.is-link) {
  color: #2c6e8a;
  font-weight: 500;
}
.header-title :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #1a3a4a;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.username {
  font-size: 14px;
  font-weight: 500;
  color: #1a3a4a;
  cursor: default;
}

/* 侧边栏菜单样式 */
:deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.85) !important;
  transition: all 0.2s ease;
}
:deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.12) !important;
  color: #ffffff !important;
}
:deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.2) !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15) !important;
  color: #ffffff !important;
  font-weight: 600;
}
:deep(.el-menu-item.is-active .el-icon) {
  color: #ffffff !important;
}
:deep(.el-menu-item.is-active span) {
  color: #ffffff !important;
}
:deep(.el-menu-item .el-icon) {
  color: rgba(255, 255, 255, 0.75);
}

@media (max-width: 820px) {
  .el-aside {
    width: 72px !important;
  }
  .logo-text,
  .logo-sub,
  .sidebar-footer {
    display: none;
  }
  .logo-area {
    padding: 16px 0 12px;
  }
  .logo-icon {
    font-size: 28px;
    margin-bottom: 0;
  }
  :deep(.el-menu-item) {
    justify-content: center !important;
    padding: 0 8px !important;
  }
  :deep(.el-menu-item .el-icon) {
    font-size: 20px;
  }
  :deep(.el-menu-item span) {
    display: none;
  }
  .el-header {
    padding: 0 16px !important;
  }
  .el-main {
    padding: 16px !important;
  }
}
</style>