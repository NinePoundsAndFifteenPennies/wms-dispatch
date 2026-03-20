import DispatcherLayout from '../../layouts/DispatcherLayout.vue'
import DispatcherWorkbenchView from '../../views/dispatcher/DispatcherWorkbenchView.vue'
import DispatcherOrdersView from '../../views/dispatcher/DispatcherOrdersView.vue'
import DispatcherMyOrdersView from '../../views/dispatcher/DispatcherMyOrdersView.vue'
import DispatcherWorkOrdersView from '../../views/dispatcher/DispatcherWorkOrdersView.vue'
import DispatcherTransfersView from '../../views/dispatcher/DispatcherTransfersView.vue'

export const dispatcherRoutes = [
  {
    path: '/dispatcher',
    component: DispatcherLayout,
    meta: { roleGroup: 'dispatcher' },
    children: [
      {
        path: '',
        name: 'dispatcher-workbench',
        component: DispatcherWorkbenchView,
        meta: { roles: ['dispatcher'], title: '工作台' },
      },
      {
        path: 'orders',
        name: 'dispatcher-orders',
        component: DispatcherOrdersView,
        meta: { roles: ['dispatcher'], title: '接单中心' },
      },
      {
        path: 'my-orders',
        name: 'dispatcher-my-orders',
        component: DispatcherMyOrdersView,
        meta: { roles: ['dispatcher'], title: '我的订单' },
      },
      {
        path: 'work-orders',
        name: 'dispatcher-work-orders',
        component: DispatcherWorkOrdersView,
        meta: { roles: ['dispatcher'], title: '工单中心' },
      },
      {
        path: 'transfers',
        name: 'dispatcher-transfers',
        component: DispatcherTransfersView,
        meta: { roles: ['dispatcher'], title: '调拨请求' },
      },
    ],
  },
]
