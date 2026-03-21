import http from '../common/http'

export const workerWorkOrdersApi = {
  getMyWorkOrders(params) {
    return http.get('/worker/work-orders', { params })
  },

  startWorkOrder(workOrderId) {
    return http.patch(`/worker/work-orders/${workOrderId}/start`)
  },

  completeWorkOrder(workOrderId, payload) {
    return http.patch(`/worker/work-orders/${workOrderId}/complete`, payload)
  },
}
