import { createRouter, createWebHistory } from 'vue-router'
import BaseLayout from '../layouts/BaseLayout.vue'
import DispatcherLayout from '../layouts/DispatcherLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import OrdersView from '../views/OrdersView.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'
import LoginView from '../views/LoginView.vue'
import UsersView from '../views/UsersView.vue'
import CustomersView from '../views/CustomersView.vue'
import ProductsView from '../views/ProductsView.vue'
import WarehousesView from '../views/WarehousesView.vue'
import WarehouseInventoryView from '../views/WarehouseInventoryView.vue'
import DispatcherWorkbenchView from '../views/dispatcher/DispatcherWorkbenchView.vue'
import DispatcherOrdersView from '../views/dispatcher/DispatcherOrdersView.vue'
import DispatcherWorkOrdersView from '../views/dispatcher/DispatcherWorkOrdersView.vue'
import DispatcherTransfersView from '../views/dispatcher/DispatcherTransfersView.vue'
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
        meta: { roles: ['admin', 'worker'] },
      },
      {
        path: 'orders',
        name: 'orders',
        component: OrdersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: WorkOrdersView,
        meta: { roles: ['admin', 'worker'] },
      },
      {
        path: 'users',
        name: 'users',
        component: UsersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'warehouses',
        name: 'warehouses',
        component: WarehousesView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'warehouses/:id/inventory',
        name: 'warehouse-inventory',
        component: WarehouseInventoryView,
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
  {
    path: '/dispatcher',
    component: DispatcherLayout,
    children: [
      {
        path: '',
        name: 'dispatcher-workbench',
        component: DispatcherWorkbenchView,
        meta: { roles: ['dispatcher'], title: '工作台' },
      },
      {
        path: 'orders',
        name: 'dispatcher-orders',
        component: DispatcherOrdersView,
        meta: { roles: ['dispatcher'], title: '订单中心' },
      },
      {
        path: 'work-orders',
        name: 'dispatcher-work-orders',
        component: DispatcherWorkOrdersView,
        meta: { roles: ['dispatcher'], title: '工单中心' },
      },
      {
        path: 'transfers',
        name: 'dispatcher-transfers',
        component: DispatcherTransfersView,
        meta: { roles: ['dispatcher'], title: '调拨请求' },
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
