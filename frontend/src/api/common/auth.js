import http from './http'

export const authApi = {
  login(data) {
    return http.post('/auth/login', data)
  },
  
  getMe() {
    return http.get('/auth/me')
  },

  updateMe(data) {
    return http.patch('/auth/me', data)
  },

  uploadMyAvatar(file) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/auth/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }
}
