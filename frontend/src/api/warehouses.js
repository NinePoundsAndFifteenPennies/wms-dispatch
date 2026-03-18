import http from './http'

export const warehousesApi = {
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

  adjustWarehouseInventoryStocktake(warehouseId, inventoryId, qtyOnHand) {
    return http.patch(`/admin/warehouses/${warehouseId}/inventory/${inventoryId}/stocktake`, {
      qty_on_hand: qtyOnHand,
    })
  },
}
