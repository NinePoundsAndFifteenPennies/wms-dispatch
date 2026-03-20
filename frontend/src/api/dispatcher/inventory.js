import http from '../common/http'

export const dispatcherInventoryApi = {
  getInventory(params) {
    return http.get('/dispatcher/inventory', { params })
  },
}
