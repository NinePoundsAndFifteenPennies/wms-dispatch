import DispatcherLayout from '../../layouts/DispatcherLayout.vue'

const DispatcherWorkbenchView = () => import('../../views/dispatcher/DispatcherWorkbenchView.vue')
const DispatcherOrdersView = () => import('../../views/dispatcher/DispatcherOrdersView.vue')
const DispatcherOrderDetailView = () => import('../../views/dispatcher/DispatcherOrderDetailView.vue')
const DispatcherMyOrdersView = () => import('../../views/dispatcher/DispatcherMyOrdersView.vue')
const DispatcherMyOrderDetailView = () => import('../../views/dispatcher/DispatcherMyOrderDetailView.vue')
const DispatcherWorkOrdersView = () => import('../../views/dispatcher/DispatcherWorkOrdersView.vue')
const DispatcherTransfersView = () => import('../../views/dispatcher/DispatcherTransfersView.vue')
const DispatcherInventoryView = () => import('../../views/dispatcher/DispatcherInventoryView.vue')

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
        path: 'orders/:orderId',
        name: 'dispatcher-order-detail',
        component: DispatcherOrderDetailView,
        meta: { roles: ['dispatcher'], title: '接单中心详情' },
      },
      {
        path: 'my-orders',
        name: 'dispatcher-my-orders',
        component: DispatcherMyOrdersView,
        meta: { roles: ['dispatcher'], title: '我的订单' },
      },
      {
        path: 'my-orders/:orderId',
        name: 'dispatcher-my-order-detail',
        component: DispatcherMyOrderDetailView,
        meta: { roles: ['dispatcher'], title: '我的订单详情' },
      },
      {
        path: 'inventory',
        name: 'dispatcher-inventory',
        component: DispatcherInventoryView,
        meta: { roles: ['dispatcher'], title: '库存中心' },
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
