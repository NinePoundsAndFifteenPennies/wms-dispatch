<template>
  <div class="login-page">
    <div class="bg-shape shape-1"></div>
    <div class="bg-shape shape-2"></div>
    
    <div class="login-content">
      <section class="login-hero">
        <div class="hero-brand">
          <div class="logo-mark">WD</div>
          <span class="brand-text">WMS DISPATCH</span>
        </div>
        
        <div class="hero-image-wrapper">
          <img src="../assets/images/login.png" alt="WMS Login" class="hero-image" />
        </div>
        
        <div class="hero-text-jumping">
          <div class="jump-item" style="--delay: 0s">
            <el-icon><Monitor /></el-icon>
            <span>智能仓储中枢</span>
          </div>
          <div class="jump-item" style="--delay: 0.2s">
            <el-icon><Tickets /></el-icon>
            <span>多端工单协同</span>
          </div>
          <div class="jump-item" style="--delay: 0.4s">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据实时洞察</span>
          </div>
        </div>
      </section>

      <section class="login-form-container">
        <el-card class="login-card">
          <template #header>
            <div class="card-head">
              <div>
                <h2>欢迎登录</h2>
                <p class="subtitle">登录系统以进入调度中枢</p>
              </div>
              <el-tag effect="dark" type="success" round>企业版</el-tag>
            </div>
          </template>
          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent>
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="请输入账号" :prefix-icon="User" size="large" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="请输入密码"
                :prefix-icon="Lock"
                size="large"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-alert v-if="errorMessage" type="error" :title="errorMessage" show-icon :closable="false" style="margin-bottom: 16px" />
            <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleLogin">
              立即登录
            </el-button>
          </el-form>
        </el-card>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Monitor, Tickets, User, Lock } from '@element-plus/icons-vue'
import { useAuthStore, getDefaultPathByRole } from '../stores/auth'
import { authApi } from '../api/auth'

const form = reactive({
  username: '',
  password: '',
})
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}
const formRef = ref()
const loading = ref(false)
const errorMessage = ref('')

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

async function handleLogin() {
  errorMessage.value = ''
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const response = await authApi.login(form)
    const token = response.data?.data?.token
    const user = response.data?.data?.user
    if (!token || !user) {
      throw new Error('登录响应无效')
    }

    authStore.setSession(token, user)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect
    if (typeof redirect === 'string' && redirect.startsWith('/')) {
      await router.push(redirect)
      return
    }
    await router.push(getDefaultPathByRole(user.role))
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4ebf5 100%);
  overflow: hidden;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  opacity: 0.6;
}

.shape-1 {
  width: 500px;
  height: 500px;
  background: #a3e4d7;
  top: -150px;
  left: -100px;
}

.shape-2 {
  width: 600px;
  height: 600px;
  background: #fdf5e6;
  bottom: -200px;
  right: -150px;
}

.login-content {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  max-width: 1200px;
  min-height: 600px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.8);
  overflow: hidden;
  margin: 20px;
}

.login-hero {
  flex: 1.1;
  display: flex;
  flex-direction: column;
  padding: 50px;
  background: linear-gradient(140deg, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.1) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.5);
}

.hero-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 40px;
}

.logo-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-deep));
  box-shadow: 0 8px 16px rgba(28, 156, 137, 0.2);
}

.brand-text {
  font-size: 20px;
  font-weight: 600;
  color: #122230;
  letter-spacing: 0.05em;
}

.hero-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
}

.hero-image {
  width: 100%;
  max-width: 480px;
  height: auto;
  object-fit: contain;
  filter: drop-shadow(0 20px 30px rgba(0, 0, 0, 0.08));
  transition: transform 0.3s ease;
}

.hero-image:hover {
  transform: translateY(-5px);
}

.hero-text-jumping {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-top: auto;
}

.jump-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #1c9c89;
  font-size: 15px;
  font-weight: 600;
  animation: jump 2.5s infinite ease-in-out;
  animation-delay: var(--delay);
}

.jump-item .el-icon {
  font-size: 28px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  box-shadow: 0 12px 24px rgba(28, 156, 137, 0.12);
  transition: all 0.3s ease;
}

.jump-item:hover .el-icon {
  transform: scale(1.1);
  box-shadow: 0 15px 30px rgba(28, 156, 137, 0.18);
}

@keyframes jump {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.login-form-container {
  flex: 0.9;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  background: rgba(255, 255, 255, 0.4);
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 20px;
  box-shadow: 0 15px 35px rgba(31, 53, 75, 0.08);
  border: none;
  background: rgba(255, 255, 255, 0.9);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.card-head h2 {
  margin: 0 0 4px 0;
  color: #122230;
  font-size: 24px;
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.submit {
  width: 100%;
  border-radius: 12px;
  font-size: 16px;
  margin-top: 12px;
  height: 44px;
}

:deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 4px 12px;
}

@media (max-width: 900px) {
  .login-content {
    flex-direction: column;
    margin: 16px;
    min-height: auto;
  }
  
  .login-hero {
    padding: 30px;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.5);
  }
  
  .hero-text-jumping {
    gap: 20px;
  }
  
  .jump-item .el-icon {
    font-size: 24px;
    padding: 12px;
  }
}
</style>
