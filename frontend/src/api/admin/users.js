import http from '../common/http'

export const usersApi = {
  getUsers(params) {
    return http.get('/admin/users', { params })
  },
  
  createUser(data) {
    return http.post('/admin/users', data)
  },
  
  updateUser(id, data) {
    return http.put(`/admin/users/${id}`, data)
  },
  
  updateUserStatus(id, isActive) {
    return http.patch(`/admin/users/${id}/status`, { is_active: isActive })
  },

  batchDisableUsers(ids) {
    return http.post('/admin/users/batch-disable', { ids })
  },

  getWarehouses() {
    return http.get('/admin/warehouses')
  }
}
