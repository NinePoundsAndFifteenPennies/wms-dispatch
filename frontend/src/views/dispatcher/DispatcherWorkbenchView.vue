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
            <h3>进行中订单</h3>
          </div>
        </div>

        <div class="queue-list" v-if="queueOrders.length > 0">
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
        <el-empty v-else description="暂无进行中订单" :image-size="96" />

        <section class="placeholder-panel">
          <p class="section-kicker">调度提醒（占位）</p>
          <p>当前为设计占位，后续将接入实时提醒流与告警策略。</p>
        </section>
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
            <span>订单明细 {{ selectedOrder.items?.length || 0 }} 条</span>
          </div>
          <el-table :data="selectedOrder.items || []" stripe height="300">
            <el-table-column prop="product_sku" label="SKU" min-width="120" />
            <el-table-column prop="product_name" label="产品名称" min-width="180" />
            <el-table-column prop="qty" label="数量" width="100" />
            <el-table-column label="单价(元)" width="120">
              <template #default="{ row }">{{ formatYuan(row.unit_price) }}</template>
            </el-table-column>
            <el-table-column label="小计(元)" width="120">
              <template #default="{ row }">{{ formatYuan((row.unit_price || 0) * (row.qty || 0)) }}</template>
            </el-table-column>
          </el-table>

          <section class="placeholder-panel">
            <p class="section-kicker">阶段工单（占位）</p>
            <p>当前保留原设计思路占位，后续将接入分阶段工单派发与推进操作。</p>
          </section>
        </div>
        <el-empty v-else description="请选择订单查看详情" :image-size="110" />
      </section>

      <aside class="insight-panel">
        <section class="side-card">
          <p class="section-kicker">当前订单概览</p>
          <div class="stat-row">
            <span>总件数</span>
            <strong>{{ selectedOrder?.total_items || 0 }}</strong>
          </div>
          <div class="stat-row">
            <span>总金额(元)</span>
            <strong>{{ selectedOrder?.total_amount || 0 }}</strong>
          </div>
          <div class="stat-row">
            <span>客户联系</span>
            <strong>{{ selectedOrder?.customer_contact || '-' }}</strong>
          </div>
          <div class="order-note">{{ selectedOrder?.description || '暂无备注' }}</div>
        </section>

        <section class="side-card placeholder-panel">
          <p class="section-kicker">动态流（占位）</p>
          <p>当前为占位设计，后续将接入订单活动流与异常事件时间线。</p>
          <el-empty description="占位图" :image-size="86" />
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

const inProgressQueueCount = computed(() => queueOrders.value.filter((o) => o.status === 'in_progress').length)
const focusTitle = computed(() => `进行中 ${inProgressQueueCount.value} 单`)
const focusDescription = computed(() => '工作台当前仅展示进行中订单，待接单请前往接单中心。')

async function fetchWorkbench() {
  loading.value = true
  try {
    const myRes = await dispatcherOrdersApi.getMyOrders()
    queueOrders.value = (myRes.data.items || [])
      .filter((item) => item.status === 'in_progress')
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
  try {
    const res = await dispatcherOrdersApi.getMyOrderDetail(orderId)
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
  return { name: 'dispatcher-my-order-detail', params: { orderId: order.id } }
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

function formatYuan(yuan) {
  const value = Number(yuan || 0)
  return `¥ ${Number.isFinite(value) ? value.toFixed(2) : '0.00'}`
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
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-list {
  display: grid;
  gap: 10px;
  margin-top: 4px;
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

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--dispatcher-muted);
}

.insight-panel {
  display: grid;
  gap: 14px;
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

.placeholder-panel {
  padding: 12px;
  border-radius: 12px;
  border: 1px dashed #d3c7b6;
  background: #f9f2e8;
}

.placeholder-panel p:last-child {
  margin-top: 8px;
  color: var(--dispatcher-muted);
}

@media (max-width: 1220px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
