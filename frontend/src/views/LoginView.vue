<template>
  <div class="login-page">
    <section class="login-hero">
      <p>WMS DISPATCH</p>
      <h1>让仓储调度更快、更稳、更可视化</h1>
      <span>统一处理订单、工单、库存和跨仓协作。</span>
    </section>

    <el-card class="login-card">
      <h2>登录系统</h2>
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
  padding: 24px;
  background: linear-gradient(140deg, #f0f8f5 0%, #f6fbff 48%, #fff4e8 100%);
}

.login-hero {
  padding: 24px;
}

.login-hero p {
  margin: 0;
  letter-spacing: 0.08em;
  font-size: 12px;
  color: #0f766e;
}

.login-hero h1 {
  margin: 8px 0 0;
  line-height: 1.2;
  font-size: clamp(28px, 4vw, 52px);
  color: #122230;
}

.login-hero span {
  display: block;
  margin-top: 14px;
  font-size: 16px;
  color: #425466;
}

.login-card {
  width: min(90vw, 420px);
  justify-self: center;
  border-radius: 14px;
}

h2 {
  margin: 0 0 16px;
}

.submit {
  width: 100%;
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
