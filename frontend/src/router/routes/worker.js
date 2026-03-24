import WorkerLayout from '../../layouts/WorkerLayout.vue'
import WorkerWorkOrdersView from '../../views/worker/WorkerWorkOrdersView.vue'
import WorkerWorkOrderDetailView from '../../views/worker/WorkerWorkOrderDetailView.vue'
import ProfileView from '../../views/common/ProfileView.vue'

export const workerRoutes = [
  {
    path: '/worker',
    component: WorkerLayout,
    meta: { roleGroup: 'worker' },
    children: [
      {
        path: '',
        name: 'worker-home',
        component: WorkerWorkOrdersView,
        meta: { roles: ['worker'], title: '我的工单' },
      },
      {
        path: 'work-orders',
        name: 'worker-work-orders',
        component: WorkerWorkOrdersView,
        meta: { roles: ['worker'], title: '我的工单' },
      },
      {
        path: 'work-orders/:workOrderId',
        name: 'worker-work-order-detail',
        component: WorkerWorkOrderDetailView,
        meta: { roles: ['worker'], title: '工单详情' },
      },
      {
        path: 'profile',
        name: 'worker-profile',
        component: ProfileView,
        meta: { roles: ['worker'], title: '个人中心' },
      },
    ],
  },
]
