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
        <div class="status-chip" :class="statusClass">
          <el-icon><Connection /></el-icon>
          <span class="dot" />
          {{ backendStatusText }}
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
          <el-button type="warning" class="action-btn" plain>
            <el-icon><Bell /></el-icon>
            待办 6
          </el-button>
          <div class="operator">
            <el-icon><UserFilled /></el-icon>
            {{ authStore.currentUser?.username || 'UNKNOWN' }}
          </div>
          <el-button type="danger" class="action-btn" plain @click="logout">退出</el-button>
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
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Connection, House, List, Tickets, User, UserFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const HEALTH_CHECK_INTERVAL = 10000
const HEALTH_CHECK_OFFLINE_INTERVAL = 30000

const activePath = computed(() => route.path)

const titleMap = {
  '/': '控制台',
  '/orders': '订单管理',
  '/work-orders': '工单管理',
  '/users': '用户管理',
}

const pageTitle = computed(() => titleMap[route.path] || 'WMS Dispatch')
const backendStatus = ref('checking')
let statusTimer = null

const backendStatusText = computed(() => {
  if (backendStatus.value === 'online') return '后端在线'
  if (backendStatus.value === 'offline') return '后端离线 · 无法访问'
  return '状态检测中...'
})

const statusClass = computed(() => ({
  'status-online': backendStatus.value === 'online',
  'status-offline': backendStatus.value === 'offline',
}))

function logout() {
  authStore.clearToken()
  router.push('/login')
}

async function checkBackendStatus() {
  try {
    const response = await http.get('/health')
    backendStatus.value = response.data?.data?.status === 'ok' ? 'online' : 'offline'
  } catch {
    backendStatus.value = 'offline'
  } finally {
    scheduleNextHealthCheck()
  }
}

function scheduleNextHealthCheck() {
  if (statusTimer) {
    window.clearTimeout(statusTimer)
  }
  const nextInterval =
    backendStatus.value === 'offline' ? HEALTH_CHECK_OFFLINE_INTERVAL : HEALTH_CHECK_INTERVAL
  statusTimer = window.setTimeout(checkBackendStatus, nextInterval)
}

onMounted(() => {
  checkBackendStatus()
})

onUnmounted(() => {
  if (statusTimer) {
    window.clearTimeout(statusTimer)
  }
})
</script>

<style scoped>
.layout-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at 88% 8%, rgba(242, 153, 74, 0.16) 0%, transparent 32%),
    radial-gradient(circle at 10% 2%, rgba(28, 156, 137, 0.16) 0%, transparent 38%);
}

.layout-aside {
  position: relative;
  padding: 20px 14px;
  border-right: 1px solid var(--line-soft);
  background: linear-gradient(180deg, #f7fcfb 0%, #eef4fa 100%);
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
  box-shadow: 0 6px 18px rgba(17, 114, 100, 0.26);
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
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #d6e8e1;
  background: #f2fbf8;
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

.status-offline {
  border-color: #f1d2d2;
  background: #fff4f4;
}

.status-offline .dot {
  background: #e05353;
  box-shadow: 0 0 0 4px rgba(224, 83, 83, 0.16);
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
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

.action-btn {
  border-radius: 10px;
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
  border: 1px solid #f8d7b4;
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
  background: linear-gradient(180deg, #fcffff 0%, #f5f9fd 100%);
  box-shadow: 0 12px 34px rgba(42, 55, 71, 0.08);
}
</style>
