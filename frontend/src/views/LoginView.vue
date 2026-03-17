<template>
  <div class="login-page">
    <section class="login-hero">
      <div class="logo-row">
        <span class="logo-mark">{{ BRAND_SHORT_NAME }}</span>
        <p>WMS DISPATCH</p>
      </div>
      <h1>
        <el-icon><Monitor /></el-icon>
        让仓储调度更快、更稳、更可视化
      </h1>
      <span>统一处理订单、工单、库存和跨仓协作。</span>
      <div class="hero-tags">
        <div>
          <el-icon><Tickets /></el-icon>
          订单全链路可视化
        </div>
        <div>
          <el-icon><Box /></el-icon>
          工单执行状态追踪
        </div>
        <div>
          <el-icon><DataAnalysis /></el-icon>
          运营数据实时洞察
        </div>
      </div>
    </section>

    <el-card class="login-card">
      <template #header>
        <div class="card-head">
          <h2>登录系统</h2>
          <el-tag effect="dark" type="success" round>安全认证</el-tag>
        </div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent>
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-alert v-if="errorMessage" type="error" :title="errorMessage" show-icon :closable="false" />
        <el-button type="primary" class="submit" :loading="loading" @click="handleLogin">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Box, DataAnalysis, Monitor, Tickets } from '@element-plus/icons-vue'
import { useAuthStore, getDefaultPathByRole } from '../stores/auth'
import http from '../api/http'

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
const BRAND_SHORT_NAME = 'WD'

async function handleLogin() {
  errorMessage.value = ''
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const response = await http.post('/auth/login', form)
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
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  align-items: center;
  gap: 24px;
  padding: 32px;
  background:
    radial-gradient(circle at 88% 8%, rgba(242, 153, 74, 0.16) 0%, transparent 30%),
    radial-gradient(circle at 8% 12%, rgba(28, 156, 137, 0.18) 0%, transparent 34%),
    linear-gradient(140deg, #eef8f6 0%, #f6fbff 48%, #fff4e8 100%);
}

.login-hero {
  padding: 30px;
  border: 1px solid #d8e5ef;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 12px 30px rgba(31, 53, 75, 0.1);
}

.logo-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-deep));
}

.login-hero p {
  margin: 0;
  letter-spacing: 0.08em;
  font-size: 12px;
  color: #0f766e;
}

.login-hero h1 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 0;
  line-height: 1.2;
  font-size: clamp(28px, 3.5vw, 48px);
  color: #122230;
}

.login-hero span {
  display: block;
  margin-top: 14px;
  font-size: 16px;
  color: #425466;
}

.hero-tags {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}

.hero-tags > div {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid #d8e7e3;
  background: #f4fbf8;
  font-size: 13px;
  color: #314657;
}

.login-card {
  width: min(90vw, 420px);
  justify-self: center;
  border-radius: 16px;
  border: 1px solid #d8e5ef;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 12px 30px rgba(31, 53, 75, 0.1);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h2 {
  margin: 0 0 16px;
}

.submit {
  width: 100%;
  margin-top: 6px;
  border-radius: 10px;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
    padding: 20px;
  }

  .login-hero {
    padding: 6px;
  }

  .login-card {
    width: 100%;
  }
}
</style>
