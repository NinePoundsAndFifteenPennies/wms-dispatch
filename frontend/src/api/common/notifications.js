import http from './http'

export const notificationsApi = {
  listMyNotifications(params) {
    return http.get('/auth/me/notifications', { params, silentError: true })
  },

  markNotificationRead(notificationId) {
    return http.patch(`/auth/me/notifications/${notificationId}/read`, null, { silentError: true })
  },

  markAllNotificationsRead() {
    return http.patch('/auth/me/notifications/read-all', null, { silentError: true })
  },
}
