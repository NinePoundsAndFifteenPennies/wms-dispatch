import http from '../common/http'

export const adminWorkOrdersApi = {
  getWorkOrders(params) {
    return http.get('/admin/work-orders', { params })
  },
}
