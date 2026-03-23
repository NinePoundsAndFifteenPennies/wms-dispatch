import http from '../common/http'

export const productsApi = {
  getProducts(params) {
    return http.get('/admin/products', { params })
  },

  getProductById(id) {
    return http.get(`/admin/products/${id}`)
  },

  createProduct(data) {
    return http.post('/admin/products', data)
  },

  updateProduct(id, data) {
    return http.put(`/admin/products/${id}`, data)
  },

  deleteProduct(id) {
    return http.delete(`/admin/products/${id}`)
  },

  updateProductStatus(id, isActive) {
    return http.patch(`/admin/products/${id}/status`, { is_active: isActive })
  },

  batchDeleteProducts(ids) {
    return http.post('/admin/products/batch-delete', { ids })
  },

  uploadProductImage(productId, file) {
    const formData = new FormData()
    formData.append('image', file)
    return http.post(`/admin/products/${productId}/image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  removeProductImage(productId) {
    return http.delete(`/admin/products/${productId}/image`)
  },
}
