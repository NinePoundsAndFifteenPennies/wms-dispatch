import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_KEY = 'wms_dispatch_token'
const USER_KEY = 'wms_dispatch_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const currentUser = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  const profileLoaded = ref(Boolean(currentUser.value))

  const isAuthenticated = computed(() => Boolean(token.value))

  function setSession(value, user = null) {
    token.value = value
    localStorage.setItem(TOKEN_KEY, value)
    if (user) {
      currentUser.value = user
      profileLoaded.value = true
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    }
  }

  function clearToken() {
    token.value = ''
    currentUser.value = null
    profileLoaded.value = false
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  function setCurrentUser(user) {
    currentUser.value = user
    profileLoaded.value = true
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }

  function hasRole(...roles) {
    return Boolean(currentUser.value && roles.includes(currentUser.value.role))
  }

  return {
    token,
    currentUser,
    profileLoaded,
    isAuthenticated,
    setSession,
    setCurrentUser,
    hasRole,
    clearToken,
  }
})

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getDefaultPathByRole(role) {
  if (role === 'admin') {
    return '/users'
  }
  if (role === 'dispatcher') {
    return '/orders'
  }
  return '/work-orders'
}
