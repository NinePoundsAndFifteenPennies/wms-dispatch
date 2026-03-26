import http from './http'

export const notificationsApi = {
  listMyNotifications(params) {
    return http.get('/auth/me/notifications', { params })
  },

  markNotificationRead(notificationId) {
    return http.patch(`/auth/me/notifications/${notificationId}/read`)
  },

  markAllNotificationsRead() {
    return http.patch('/auth/me/notifications/read-all')
  },
}
