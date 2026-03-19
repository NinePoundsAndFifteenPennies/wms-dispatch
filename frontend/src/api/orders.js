import http from './http'

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

  exportOrders(params) {
    return http.get('/admin/orders/export', { params })
  },

  exportOrderDetail(orderId, params) {
    return http.get(`/admin/orders/${orderId}/export`, { params })
  },
}
