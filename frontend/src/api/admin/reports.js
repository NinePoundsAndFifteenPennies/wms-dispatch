import http from '../common/http'

export const adminReportsApi = {
  generateReport(payload) {
    return http.post('/admin/reports/generate', payload, {
      timeout: 0,
    })
  },

  listReports(params) {
    return http.get('/admin/reports', { params })
  },

  getReportDetail(reportId) {
    return http.get(`/admin/reports/${reportId}`)
  },
}
