import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getAuthToken } from '../../stores/auth'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

http.interceptors.request.use((config) => {
  const token = getAuthToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.config?.silentError) {
      return Promise.reject(error)
    }

    const responseMessage = error.response?.data?.message
    const isTimeout = error?.code === 'ECONNABORTED' || /timeout/i.test(error?.message || '')
    const message = responseMessage || (isTimeout ? '请求超时，请稍后重试' : (error.message || '请求失败'))

    ElMessage.error(message)

    return Promise.reject(error)
  },
)

export default http
