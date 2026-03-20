import http from '../common/http'

export const ordersApi = {
  getOrders(params) {
    return http.get('/admin/orders', { params })
  },

  getOrderDetail(orderId) {
    return http.get(`/admin/orders/${orderId}`)
  },

  createOrder(data) {
    return http.post('/admin/orders', data)
  },

  updatePendingOrder(orderId, data) {
    return http.patch(`/admin/orders/${orderId}/pending`, data)
  },

  cancelPendingOrder(orderId, data) {
    return http.post(`/admin/orders/${orderId}/cancel`, data)
  },

  reopenCancelledOrder(orderId) {
    return http.post(`/admin/orders/${orderId}/reopen`)
  },

  exportOrders(params) {
    return http.get('/admin/orders/export', { params })
  },

  exportOrderDetail(orderId, params) {
    return http.get(`/admin/orders/${orderId}/export`, { params })
  },
}
