<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 class="login-title">景区导览管理后台</h2>
      <el-form :model="form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" style="width: 100%" size="large">登录</el-button>
        </el-form-item>
      </el-form>
      <div class="login-tip">演示账号：任意用户名和密码均可登录</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const form = ref({ username: '', password: '' })

const handleLogin = () => {
  if (form.value.username && form.value.password) {
    localStorage.setItem('token', 'mock-token')
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } else {
    ElMessage.warning('请输入用户名和密码')
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  border-radius: 24px;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 35px -10px rgba(0,0,0,0.2);
}
.login-title {
  text-align: center;
  margin-bottom: 30px;
  color: var(--text-dark);
  font-weight: 600;
}
.login-tip {
  text-align: center;
  font-size: 12px;
  color: var(--text-gray);
  margin-top: 20px;
}
</style>