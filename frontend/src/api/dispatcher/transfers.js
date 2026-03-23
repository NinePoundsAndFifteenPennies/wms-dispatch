import http from '../common/http'

export const dispatcherTransfersApi = {
  listTransfers(params) {
    return http.get('/dispatcher/transfers', { params })
  },

  getTransferDetail(transferId) {
    return http.get(`/dispatcher/transfers/${transferId}`)
  },

  createTransfer(payload) {
    return http.post('/dispatcher/transfers', payload)
  },

  approveTransfer(transferId, payload = {}) {
    return http.post(`/dispatcher/transfers/${transferId}/approve`, payload)
  },

  rejectTransfer(transferId, payload) {
    return http.post(`/dispatcher/transfers/${transferId}/reject`, payload)
  },

  executeTransfer(transferId, payload = {}) {
    return http.post(`/dispatcher/transfers/${transferId}/execute`, payload)
  },

  listSourceWarehouses() {
    return http.get('/dispatcher/transfers/source-warehouses')
  },

  listSourceInventory(params) {
    return http.get('/dispatcher/transfers/source-inventory', { params })
  },

  listSourceDispatchers(params) {
    return http.get('/dispatcher/transfers/source-dispatchers', { params })
  },

  listPendingInboundRecords() {
    return http.get('/dispatcher/inbound-records/pending')
  },

  confirmInboundRecord(recordId) {
    return http.post(`/dispatcher/inbound-records/${recordId}/confirm`)
  },
}
