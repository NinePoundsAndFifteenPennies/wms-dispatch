<template>
  <div class="dispatcher-shell">
    <aside class="dispatcher-sidebar">
      <div class="brand-block">
        <div class="brand-mark">WD</div>
        <div>
          <p class="brand-title">Dispatcher Desk</p>
          <p class="brand-subtitle">{{ shellSummary.title }}</p>
        </div>
      </div>

      <nav class="dispatcher-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: activePath === item.path }"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.count" class="nav-pill">{{ item.count }}</span>
        </router-link>
      </nav>

      <section class="sidebar-note">
        <p class="sidebar-note-label">{{ shellSummary.sidebarFootnote.label }}</p>
        <p class="sidebar-note-value">{{ shellSummary.sidebarFootnote.value }}</p>
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
            <span
              v-for="badge in shellSummary.statusBadges"
              :key="badge.key"
              class="status-badge"
              :class="`tone-${badge.tone}`"
            >
              {{ badge.label }} {{ badge.value }}
            </span>
          </div>

          <button type="button" class="profile-chip" @click="logout">
            <span class="profile-avatar">{{ shellSummary.profile.name.slice(0, 1) }}</span>
            <span>
              <strong>{{ shellSummary.profile.name }}</strong>
              <small>{{ shellSummary.profile.role }} / {{ shellSummary.profile.warehouse }}</small>
            </span>
          </button>
        </div>
      </header>

      <main class="dispatcher-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { dispatcherShellSummary } from '../mock/dispatcher'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const shellSummary = dispatcherShellSummary
const navItems = [
  { path: '/dispatcher', label: '工作台' },
  { path: '/dispatcher/orders', label: '订单中心', count: '05' },
  { path: '/dispatcher/work-orders', label: '工单中心', count: '05' },
  { path: '/dispatcher/transfers', label: '调拨请求', count: '04' },
]

const activePath = computed(() => route.path)

function logout() {
  authStore.clearToken()
  router.push('/login')
}
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
  --dispatcher-pending-bg: #f7ead6;
  --dispatcher-pending-text: #7a4a16;
  --dispatcher-active-bg: #e7eef7;
  --dispatcher-active-text: #1e4f85;
  --dispatcher-alert-bg: #f8e4e2;
  --dispatcher-alert-text: #922f2f;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
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
  backdrop-filter: blur(12px);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #2b2721;
  color: #f9f4eb;
  font-size: 13px;
  font-weight: 700;
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
  transition: all 0.2s ease;
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
  box-shadow: 0 10px 24px rgba(59, 52, 43, 0.08);
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
  line-height: 1.6;
  color: var(--dispatcher-muted);
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
  backdrop-filter: blur(10px);
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
  flex-wrap: wrap;
  justify-content: flex-end;
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
}

.tone-pending {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.tone-active {
  background: var(--dispatcher-active-bg);
  color: var(--dispatcher-active-text);
}

.tone-alert {
  background: var(--dispatcher-alert-bg);
  color: var(--dispatcher-alert-text);
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
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #d9d1c4;
  font-size: 12px;
  font-weight: 700;
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

  .dispatcher-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--dispatcher-border);
  }

  .dispatcher-nav {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .sidebar-note {
    margin-top: 0;
  }
}

@media (max-width: 720px) {
  .dispatcher-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dispatcher-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .dispatcher-content {
    padding: 14px;
  }
}
</style>
