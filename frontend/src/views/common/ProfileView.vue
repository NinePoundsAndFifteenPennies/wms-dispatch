<template>
  <div class="profile-page" v-loading="loading">
    <el-card shadow="never" class="profile-card">
      <div class="profile-head">
        <el-avatar :size="88" :src="getAvatarUrl(form.avatar)" />
        <div class="profile-meta">
          <h3>{{ form.username || '未登录用户' }}</h3>
          <p>{{ roleText(form.role) }} · {{ form.email || '未设置邮箱' }}</p>
          <el-upload
            class="avatar-uploader"
            :show-file-list="false"
            :http-request="uploadAvatar"
            accept="image/*"
          >
            <el-button type="primary" plain :loading="uploading">上传头像</el-button>
          </el-upload>
        </div>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" class="profile-form">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" maxlength="32" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="个人简介" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="介绍你的职责或专长"
          />
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button type="primary" :loading="saving" @click="saveProfile">保存资料</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '../../api/common/auth'
import { useAuthStore } from '../../stores/auth'
import { getAvatarUrl } from '../../utils/avatar'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  email: '',
  role: '',
  avatar: '',
  phone: '',
  description: '',
})

const rules = {
  phone: [
    {
      validator: (_, value, callback) => {
        if (!value) {
          callback()
          return
        }
        if (!/^[0-9+\-\s]{6,32}$/.test(value)) {
          callback(new Error('手机号格式不正确'))
          return
        }
        callback()
      },
      trigger: ['blur', 'change'],
    },
  ],
}

function roleText(role) {
  if (role === 'admin') return '管理员'
  if (role === 'dispatcher') return '调度员'
  if (role === 'worker') return '工人'
  return role || '未知角色'
}

function fillForm(user) {
  form.username = user?.username || ''
  form.email = user?.email || ''
  form.role = user?.role || ''
  form.avatar = user?.avatar || ''
  form.phone = user?.phone || ''
  form.description = user?.description || ''
}

async function fetchMe() {
  loading.value = true
  try {
    const res = await authApi.getMe()
    const user = res.data?.data || {}
    fillForm(user)
    authStore.setCurrentUser(user)
  } catch {
    ElMessage.error('加载个人资料失败')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const res = await authApi.updateMe({
      phone: form.phone || null,
      description: form.description || null,
    })
    const user = res.data?.data || {}
    fillForm(user)
    authStore.setCurrentUser(user)
    ElMessage.success('个人资料已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function uploadAvatar(uploadRequest) {
  uploading.value = true
  try {
    const res = await authApi.uploadMyAvatar(uploadRequest.file)
    const user = res.data?.data || {}
    fillForm(user)
    authStore.setCurrentUser(user)
    ElMessage.success('头像上传成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  fillForm(authStore.currentUser || {})
  fetchMe()
})
</script>

<style scoped>
.profile-page {
  display: grid;
}

.profile-card {
  border-radius: 12px;
}

.profile-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.profile-meta h3 {
  margin: 0;
  font-size: 20px;
}

.profile-meta p {
  margin: 6px 0 10px;
  color: #64748b;
}

.profile-form {
  max-width: 680px;
}

.actions {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .profile-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
