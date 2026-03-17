import { createRouter, createWebHistory } from 'vue-router'
import BaseLayout from '../layouts/BaseLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import OrdersView from '../views/OrdersView.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'
import LoginView from '../views/LoginView.vue'
import UsersView from '../views/UsersView.vue'
import CustomersView from '../views/CustomersView.vue'
import ProductsView from '../views/ProductsView.vue'
import { useAuthStore, getDefaultPathByRole, isTokenExpired } from '../stores/auth'
import { authApi } from '../api/auth'

function handleDisabledUser(authStore, redirectPath) {
  authStore.clearToken()
  return { name: 'login', query: { redirect: redirectPath } }
}

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
      {
        path: 'customers',
        name: 'customers',
        component: CustomersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'products',
        name: 'products',
        component: ProductsView,
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

  if (authStore.isAuthenticated && isTokenExpired(authStore.token)) {
    authStore.clearToken()
    if (!to.meta.public) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.public) {
    if (to.name === 'login' && authStore.isAuthenticated && authStore.currentUser?.role) {
      return { path: getDefaultPathByRole(authStore.currentUser.role) }
    }
    return true
  }

  if (!authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const requiredRoles = to.meta.roles || []
  if (authStore.profileLoaded && authStore.currentUser) {
    if (!authStore.currentUser.is_active) {
      return handleDisabledUser(authStore, to.fullPath)
    }
    if (requiredRoles.length > 0 && !requiredRoles.includes(authStore.currentUser.role)) {
      return { path: getDefaultPathByRole(authStore.currentUser.role) }
    }
    return true
  }

  return authApi
    .getMe()
    .then((response) => {
      const user = response.data?.data
      if (!user?.is_active) {
        return handleDisabledUser(authStore, to.fullPath)
      }

      authStore.setCurrentUser(user)

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
