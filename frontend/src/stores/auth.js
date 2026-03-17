import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_KEY = 'wms_dispatch_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')

  const isAuthenticated = computed(() => Boolean(token.value))

  function setToken(value) {
    token.value = value
    localStorage.setItem(TOKEN_KEY, value)
  }

  function clearToken() {
    token.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  return {
    token,
    isAuthenticated,
    setToken,
    clearToken,
  }
})

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
