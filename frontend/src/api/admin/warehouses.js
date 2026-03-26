import http from '../common/http'

export const warehousesApi = {
  getWarehouseOptions() {
    return http.get('/admin/warehouses/options')
  },

  getWarehouses(params) {
    return http.get('/admin/warehouses/manage', { params })
  },

  createWarehouse(data) {
    return http.post('/admin/warehouses', data)
  },

  updateWarehouse(id, data) {
    return http.put(`/admin/warehouses/${id}`, data)
  },

  deleteWarehouse(id) {
    return http.delete(`/admin/warehouses/${id}`)
  },

  updateWarehouseStatus(id, isActive) {
    return http.patch(`/admin/warehouses/${id}/status`, { is_active: isActive })
  },

  batchDeleteWarehouses(ids) {
    return http.post('/admin/warehouses/batch-delete', { ids })
  },

  uploadWarehouseImage(warehouseId, file) {
    const formData = new FormData()
    formData.append('image', file)
    return http.post(`/admin/warehouses/${warehouseId}/image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  removeWarehouseImage(warehouseId) {
    return http.delete(`/admin/warehouses/${warehouseId}/image`)
  },

  getWarehouseInventory(warehouseId, params) {
    return http.get(`/admin/warehouses/${warehouseId}/inventory`, { params })
  },

  getInventoryFlowTrends(params) {
    return http.get('/admin/warehouses/inventory-movements/trends', { params })
  },

  getWarehouseInventoryFlowNodeDetails(warehouseId, params) {
    return http.get(`/admin/warehouses/${warehouseId}/inventory-movements/node-details`, { params })
  },

  adjustWarehouseInventoryStocktake(warehouseId, inventoryId, data) {
    return http.patch(`/admin/warehouses/${warehouseId}/inventory/${inventoryId}/stocktake`, {
      qty_on_hand: data.qty_on_hand,
      qty_threshold: data.qty_threshold,
      reason: data.reason,
    })
  },

  warehouseInventoryInbound(warehouseId, data) {
    return http.post(`/admin/warehouses/${warehouseId}/inventory/inbound`, {
      product_id: data.product_id,
      qty: data.qty,
      reason: data.reason,
    })
  },
}
