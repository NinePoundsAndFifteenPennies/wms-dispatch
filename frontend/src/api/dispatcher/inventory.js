import http from '../common/http'

export const dispatcherInventoryApi = {
  getInventory(params) {
    return http.get('/dispatcher/inventory', { params })
  },

  getFlowTrend(params) {
    return http.get('/dispatcher/inventory-movements/trend', { params })
  },

  getFlowNodeDetails(params) {
    return http.get('/dispatcher/inventory-movements/node-details', { params })
  },
}
