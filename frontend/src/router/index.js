import { createRouter, createWebHistory } from 'vue-router'
import BaseLayout from '../layouts/BaseLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import OrdersView from '../views/OrdersView.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'
import LoginView from '../views/LoginView.vue'
import UsersView from '../views/UsersView.vue'
import { useAuthStore, getDefaultPathByRole } from '../stores/auth'
import http from '../api/http'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/',
    component: BaseLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
        meta: { roles: ['admin', 'dispatcher', 'worker'] },
      },
      {
        path: 'orders',
        name: 'orders',
        component: OrdersView,
        meta: { roles: ['admin', 'dispatcher'] },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: WorkOrdersView,
        meta: { roles: ['admin', 'dispatcher', 'worker'] },
      },
      {
        path: 'users',
        name: 'users',
        component: UsersView,
        meta: { roles: ['admin'] },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    if (to.name === 'login' && authStore.isAuthenticated && authStore.currentUser?.role) {
      return { path: getDefaultPathByRole(authStore.currentUser.role) }
    }
    return true
  }

  if (!authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  return http
    .get('/auth/me')
    .then((response) => {
      const user = response.data?.data
      if (!user?.is_active) {
        authStore.clearToken()
        return { name: 'login', query: { redirect: to.fullPath } }
      }

      authStore.setCurrentUser(user)

      const requiredRoles = to.meta.roles || []
      if (requiredRoles.length > 0 && !requiredRoles.includes(user.role)) {
        return { path: getDefaultPathByRole(user.role) }
      }

      return true
    })
    .catch(() => {
      authStore.clearToken()
      return { name: 'login', query: { redirect: to.fullPath } }
    })
})

export default router
