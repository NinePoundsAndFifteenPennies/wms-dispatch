import http from './http'

export const authApi = {
  login(data) {
    return http.post('/auth/login', data)
  },
  
  getMe() {
    return http.get('/auth/me')
  }
}
