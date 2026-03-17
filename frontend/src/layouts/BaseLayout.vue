<template>
  <el-container class="layout-shell">
    <el-aside class="layout-aside" width="248px">
      <div class="brand-wrap">
        <div class="brand-mark">WD</div>
        <div>
          <p class="brand-title">WMS Dispatch</p>
          <p class="brand-subtitle">Warehouse Console</p>
        </div>
      </div>

      <el-menu class="nav-menu" :default-active="activePath" router>
        <el-menu-item index="/">
          <el-icon class="menu-icon"><House /></el-icon>
          控制台总览
        </el-menu-item>
        <el-menu-item index="/orders">
          <el-icon class="menu-icon"><Tickets /></el-icon>
          订单中枢
        </el-menu-item>
        <el-menu-item index="/work-orders">
          <el-icon class="menu-icon"><List /></el-icon>
          工单执行
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/users">
          <el-icon class="menu-icon"><User /></el-icon>
          用户管理
        </el-menu-item>
      </el-menu>

      <div class="status-panel">
        <p>系统状态</p>
        <div class="status-chip">
          <el-icon><Connection /></el-icon>
          <span class="dot" />
          后端在线 · 8000
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div>
          <p class="page-tag">WMS Dispatch Platform</p>
          <h2>{{ pageTitle }}</h2>
        </div>
        <div class="header-actions">
          <el-button type="warning" plain>
            <el-icon><Bell /></el-icon>
            待办 6
          </el-button>
          <div class="operator">
            <el-icon><UserFilled /></el-icon>
            {{ authStore.currentUser?.username || 'UNKNOWN' }}
          </div>
          <el-button type="danger" plain @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="layout-main">
        <section class="page-frame">
          <router-view />
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Connection, House, List, Tickets, User, UserFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activePath = computed(() => route.path)

const titleMap = {
  '/': '控制台',
  '/orders': '订单管理',
  '/work-orders': '工单管理',
  '/users': '用户管理',
}

const pageTitle = computed(() => titleMap[route.path] || 'WMS Dispatch')

function logout() {
  authStore.clearToken()
  router.push('/login')
}
</script>

<style scoped>
.layout-shell {
  min-height: 100vh;
}

.layout-aside {
  position: relative;
  padding: 20px 14px;
  border-right: 1px solid var(--line-soft);
  background: linear-gradient(180deg, #f9fcff 0%, #eef4fa 100%);
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
  background: linear-gradient(135deg, var(--brand), var(--brand-deep));
}

.brand-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--ink-strong);
}

.brand-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--ink-muted);
}

.nav-menu {
  border-right: none;
  background: transparent;
}

:deep(.el-menu-item) {
  margin-bottom: 6px;
  border-radius: 10px;
}

.menu-icon {
  margin-right: 8px;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(28, 156, 137, 0.16), rgba(28, 156, 137, 0.08));
  color: var(--brand-deep);
  font-weight: 700;
}

.status-panel {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 20px;
  padding: 14px;
  border: 1px solid #d4dde8;
  border-radius: 14px;
  background: #ffffff;
}

.status-panel p {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--ink-muted);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-normal);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #18a86a;
  box-shadow: 0 0 0 4px rgba(24, 168, 106, 0.16);
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(4px);
}

.layout-header h2 {
  margin: 0;
  font-size: 24px;
  color: var(--ink-strong);
}

.page-tag {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-muted);
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.operator {
  min-width: 82px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  text-align: center;
  border-radius: 10px;
  font-weight: 700;
  font-size: 12px;
  color: var(--ink-strong);
  background: #fff3e7;
}

.layout-main {
  padding: 20px;
}

.page-frame {
  min-height: calc(100vh - 100px);
  border: 1px solid #d8e0ea;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fc 100%);
  box-shadow: 0 8px 30px rgba(42, 55, 71, 0.08);
}
</style>
