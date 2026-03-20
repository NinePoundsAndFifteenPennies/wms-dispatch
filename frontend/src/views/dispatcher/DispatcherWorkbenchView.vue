<template>
  <div class="dispatcher-workbench" v-loading="loading">
    <section class="focus-banner">
      <p class="section-kicker">Today Focus</p>
      <h2>{{ focusTitle }}</h2>
      <p>{{ focusDescription }}</p>
    </section>

    <section class="workspace-grid">
      <aside class="queue-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">订单队列</p>
            <h3>进行中 / 待接单</h3>
          </div>
        </div>

        <div class="queue-list">
          <button
            v-for="order in queueOrders"
            :key="order.id"
            type="button"
            class="queue-card"
            :class="{ selected: selectedOrderId === order.id }"
            @click="selectOrder(order.id)"
          >
            <div class="queue-card-head">
              <strong>{{ order.order_no }}</strong>
              <span class="priority-chip" :class="`priority-${order.priority}`">{{ priorityText(order.priority) }}</span>
            </div>
            <p>{{ order.customer_name }}</p>
            <small>{{ statusText(order.status) }}</small>
          </button>
        </div>
      </aside>

      <section class="detail-panel">
        <div class="detail-head" v-if="selectedOrder">
          <div>
            <h3>{{ selectedOrder.order_no }} / {{ selectedOrder.customer_name }}</h3>
            <p>
              仓库：{{ selectedOrder.warehouse_name || '-' }} ·
              状态：{{ statusText(selectedOrder.status) }} ·
              优先级：{{ priorityText(selectedOrder.priority) }}
            </p>
          </div>
          <router-link class="ghost-button" :to="orderDetailPath(selectedOrder)">查看详情</router-link>
        </div>

        <div class="detail-body" v-if="selectedOrder">
          <div class="action-row">
            <span>当前订单明细 {{ selectedOrder.items?.length || 0 }} 条</span>
          </div>
          <div class="work-order-list">
            <article v-for="item in selectedOrder.items || []" :key="item.id" class="work-order-card">
              <div class="worker-avatar">{{ item.product_name.slice(0, 1) }}</div>
              <div class="work-order-meta">
                <strong>{{ item.product_name }}</strong>
                <p>{{ item.product_sku }} · 数量 {{ item.qty }}</p>
              </div>
              <span class="status-chip">¥ {{ (item.unit_price || 0) / 100 }}</span>
            </article>
          </div>
        </div>
      </section>

      <aside class="insight-panel">
        <section class="side-card">
          <p class="section-kicker">当前订单概览</p>
          <div class="stat-row">
            <span>总件数</span>
            <strong>{{ selectedOrder?.total_items || 0 }}</strong>
          </div>
          <div class="stat-row">
            <span>总金额(分)</span>
            <strong>{{ selectedOrder?.total_amount || 0 }}</strong>
          </div>
          <div class="stat-row">
            <span>客户联系</span>
            <strong>{{ selectedOrder?.customer_contact || '-' }}</strong>
          </div>
          <div class="order-note">{{ selectedOrder?.description || '暂无备注' }}</div>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'

const loading = ref(false)
const queueOrders = ref([])
const detailMap = ref({})
const selectedOrderId = ref(null)

const selectedOrder = computed(() => {
  if (!selectedOrderId.value) return null
  return detailMap.value[selectedOrderId.value] || null
})

const focusTitle = computed(() => `待接单 ${queueOrders.value.filter((o) => o.status === 'pending_acceptance').length} 单`)
const focusDescription = computed(
  () => `进行中 ${queueOrders.value.filter((o) => o.status === 'in_progress').length} 单，请优先处理高优先级订单。`
)

async function fetchWorkbench() {
  loading.value = true
  try {
    const [pendingRes, myRes] = await Promise.all([
      dispatcherOrdersApi.getPendingOrders(),
      dispatcherOrdersApi.getMyOrders(),
    ])
    queueOrders.value = [...(myRes.data.items || []), ...(pendingRes.data.items || [])]
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, 8)

    if (queueOrders.value.length > 0) {
      selectedOrderId.value = queueOrders.value[0].id
      await ensureDetailLoaded(selectedOrderId.value)
    }
  } catch {
    queueOrders.value = []
    detailMap.value = {}
    selectedOrderId.value = null
  } finally {
    loading.value = false
  }
}

async function ensureDetailLoaded(orderId) {
  if (detailMap.value[orderId]) return
  const order = queueOrders.value.find((item) => item.id === orderId)
  if (!order) return
  try {
    const req =
      order.status === 'pending_acceptance'
        ? dispatcherOrdersApi.getPendingOrderDetail(orderId)
        : dispatcherOrdersApi.getMyOrderDetail(orderId)
    const res = await req
    detailMap.value = { ...detailMap.value, [orderId]: res.data }
  } catch {
    detailMap.value = { ...detailMap.value }
  }
}

async function selectOrder(orderId) {
  selectedOrderId.value = orderId
  await ensureDetailLoaded(orderId)
}

function orderDetailPath(order) {
  return order.status === 'pending_acceptance'
    ? { name: 'dispatcher-order-detail', params: { orderId: order.id } }
    : { name: 'dispatcher-my-order-detail', params: { orderId: order.id } }
}

function priorityText(priority) {
  return { high: '高', medium: '中', low: '低' }[priority] || priority
}

function statusText(status) {
  return {
    pending_acceptance: '待接单',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }[status] || status
}

onMounted(fetchWorkbench)
</script>

<style scoped>
.dispatcher-workbench {
  display: grid;
  gap: 16px;
}

.focus-banner {
  padding: 18px 20px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: linear-gradient(135deg, #faf7f1 0%, #f1ece3 100%);
}

.focus-banner h2,
.focus-banner p,
.section-kicker,
.panel-heading h3 {
  margin: 0;
}

.focus-banner h2 {
  margin-top: 6px;
  font-size: 28px;
}

.focus-banner p:last-child {
  margin-top: 8px;
  color: var(--dispatcher-muted);
}

.section-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.workspace-grid {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 16px;
}

.queue-panel,
.detail-panel,
.side-card {
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.86);
}

.queue-panel {
  padding: 14px;
}

.queue-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.queue-card {
  width: 100%;
  text-align: left;
  padding: 12px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 12px;
  background: var(--dispatcher-surface);
  color: inherit;
  cursor: pointer;
}

.queue-card.selected {
  border-color: var(--dispatcher-border-strong);
  box-shadow: 0 10px 22px rgba(63, 54, 42, 0.08);
}

.queue-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.priority-chip {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
}

.priority-high {
  background: #fbe2df;
  color: #a54343;
}

.priority-medium {
  background: #f7ead6;
  color: #7a4a16;
}

.priority-low {
  background: #e8efdd;
  color: #436c25;
}

.detail-head,
.detail-body {
  padding: 16px 18px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--dispatcher-border);
}

.ghost-button {
  border: 1px solid var(--dispatcher-border-strong);
  background: var(--dispatcher-surface);
  color: var(--dispatcher-text);
  border-radius: 10px;
  padding: 9px 14px;
  text-decoration: none;
}

.work-order-list {
  display: grid;
  gap: 10px;
}

.work-order-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 14px;
  background: var(--dispatcher-surface);
}

.worker-avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #ddd4c5;
  font-size: 12px;
  font-weight: 700;
}

.work-order-meta {
  flex: 1;
}

.work-order-meta strong,
.work-order-meta p {
  margin: 0;
}

.work-order-meta p {
  margin-top: 4px;
  color: var(--dispatcher-muted);
}

.status-chip {
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  background: #f7ead6;
  color: #7a4a16;
}

.insight-panel {
  display: grid;
}

.side-card {
  padding: 14px 16px;
}

.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-row + .stat-row {
  margin-top: 10px;
}

.order-note {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f2ece3;
  color: var(--dispatcher-muted);
}

@media (max-width: 1220px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
