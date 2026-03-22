import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_KEY = 'wms_dispatch_token'
const USER_KEY = 'wms_dispatch_user'

function parseStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const currentUser = ref(parseStoredUser())
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
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
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

function decodeJwtPayload(token) {
  const parts = token.split('.')
  if (parts.length < 2) return null

  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

export function isTokenExpired(token = getAuthToken()) {
  if (!token) return true

  const payload = decodeJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') {
    return true
  }

  return Date.now() >= payload.exp * 1000
}

export function getDefaultPathByRole(role) {
  if (role === 'admin') {
    return '/users'
  }
  if (role === 'dispatcher') {
    return '/dispatcher'
  }
  return '/worker/work-orders'
}
