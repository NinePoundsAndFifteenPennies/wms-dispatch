<template>
  <div class="dispatcher-shell">
    <aside class="dispatcher-sidebar">
      <div class="brand-block">
        <img class="brand-mark" src="../assets/images/warehouse-badge.svg" alt="WMS Dispatcher 仓库标识" />
        <div>
          <p class="brand-title">Dispatcher Desk</p>
          <p class="brand-subtitle">{{ warehouseTitle }}</p>
        </div>
      </div>

      <nav class="dispatcher-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: isNavActive(item.path) }"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.count !== undefined" class="nav-pill">{{ item.count }}</span>
        </router-link>
      </nav>

      <section class="sidebar-note">
        <p class="sidebar-note-label">系统状态</p>
        <p class="sidebar-note-value" :class="statusClass">{{ backendStatusText }}</p>
      </section>
    </aside>

    <section class="dispatcher-main">
      <header class="dispatcher-topbar">
        <div>
          <p class="topbar-kicker">Dispatcher Console</p>
          <h1>{{ route.meta.title || '工作台' }}</h1>
        </div>

        <div class="topbar-actions">
          <div class="badge-group">
            <button
              v-for="badge in dispatcherStore.statusBadges"
              :key="badge.key"
              type="button"
              class="status-badge"
              :class="`tone-${badge.tone}`"
              @click="goByBadge(badge.key)"
            >
              {{ badge.label }} {{ badge.value }}
            </button>
          </div>

          <el-dropdown trigger="click" @command="handleCommand">
            <button type="button" class="profile-chip">
              <img class="profile-avatar" :src="profileAvatarUrl" alt="调度员头像" />
              <span>
                <strong>{{ profileName }}</strong>
                <small>调度员 / {{ warehouseTitle }}</small>
              </span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="dispatcher-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/common/http'
import { useAuthStore } from '../stores/auth'
import { useDispatcherStore } from '../stores/dispatcher'
import { getAvatarUrl } from '../utils/avatar'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const dispatcherStore = useDispatcherStore()

const HEALTH_CHECK_INTERVAL_MS = 10000
const HEALTH_CHECK_OFFLINE_INTERVAL_MS = 30000
const backendStatus = ref('checking')
let statusTimer = null

const activePath = computed(() => route.path)
const warehouseTitle = computed(() => dispatcherStore.summary.warehouse_name || '仓库未绑定')

function isNavActive(navPath) {
  if (navPath === '/dispatcher') return activePath.value === '/dispatcher'
  return activePath.value === navPath || activePath.value.startsWith(navPath + '/')
}
const profileName = computed(() => authStore.currentUser?.username || '未知用户')
const profileAvatarUrl = computed(() => getAvatarUrl(authStore.currentUser?.avatar))

const backendStatusText = computed(() => {
  if (backendStatus.value === 'online') return '后端在线'
  if (backendStatus.value === 'offline') return '后端离线 · 无法访问'
  return '状态检测中...'
})

const statusClass = computed(() =>
  backendStatus.value === 'online' ? 'status-online' : backendStatus.value === 'offline' ? 'status-offline' : ''
)

const navItems = computed(() => [
  { path: '/dispatcher', label: '工作台' },
  { path: '/dispatcher/orders', label: '接单中心', count: dispatcherStore.summary.pending_count },
  { path: '/dispatcher/my-orders', label: '我的订单', count: dispatcherStore.summary.my_orders_count },
  { path: '/dispatcher/inventory', label: '库存中心' },
  { path: '/dispatcher/flow-records', label: '流水记录' },
  { path: '/dispatcher/work-orders', label: '工单中心' },
  { path: '/dispatcher/transfers', label: '调拨请求' },
])

function logout() {
  authStore.clearToken()
  router.push('/login')
}

function handleCommand(command) {
  if (command === 'logout') {
    logout()
    return
  }
  if (command === 'profile') {
    router.push('/dispatcher/profile')
  }
}

function goByBadge(key) {
  if (key === 'pending') {
    router.push('/dispatcher/orders')
    return
  }
  if (key === 'active') {
    router.push({ path: '/dispatcher/my-orders', query: { status: 'in_progress' } })
    return
  }
  if (key === 'done') {
    router.push({ path: '/dispatcher/my-orders', query: { status: 'completed' } })
  }
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
  if (statusTimer) clearTimeout(statusTimer)
  statusTimer = setTimeout(
    checkBackendStatus,
    backendStatus.value === 'offline' ? HEALTH_CHECK_OFFLINE_INTERVAL_MS : HEALTH_CHECK_INTERVAL_MS
  )
}

onMounted(async () => {
  await dispatcherStore.refreshSummary()
  checkBackendStatus()
})

watch(
  () => route.path,
  () => {
    dispatcherStore.refreshSummary().catch(() => {})
  }
)

onUnmounted(() => {
  if (statusTimer) clearTimeout(statusTimer)
})
</script>

<style scoped>
.dispatcher-shell {
  --dispatcher-bg: #f3f0e8;
  --dispatcher-panel: #f7f4ee;
  --dispatcher-surface: #fffdf9;
  --dispatcher-border: #d6d0c4;
  --dispatcher-border-strong: #bfb6a6;
  --dispatcher-text: #26221c;
  --dispatcher-muted: #6f675a;
  --dispatcher-soft: #8e8578;
  --dispatcher-pending-bg: #fbe9cf;
  --dispatcher-pending-text: #9a5b18;
  --dispatcher-active-bg: #e2eefc;
  --dispatcher-active-text: #1f5c9a;
  --dispatcher-done-bg: #e2f5e8;
  --dispatcher-done-text: #2c7a4b;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  background:
    radial-gradient(circle at 0 0, rgba(178, 150, 96, 0.08) 0%, transparent 18%),
    linear-gradient(180deg, #f6f3ec 0%, #ede8de 100%);
  color: var(--dispatcher-text);
}

.dispatcher-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 14px;
  border-right: 1px solid var(--dispatcher-border);
  background: rgba(250, 247, 241, 0.92);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  object-fit: cover;
  box-shadow: 0 6px 18px rgba(43, 39, 33, 0.22);
}

.brand-title,
.brand-subtitle {
  margin: 0;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: var(--dispatcher-muted);
}

.dispatcher-nav {
  display: grid;
  gap: 6px;
}

.nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: var(--dispatcher-muted);
  text-decoration: none;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.72);
  border-color: var(--dispatcher-border);
}

.nav-link.active {
  background: var(--dispatcher-surface);
  border-color: var(--dispatcher-border-strong);
  color: var(--dispatcher-text);
  font-weight: 700;
}

.nav-pill {
  min-width: 28px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #ebe4d7;
  color: var(--dispatcher-soft);
  font-size: 11px;
  text-align: center;
}

.sidebar-note {
  margin-top: auto;
  padding: 14px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 14px;
  background: rgba(255, 253, 249, 0.9);
}

.sidebar-note-label,
.sidebar-note-value {
  margin: 0;
}

.sidebar-note-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.sidebar-note-value {
  margin-top: 8px;
  font-size: 12px;
  color: var(--dispatcher-muted);
}

.status-online {
  color: #2c7a4b;
}

.status-offline {
  color: #a0473f;
}

.dispatcher-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.dispatcher-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--dispatcher-border);
  background: rgba(247, 244, 238, 0.9);
}

.topbar-kicker,
.dispatcher-topbar h1 {
  margin: 0;
}

.topbar-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.dispatcher-topbar h1 {
  margin-top: 4px;
  font-size: 22px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-badge {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.tone-pending {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.tone-active {
  background: var(--dispatcher-active-bg);
  color: var(--dispatcher-active-text);
}

.tone-done {
  background: var(--dispatcher-done-bg);
  color: var(--dispatcher-done-text);
}

.profile-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 12px;
  background: var(--dispatcher-surface);
  color: inherit;
  cursor: pointer;
}

.profile-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
}

.profile-chip strong,
.profile-chip small {
  display: block;
  text-align: left;
}

.profile-chip small {
  margin-top: 3px;
  color: var(--dispatcher-muted);
}

.dispatcher-content {
  flex: 1;
  min-width: 0;
  padding: 18px;
}

@media (max-width: 980px) {
  .dispatcher-shell {
    grid-template-columns: 1fr;
  }
}
</style>
