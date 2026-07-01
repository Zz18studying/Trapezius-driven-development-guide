<template>
  <div class="welcome-page">
    <div class="welcome-bg"></div>
    <div class="welcome-mask"></div>
    <div class="welcome-content">
      <h1>你好，管理员</h1>
      <p>欢迎来到灵山胜境 · 智慧导览后台</p>
      <el-button 
        type="primary" 
        size="large" 
        round 
        @click="enterDashboard"
        class="welcome-btn"
      >
        进入管理界面 →
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const enterDashboard = () => {
  router.push('/admin/dashboard')
}
</script>

<style scoped>
.welcome-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.welcome-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url('@/assets/scenery-bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-color: #1a3a4a;
}

.welcome-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(26, 58, 74, 0.7) 0%, rgba(44, 110, 138, 0.5) 60%, rgba(58, 138, 170, 0.3) 100%);
}

.welcome-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
  animation: welcomeFadeIn 1.5s ease-out;
  padding: 40px;
}

.welcome-content h1 {
  font-size: 56px;
  font-weight: 700;
  margin: 0 0 12px 0;
  letter-spacing: 6px;
  text-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.welcome-content p {
  font-size: 18px;
  opacity: 0.85;
  margin: 0 0 36px 0;
  letter-spacing: 8px;
  font-weight: 300;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.2);
}

.welcome-btn {
  padding: 14px 48px;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  color: white;
  transition: all 0.3s ease;
}

.welcome-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

@keyframes welcomeFadeIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>