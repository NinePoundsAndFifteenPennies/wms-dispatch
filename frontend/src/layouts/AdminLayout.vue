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
        <el-menu-item v-if="authStore.hasRole('admin')" index="/">
          <el-icon class="menu-icon"><House /></el-icon>
          控制台总览
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/orders">
          <el-icon class="menu-icon"><Tickets /></el-icon>
          订单中枢
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/work-orders">
          <el-icon class="menu-icon"><List /></el-icon>
          工单执行
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/users">
          <el-icon class="menu-icon"><User /></el-icon>
          用户管理
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/warehouses">
          <el-icon class="menu-icon"><OfficeBuilding /></el-icon>
          仓库管理
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/flow-records">
          <el-icon class="menu-icon"><TrendCharts /></el-icon>
          流水记录
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/customers">
          <el-icon class="menu-icon"><User /></el-icon>
          客户管理
        </el-menu-item>
        <el-menu-item v-if="authStore.hasRole('admin')" index="/products">
          <el-icon class="menu-icon"><Goods /></el-icon>
          产品管理
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
          <el-badge :value="unreadCount" :hidden="unreadCount <= 0" :max="99">
            <el-button type="warning" class="action-btn" plain @click="openNotificationDrawer">
              <el-icon><Bell /></el-icon>
              待办
            </el-button>
          </el-badge>
          
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="operator">
              <img class="operator-avatar" :src="profileAvatarUrl" alt="当前用户头像" />
              <div class="user-info">
                <span class="user-name">{{ authStore.currentUser?.username || '未知用户' }}</span>
                <span class="user-role">{{ formatRole(authStore.currentUser?.role) }}</span>
              </div>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item divided command="logout" class="text-danger">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main">
        <section class="page-frame">
          <router-view />
        </section>
      </el-main>
    </el-container>

    <el-drawer
      v-model="notificationDrawerVisible"
      title="异常通知"
      size="420px"
      @open="fetchNotifications"
    >
      <div class="notification-toolbar">
        <span>未读 {{ unreadCount }}</span>
        <div class="notification-actions">
          <el-radio-group v-model="notificationReadFilter" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="unread">仅未读</el-radio-button>
            <el-radio-button label="read">仅已读</el-radio-button>
          </el-radio-group>
          <el-button link type="primary" :disabled="unreadCount <= 0" @click="markAllNotificationsRead">全部标记已读</el-button>
        </div>
      </div>

      <div v-loading="notificationLoading" class="notification-list">
        <template v-if="filteredNotificationItems.length > 0">
          <article
            v-for="item in filteredNotificationItems"
            :key="item.id"
            class="notification-item"
            :class="{ unread: !item.is_read }"
            @click="markNotificationRead(item)"
          >
            <div class="notification-head">
              <strong>{{ item.title }}</strong>
              <small>{{ formatNotificationTime(item.created_at) }}</small>
            </div>
            <p>{{ item.body || '无详情' }}</p>
          </article>
        </template>
        <el-empty v-else :description="notificationEmptyText" :image-size="96" />
      </div>
    </el-drawer>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Bell, Connection, Goods, House, List, OfficeBuilding, Tickets, TrendCharts, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import http from '../api/common/http'
import { notificationsApi } from '../api/common/notifications'
import { createNotificationSocket } from '../api/common/notificationSocket'
import { getAvatarUrl } from '../utils/avatar'

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
  '/warehouses': '仓库管理',
  '/flow-records': '流水记录',
  '/customers': '客户管理',
  '/products': '产品管理',
}

const pageTitle = computed(() => {
  if (route.path.startsWith('/warehouses/') && route.path.endsWith('/inventory')) {
    const warehouseName = typeof route.query.name === 'string' ? route.query.name.trim() : ''
    return warehouseName || '仓库库存详情'
  }
  return titleMap[route.path] || 'WMS Dispatch'
})
const backendStatus = ref('checking')
let statusTimer = null
let notificationSocket = null
let notificationReconnectTimer = null
let notificationReconnectAttempts = 0
const notificationDrawerVisible = ref(false)
const notificationLoading = ref(false)
const notificationItems = ref([])
const unreadCount = ref(0)
const notificationReadFilter = ref('all')

const filteredNotificationItems = computed(() => {
  if (notificationReadFilter.value === 'unread') {
    return notificationItems.value.filter((item) => !item.is_read)
  }
  if (notificationReadFilter.value === 'read') {
    return notificationItems.value.filter((item) => item.is_read)
  }
  return notificationItems.value
})

const notificationEmptyText = computed(() => {
  if (notificationReadFilter.value === 'unread') return '暂无未读通知'
  if (notificationReadFilter.value === 'read') return '暂无已读通知'
  return '暂无异常通知'
})

const backendStatusText = computed(() => {
  if (backendStatus.value === 'online') return '后端在线'
  if (backendStatus.value === 'offline') return '后端离线 · 无法访问'
  return '状态检测中...'
})

const profileAvatarUrl = computed(() => getAvatarUrl(authStore.currentUser?.avatar))

const statusClass = computed(() => ({
  'status-online': backendStatus.value === 'online',
  'status-offline': backendStatus.value === 'offline',
}))

function formatRole(role) {
  const roles = {
    admin: '系统管理员',
    dispatcher: '调度员',
    worker: '库房工人'
  }
  return roles[role] || role || '未知角色'
}

function handleCommand(command) {
  if (command === 'logout') {
    logout()
  } else if (command === 'profile') {
    router.push('/profile')
  }
}

function logout() {
  authStore.clearToken()
  router.push('/login')
}

function openNotificationDrawer() {
  notificationDrawerVisible.value = true
  fetchNotifications()
}

async function fetchNotifications() {
  notificationLoading.value = true
  try {
    const res = await notificationsApi.listMyNotifications({ limit: 80 })
    const data = res.data?.data || {}
    notificationItems.value = data.items || []
    unreadCount.value = Number(data.unread_count || 0)
  } catch {
    notificationItems.value = []
    unreadCount.value = 0
  } finally {
    notificationLoading.value = false
  }
}

async function markNotificationRead(item) {
  if (!item || item.is_read) return
  try {
    await notificationsApi.markNotificationRead(item.id)
    item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch {
    // no-op, global interceptor already handles toast
  }
}

async function markAllNotificationsRead() {
  try {
    await notificationsApi.markAllNotificationsRead()
    notificationItems.value = notificationItems.value.map((item) => ({ ...item, is_read: true }))
    unreadCount.value = 0
  } catch {
    // no-op, global interceptor already handles toast
  }
}

function formatNotificationTime(value) {
  if (!value) return '-'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '-'
  return dt.toLocaleString('zh-CN', { hour12: false })
}

function closeNotificationSocket() {
  if (notificationReconnectTimer) {
    window.clearTimeout(notificationReconnectTimer)
    notificationReconnectTimer = null
  }
  notificationReconnectAttempts = 0
  if (notificationSocket) {
    notificationSocket.close()
    notificationSocket = null
  }
}

function connectNotificationSocket() {
  closeNotificationSocket()
  notificationSocket = createNotificationSocket({
    token: authStore.token,
    onState(payload) {
      unreadCount.value = Number(payload.unread_count || 0)
      if (notificationDrawerVisible.value) {
        fetchNotifications()
      }
    },
    onClose() {
      if (!authStore.token) return
      notificationReconnectAttempts += 1
      if (notificationReconnectAttempts > 10) return
      const delay = Math.min(2500 * notificationReconnectAttempts, 15000)
      notificationReconnectTimer = window.setTimeout(connectNotificationSocket, delay)
    },
    onOpen() {
      notificationReconnectAttempts = 0
    },
  })
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
  fetchNotifications()
  connectNotificationSocket()
})

onUnmounted(() => {
  if (statusTimer) {
    window.clearTimeout(statusTimer)
  }
  closeNotificationSocket()
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 12px;
  text-align: left;
  border-radius: 10px;
  border: 1px solid #d8e0ea;
  background: #fdfdfd;
  cursor: pointer;
  transition: all 0.2s;
}

.operator:hover {
  background: #f7f9fc;
  border-color: #c5d0dc;
}

.operator-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}

.user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.user-name {
  font-weight: 700;
  font-size: 13px;
  color: var(--ink-strong);
}

.user-role {
  font-size: 11px;
  color: var(--ink-muted);
}

.text-danger {
  color: #e05353;
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

.notification-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--ink-muted);
  font-size: 12px;
}

.notification-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.notification-list {
  display: grid;
  gap: 10px;
}

.notification-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbff;
  cursor: pointer;
}

.notification-item.unread {
  border-color: #f3c67a;
  background: #fff9ef;
}

.notification-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.notification-head small {
  color: #64748b;
}

.notification-item p {
  margin: 6px 0 0;
  color: #475569;
  font-size: 13px;
}
</style>
