<template>
  <el-container class="worker-shell">
    <el-aside class="worker-aside" width="220px">
      <div class="brand-wrap">
        <div class="brand-mark">WK</div>
        <div>
          <p class="brand-title">Worker Desk</p>
          <p class="brand-subtitle">工单执行台</p>
        </div>
      </div>

      <el-menu class="nav-menu" :default-active="activePath" router>
        <el-menu-item index="/worker/work-orders">
          <el-icon class="menu-icon"><List /></el-icon>
          我的工单
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="worker-header">
        <div>
          <p class="page-tag">Worker Console</p>
          <h2>{{ route.meta.title || '我的工单' }}</h2>
        </div>
        <div class="header-actions">
          <div class="operator">
            <el-icon><UserFilled /></el-icon>
            <div class="user-info">
              <span class="user-name">{{ authStore.currentUser?.username || '未知用户' }}</span>
              <span class="user-role">库房工人</span>
            </div>
          </div>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="worker-main">
        <section class="page-frame">
          <router-view />
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { List, UserFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activePath = computed(() => route.path)

function logout() {
  authStore.clearToken()
  router.push('/login')
}

onMounted(() => {
  if (route.query.migrated_from === 'work-orders') {
    ElMessage.info('工人入口已迁移到 /worker/work-orders，已为你自动跳转。')
    const nextQuery = { ...route.query }
    delete nextQuery.migrated_from
    router.replace({ path: route.path, query: nextQuery })
  }
})
</script>

<style scoped>
.worker-shell {
  min-height: 100vh;
  background: linear-gradient(180deg, #f7fcfb 0%, #eef4fa 100%);
}

.worker-aside {
  padding: 20px 14px;
  border-right: 1px solid #d8e1eb;
  background: #f4faf9;
}

.brand-wrap {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #1c9c89, #117264);
}

.brand-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #16202a;
}

.brand-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #64748b;
}

.nav-menu {
  border-right: none;
  background: transparent;
}

.worker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #d8e1eb;
  background: rgba(255, 255, 255, 0.92);
}

.page-tag {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.worker-header h2 {
  margin: 4px 0 0;
  font-size: 22px;
  color: #16202a;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.operator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid #d8e1eb;
  background: #fff;
}

.user-info {
  display: grid;
}

.user-name {
  font-size: 13px;
  color: #16202a;
  font-weight: 600;
}

.user-role {
  font-size: 12px;
  color: #64748b;
}

.worker-main {
  padding: 16px;
}

.page-frame {
  padding: 14px;
  border: 1px solid #d8e1eb;
  border-radius: 14px;
  background: #fff;
}

@media (max-width: 900px) {
  .worker-shell {
    display: block;
  }

  .worker-aside {
    width: 100% !important;
    border-right: none;
    border-bottom: 1px solid #d8e1eb;
  }
}
</style>
