import http from '../common/http'

export const adminDashboardApi = {
  getOverview() {
    return http.get('/admin/dashboard-overview')
  },

  getWarehouseDispatcherPerformance(warehouseId) {
    return http.get(`/admin/dashboard-overview/warehouse-performance/${warehouseId}`)
  },
}
