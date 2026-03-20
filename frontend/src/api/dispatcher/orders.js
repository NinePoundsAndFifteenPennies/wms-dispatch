import http from '../common/http'

export const dispatcherOrdersApi = {
  getPendingOrders(params) {
    return http.get('/dispatcher/orders', { params })
  },

  getPendingOrderDetail(orderId) {
    return http.get(`/dispatcher/orders/${orderId}`)
  },

  acceptOrder(orderId, config = {}) {
    return http.post(`/dispatcher/orders/${orderId}/accept`, undefined, config)
  },

  getMyOrders(params) {
    return http.get('/dispatcher/my-orders', { params })
  },

  getMyOrderDetail(orderId) {
    return http.get(`/dispatcher/my-orders/${orderId}`)
  },

  getDashboardSummary() {
    return http.get('/dispatcher/dashboard-summary')
  },
}
