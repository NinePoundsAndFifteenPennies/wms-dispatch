import http from './http'

export const customersApi = {
  getCustomers(params) {
    return http.get('/admin/customers', { params })
  },

  createCustomer(data) {
    return http.post('/admin/customers', data)
  },

  updateCustomer(id, data) {
    return http.put(`/admin/customers/${id}`, data)
  },

  deleteCustomer(id) {
    return http.delete(`/admin/customers/${id}`)
  },

  updateCustomerStatus(id, isActive) {
    return http.patch(`/admin/customers/${id}/status`, { is_active: isActive })
  },

  batchDeleteCustomers(ids) {
    return http.post('/admin/customers/batch-delete', { ids })
  },
}
