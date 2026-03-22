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

    cancelMyOrder(orderId, payload) {
      return http.post(`/dispatcher/my-orders/${orderId}/cancel`, payload)
    },

  getDashboardSummary() {
    return http.get('/dispatcher/dashboard-summary')
  },

  getWorkers(params) {
    return http.get('/dispatcher/workers', { params })
  },

  getOrderWorkOrders(orderId, params) {
    return http.get(`/dispatcher/orders/${orderId}/work-orders`, { params })
  },

  createWorkOrder(orderId, payload) {
    return http.post(`/dispatcher/orders/${orderId}/work-orders`, payload)
  },

  precheckWorkOrder(orderId, payload) {
    return http.post(`/dispatcher/orders/${orderId}/work-orders/precheck`, payload)
  },

  terminateWorkOrder(workOrderId, payload) {
    return http.patch(`/dispatcher/work-orders/${workOrderId}/terminate`, payload)
  },

  manualCompleteStage(orderId, stageId, payload) {
    return http.post(`/dispatcher/orders/${orderId}/stages/${stageId}/complete`, payload)
  },
}
