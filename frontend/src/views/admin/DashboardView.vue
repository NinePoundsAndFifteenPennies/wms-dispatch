<template>
  <div class="dashboard-grid">
    <section class="hero">
      <p class="kicker">Today Focus</p>
      <h3>
        <el-icon><Monitor /></el-icon>
        管理控制台聚焦订单运营与库存健康，支持绩效钻取与预警追踪
      </h3>
      <p>点击绩效图可下钻到仓库调度员视角，点击预警可直接进入相关订单或库存页面。</p>
    </section>

    <KpiCards :kpis="overview.kpis" @card-click="handleCardClick" />

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else>
      <OrdersStatusDonut
        :items="overview.orders_status_distribution"
        @slice-click="handleOrderStatusClick"
      />

      <WarehouseOrderPerformanceBar
        :items="overview.warehouse_order_performance"
        @warehouse-click="openWarehousePerformance"
      />

      <WarehouseLoadBar :items="overview.warehouse_loads" @bar-click="openWarehouseInventory" />

      <LowStockTopBar :items="overview.low_stock_top" @item-click="openWarehouseInventory" />

      <ProductPopularityDonut
        :items="overview.product_popularity"
        @product-click="handleProductPopularityClick"
      />

      <AlertTimeline :items="overview.alerts" @alert-click="handleAlertClick" />
    </template>

    <el-dialog v-model="dispatcherDialogVisible" width="960px" destroy-on-close>
      <template #header>
        <span>{{ dispatcherPerformance.warehouse_name || '仓库' }} 调度员订单绩效</span>
      </template>
      <DispatcherOrderPerformanceBar
        :warehouse-name="dispatcherPerformance.warehouse_name"
        :items="dispatcherPerformance.dispatchers"
      />
      <el-empty
        v-if="!dispatcherLoading && !dispatcherPerformance.dispatchers.length"
        description="该仓库暂无调度员订单数据"
      />
      <template #footer>
        <el-button @click="dispatcherDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import { adminDashboardApi } from '../../api/admin/dashboard'
import KpiCards from '../../components/admin/dashboard/KpiCards.vue'
import OrdersStatusDonut from '../../components/admin/dashboard/OrdersStatusDonut.vue'
import WarehouseLoadBar from '../../components/admin/dashboard/WarehouseLoadBar.vue'
import LowStockTopBar from '../../components/admin/dashboard/LowStockTopBar.vue'
import AlertTimeline from '../../components/admin/dashboard/AlertTimeline.vue'
import WarehouseOrderPerformanceBar from '../../components/admin/dashboard/WarehouseOrderPerformanceBar.vue'
import DispatcherOrderPerformanceBar from '../../components/admin/dashboard/DispatcherOrderPerformanceBar.vue'
import ProductPopularityDonut from '../../components/admin/dashboard/ProductPopularityDonut.vue'

const router = useRouter()
const loading = ref(false)
const dispatcherDialogVisible = ref(false)
const dispatcherLoading = ref(false)
const refreshTimer = ref(null)
const dispatcherPerformance = ref({
  warehouse_id: null,
  warehouse_name: '',
  total_orders: 0,
  completed_orders: 0,
  completion_rate: 0,
  dispatchers: [],
})

const overview = ref({
  kpis: {
    pending_acceptance_orders: 0,
    low_stock_alerts: 0,
    cancelled_orders_today: 0,
    accepted_no_dispatch_orders: 0,
  },
  orders_status_distribution: [],
  warehouse_loads: [],
  warehouse_order_performance: [],
  product_popularity: [],
  low_stock_top: [],
  alerts: [],
})

async function fetchOverview() {
  loading.value = true
  try {
    const res = await adminDashboardApi.getOverview()
    overview.value = res.data || overview.value
  } catch {
    ElMessage.error('控制台总览数据加载失败')
  } finally {
    loading.value = false
  }
}

function handleCardClick(key) {
  if (key === 'pending_acceptance_orders') {
    router.push({ path: '/orders', query: { status: 'pending_acceptance' } })
    return
  }
  if (key === 'accepted_no_dispatch_orders') {
    router.push({ path: '/orders', query: { status: 'in_progress' } })
    return
  }
  if (key === 'low_stock_alerts') {
    const firstLowStock = overview.value.low_stock_top?.[0]
    if (firstLowStock?.warehouse_id) {
      openWarehouseInventory(firstLowStock.warehouse_id)
      return
    }
    router.push('/warehouses')
    return
  }
  if (key === 'cancelled_orders_today') {
    router.push({ path: '/orders', query: { status: 'cancelled' } })
  }
}

function handleOrderStatusClick(status) {
  router.push({ path: '/orders', query: { status } })
}

function openWarehouseInventory(warehouseId) {
  if (!warehouseId) return
  router.push({
    path: `/warehouses/${warehouseId}/inventory`,
    query: { from: 'dashboard' },
  })
}

async function openWarehousePerformance(warehouseId) {
  if (!warehouseId) return
  dispatcherDialogVisible.value = true
  dispatcherLoading.value = true
  try {
    const res = await adminDashboardApi.getWarehouseDispatcherPerformance(warehouseId)
    dispatcherPerformance.value = res.data || dispatcherPerformance.value
  } catch {
    ElMessage.error('仓库调度员绩效加载失败')
  } finally {
    dispatcherLoading.value = false
  }
}

function handleAlertClick(alert) {
  if (!alert) return
  if (alert.alert_type === 'order_pending' && alert.order_no) {
    router.push({ path: '/orders', query: { search: alert.order_no, status: 'pending_acceptance' } })
    return
  }
  if (alert.alert_type === 'accepted_no_dispatch' && alert.order_no) {
    router.push({ path: '/orders', query: { search: alert.order_no, status: 'in_progress' } })
    return
  }
  if (alert.alert_type === 'order_cancelled' && alert.order_no) {
    router.push({ path: '/orders', query: { search: alert.order_no, status: 'cancelled' } })
    return
  }
  if (alert.alert_type === 'low_stock' && alert.warehouse_id) {
    openWarehouseInventory(alert.warehouse_id)
  }
}

function handleProductPopularityClick(payload) {
  const query = {
    from: 'dashboard',
  }

  if (payload?.productId) {
    query.focus_product_id = String(payload.productId)
  }
  if (payload?.sku) {
    query.search = payload.sku
  }

  router.push({
    path: '/products',
    query,
  })
}

onMounted(() => {
  fetchOverview()
  refreshTimer.value = setInterval(fetchOverview, 60000)
})

onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
})
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: 2fr 1fr;
}

.hero {
  grid-column: 1 / -1;
  padding: 18px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(120deg, #1c9c89 0%, #117264 55%, #0a4f47 100%);
}

.kicker {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 12px;
  opacity: 0.84;
}

.hero h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 24px;
}

.hero p {
  margin: 10px 0 0;
  font-size: 14px;
  opacity: 0.9;
}

@media (max-width: 960px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero h3 {
    font-size: 20px;
  }

  .hero p {
    font-size: 13px;
  }
}
</style>
