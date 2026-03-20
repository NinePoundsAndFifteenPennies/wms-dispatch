import { createRouter, createWebHistory } from 'vue-router'
import { publicRoutes } from './routes/public'
import { adminRoutes } from './routes/admin'
import { dispatcherRoutes } from './routes/dispatcher'
import { registerAuthGuard } from './guards/authGuard'

const router = createRouter({
  history: createWebHistory(),
  routes: [...publicRoutes, ...adminRoutes, ...dispatcherRoutes],
})

registerAuthGuard(router)

export default router
