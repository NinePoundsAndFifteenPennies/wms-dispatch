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
    const responseMessage = error.response?.data?.message
    const message = responseMessage || error.message || 'Request failed'

    ElMessage.error(message)

    return Promise.reject(error)
  },
)

export default http
