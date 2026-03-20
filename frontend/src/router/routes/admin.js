import AdminLayout from '../../layouts/AdminLayout.vue'
import DashboardView from '../../views/admin/DashboardView.vue'
import OrdersView from '../../views/admin/OrdersView.vue'
import WorkOrdersView from '../../views/admin/WorkOrdersView.vue'
import UsersView from '../../views/admin/UsersView.vue'
import CustomersView from '../../views/admin/CustomersView.vue'
import ProductsView from '../../views/admin/ProductsView.vue'
import WarehousesView from '../../views/admin/WarehousesView.vue'
import WarehouseInventoryView from '../../views/admin/WarehouseInventoryView.vue'

export const adminRoutes = [
  {
    path: '/',
    component: AdminLayout,
    meta: { roleGroup: 'admin' },
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
        meta: { roles: ['admin', 'worker'] },
      },
      {
        path: 'orders',
        name: 'orders',
        component: OrdersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: WorkOrdersView,
        meta: { roles: ['admin', 'worker'] },
      },
      {
        path: 'users',
        name: 'users',
        component: UsersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'warehouses',
        name: 'warehouses',
        component: WarehousesView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'warehouses/:id/inventory',
        name: 'warehouse-inventory',
        component: WarehouseInventoryView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'customers',
        name: 'customers',
        component: CustomersView,
        meta: { roles: ['admin'] },
      },
      {
        path: 'products',
        name: 'products',
        component: ProductsView,
        meta: { roles: ['admin'] },
      },
    ],
  },
]
