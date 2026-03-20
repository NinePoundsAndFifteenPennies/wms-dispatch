import { authApi } from '../../api/common/auth'
import { useAuthStore, getDefaultPathByRole, isTokenExpired } from '../../stores/auth'

function handleDisabledUser(authStore, redirectPath) {
  authStore.clearToken()
  return { name: 'login', query: { redirect: redirectPath } }
}

export function registerAuthGuard(router) {
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
}
