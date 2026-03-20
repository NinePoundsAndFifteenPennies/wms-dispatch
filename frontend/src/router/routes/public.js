import LoginView from '../../views/LoginView.vue'

export const publicRoutes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
]
