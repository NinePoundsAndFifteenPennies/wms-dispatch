<template>
  <div class="dispatcher-workbench" v-loading="loading">
    <section class="top-strip">
      <p class="head-title">调度工作台</p>
      <div class="head-pills">
        <span class="pill warn">待接单 {{ queueCatalog.pending }}</span>
        <span class="pill active">进行中 {{ queueCatalog.in_progress }}</span>
        <span class="pill danger">告警 {{ queueCatalog.alert }}</span>
      </div>
    </section>

    <section class="bench-grid">
      <aside class="bench-panel queue-panel">
        <p class="panel-label">视图</p>
        <div class="queue-switcher">
          <button
            v-for="tab in queueTabs"
            :key="tab.key"
            type="button"
            class="queue-tab"
            :class="{ active: queueMode === tab.key }"
            @click="queueMode = tab.key"
          >
            <span>{{ tab.label }}</span>
            <span class="dot" :class="`dot-${tab.tone}`"></span>
          </button>
        </div>

        <div v-if="queueList.length > 0" class="queue-list">
          <button
            v-for="order in queueList"
            :key="order.id"
            type="button"
            class="queue-card"
            :class="{ selected: selectedOrderId === order.id }"
            @click="selectOrder(order.id)"
          >
            <div class="queue-top">
              <strong>{{ order.order_no }}</strong>
              <span class="priority-chip" :class="`priority-${order.priority}`">{{ priorityText(order.priority) }}</span>
            </div>
            <p class="queue-meta">{{ order.customer_name }} · {{ stageHint(order) }}</p>
            <p class="queue-sub">{{ statusText(order.status) }} · {{ timeText(order.updated_at) }}</p>
          </button>
        </div>
        <el-empty v-else :description="emptyText" :image-size="90" />

        <section class="placeholder-card">
          <p class="panel-label">异常中心（占位）</p>
          <p>未实现告警规则与超时 SLA 面板，当前保留视觉占位。</p>
        </section>
      </aside>

      <section class="bench-panel center-panel">
        <template v-if="selectedOrder">
          <header class="order-head">
            <div>
              <h3>{{ selectedOrder.order_no }}</h3>
              <p>{{ selectedOrder.customer_name }} · {{ selectedOrder.warehouse_name || '-' }} · {{ statusText(selectedOrder.status) }}</p>
            </div>
            <div class="head-actions">
              <router-link class="line-btn" :to="orderDetailPath(selectedOrder)">查看详情</router-link>
              <router-link
                v-if="selectedOrderSource === 'my' && selectedOrder.status === 'in_progress'"
                class="solid-btn"
                :to="{ name: 'dispatcher-my-order-detail', params: { orderId: selectedOrder.id } }"
              >
                + 派发工单
              </router-link>
            </div>
          </header>

          <div class="stage-tabs">
            <button
              v-for="stage in selectedOrder.stages || []"
              :key="stage.id"
              type="button"
              class="stage-tab"
              :class="{ active: selectedStageId === stage.id }"
              @click="selectedStageId = stage.id"
            >
              {{ stageText(stage.stage_type) }}
              <small>{{ stageStatusText(stage.status) }}</small>
            </button>
          </div>

          <div class="work-body">
            <section class="task-column">
              <p class="panel-label">本阶段工单 · {{ stageWorkOrders.length }} 张</p>
              <div class="task-list" v-if="stageWorkOrders.length > 0">
                <article v-for="work in stageWorkOrders" :key="work.id" class="task-card">
                  <span class="avatar">{{ firstChar(work.worker_name) }}</span>
                  <div>
                    <strong>{{ work.worker_name }}</strong>
                    <p>{{ workOrderStatusText(work.status) }} · {{ priorityText(work.priority) }}</p>
                    <p>开始 {{ timeText(work.started_at || work.created_at) }}</p>
                  </div>
                  <span class="status-tag" :class="`tag-${work.status}`">{{ workOrderStatusText(work.status) }}</span>
                </article>
              </div>
              <el-empty v-else description="暂无工单，点击右上角派发" :image-size="80" />
            </section>

            <section class="items-column">
              <p class="panel-label">订单明细</p>
              <el-table :data="selectedOrder.items || []" height="300" stripe>
                <el-table-column prop="product_sku" label="SKU" min-width="110" />
                <el-table-column prop="product_name" label="产品" min-width="160" />
                <el-table-column prop="qty" label="件数" width="80" />
                <el-table-column label="小计" width="110">
                  <template #default="{ row }">{{ formatYuan(row.subtotal || (row.unit_price || 0) * (row.qty || 0)) }}</template>
                </el-table-column>
              </el-table>
            </section>
          </div>
        </template>
        <el-empty v-else description="请选择左侧订单" :image-size="110" />
      </section>

      <aside class="right-stack">
        <section class="bench-panel side-panel">
          <p class="panel-label">本仓工人状态</p>
          <div v-if="workerStatusRows.length > 0" class="worker-list">
            <div v-for="row in workerStatusRows" :key="row.key" class="worker-row">
              <span class="signal" :class="`signal-${row.tone}`"></span>
              <span>{{ row.name }}</span>
              <span class="worker-state">{{ row.state }}</span>
            </div>
          </div>
          <el-empty v-else :description="selectedOrder ? '暂无已派发工单，请先派发工单' : '请先选择左侧订单'" :image-size="72" />

          <div class="summary-box" v-if="selectedOrder">
            <div class="summary-row"><span>产品种类</span><strong>{{ selectedOrder.items?.length || 0 }} SKU</strong></div>
            <div class="summary-row"><span>总件数</span><strong>{{ selectedOrder.total_items || 0 }} 件</strong></div>
            <div class="summary-row"><span>客户联系</span><strong>{{ selectedOrder.customer_contact || '-' }}</strong></div>
          </div>
        </section>

        <section class="bench-panel side-panel">
          <p class="panel-label">动态流</p>
          <div v-if="timeline.length > 0" class="timeline-list">
            <article class="timeline-item" v-for="(line, index) in timeline" :key="`${line.time}-${index}`">
              <p>{{ line.text }}</p>
              <small>{{ line.time }}</small>
            </article>
          </div>
          <el-empty v-else description="暂无动态" :image-size="72" />
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import {
  compareCnDateDesc,
  formatCnDateTime,
  isCnOvertime,
  minutesSinceCn,
} from '../../utils/cnTime'

const loading = ref(false)
const queueMode = ref('in_progress')
const myOrders = ref([])
const pendingOrders = ref([])
const detailMap = ref({})
const workOrderMap = ref({})
const sourceMap = ref({})
const selectedOrderId = ref(null)
const selectedStageId = ref(null)

const queueTabs = [
  { key: 'in_progress', label: '进行中订单', tone: 'blue' },
  { key: 'pending', label: '待接单', tone: 'orange' },
  { key: 'alert', label: '告警 & 超时', tone: 'red' },
]

const queueCatalog = computed(() => {
  const inProgress = myOrders.value.filter((item) => item.status === 'in_progress').length
  const pending = pendingOrders.value.length
  const alert = myOrders.value.filter((item) => isCnOvertime(item.updated_at, 120)).length
  return {
    in_progress: inProgress,
    pending,
    alert,
  }
})

const queueList = computed(() => {
  if (queueMode.value === 'pending') return pendingOrders.value
  if (queueMode.value === 'alert') return myOrders.value.filter((item) => isCnOvertime(item.updated_at, 120))
  return myOrders.value.filter((item) => item.status === 'in_progress')
})

const emptyText = computed(() => {
  if (queueMode.value === 'pending') return '暂无待接单订单'
  if (queueMode.value === 'alert') return '暂无告警订单'
  return '暂无进行中订单'
})

const selectedOrder = computed(() => {
  if (!selectedOrderId.value) return null
  return detailMap.value[selectedOrderId.value] || null
})

const selectedOrderSource = computed(() => {
  if (!selectedOrderId.value) return null
  return sourceMap.value[selectedOrderId.value] || null
})

const selectedOrderWorkOrders = computed(() => {
  if (!selectedOrderId.value) return []
  return workOrderMap.value[selectedOrderId.value] || []
})

const stageWorkOrders = computed(() => {
  if (!selectedStageId.value) return selectedOrderWorkOrders.value
  return selectedOrderWorkOrders.value.filter((item) => item.stage_id === selectedStageId.value)
})

const workerStatusRows = computed(() => {
  const rows = selectedOrderWorkOrders.value
  if (rows.length > 0) {
    const latestByWorker = rows.reduce((acc, item) => {
      const key = item.worker_id
      const prev = acc[key]
      if (!prev || compareCnDateDesc(item.updated_at, prev.updated_at) < 0) {
        acc[key] = item
      }
      return acc
    }, {})

    return Object.values(latestByWorker)
      .slice(0, 8)
      .map((item) => ({
        key: `wo-${item.id}`,
        name: item.worker_name,
        state: workerStateText(item),
        tone: workerTone(item.status),
      }))
  }

  return []
})

const timeline = computed(() => {
  const detail = selectedOrder.value
  if (!detail) return []

  const lines = []
  if (detail.created_at) lines.push({ timeRaw: detail.created_at, text: `${detail.order_no} 已创建` })
  if (detail.accepted_at) lines.push({ timeRaw: detail.accepted_at, text: `${detail.order_no} 已被接单` })
  if (detail.completed_at) lines.push({ timeRaw: detail.completed_at, text: `${detail.order_no} 已完成` })
  if (detail.cancelled_at) lines.push({ timeRaw: detail.cancelled_at, text: `${detail.order_no} 已取消` })

  selectedOrderWorkOrders.value.forEach((item) => {
    if (item.created_at) {
      lines.push({
        timeRaw: item.created_at,
        text: `${item.worker_name} 被派发 ${stageText(item.stage_type)} 工单`,
      })
    }
    if (item.started_at) {
      lines.push({
        timeRaw: item.started_at,
        text: `${item.worker_name} 开始执行 ${stageText(item.stage_type)} 工单`,
      })
    }
    if (item.completed_at) {
      lines.push({
        timeRaw: item.completed_at,
        text: `${item.worker_name} 完成 ${stageText(item.stage_type)} 工单`,
      })
    }
    if (item.terminated_at) {
      lines.push({
        timeRaw: item.terminated_at,
        text: `${item.worker_name} 工单已终止`,
      })
    }
  })

  return lines
    .sort((a, b) => compareCnDateDesc(a.timeRaw, b.timeRaw))
    .slice(0, 8)
    .map((item) => ({
      text: item.text,
      time: formatCnDateTime(item.timeRaw),
    }))
})

watch(selectedOrder, (order) => {
  const stageList = order?.stages || []
  if (stageList.length === 0) {
    selectedStageId.value = null
    return
  }
  const stage = stageList.find((item) => item.status !== 'completed') || stageList[0]
  selectedStageId.value = stage.id
})

watch(queueList, async (list) => {
  if (list.length === 0) {
    selectedOrderId.value = null
    return
  }
  if (!list.some((item) => item.id === selectedOrderId.value)) {
    selectedOrderId.value = list[0].id
    await ensureLoaded(selectedOrderId.value)
  }
})

async function fetchWorkbench() {
  loading.value = true
  try {
    const [myRes, pendingRes] = await Promise.all([dispatcherOrdersApi.getMyOrders(), dispatcherOrdersApi.getPendingOrders()])
    myOrders.value = (myRes.data.items || []).sort((a, b) => compareCnDateDesc(a.updated_at, b.updated_at))
    pendingOrders.value = (pendingRes.data.items || []).sort((a, b) => compareCnDateDesc(a.updated_at, b.updated_at))

    const source = {}
    myOrders.value.forEach((item) => {
      source[item.id] = 'my'
    })
    pendingOrders.value.forEach((item) => {
      if (!source[item.id]) source[item.id] = 'pending'
    })
    sourceMap.value = source

    if (queueList.value.length > 0) {
      selectedOrderId.value = queueList.value[0].id
      await ensureLoaded(selectedOrderId.value)
    }
  } catch {
    myOrders.value = []
    pendingOrders.value = []
    detailMap.value = {}
    workOrderMap.value = {}
    sourceMap.value = {}
    selectedOrderId.value = null
  } finally {
    loading.value = false
  }
}

async function ensureLoaded(orderId) {
  if (!detailMap.value[orderId]) {
    try {
      const source = sourceMap.value[orderId]
      const detailRes =
        source === 'pending'
          ? await dispatcherOrdersApi.getPendingOrderDetail(orderId)
          : await dispatcherOrdersApi.getMyOrderDetail(orderId)
      detailMap.value = { ...detailMap.value, [orderId]: detailRes.data }
    } catch {
      detailMap.value = { ...detailMap.value }
    }
  }

  if (!workOrderMap.value[orderId] && sourceMap.value[orderId] === 'my') {
    try {
      const workRes = await dispatcherOrdersApi.getOrderWorkOrders(orderId)
      workOrderMap.value = { ...workOrderMap.value, [orderId]: workRes.data.items || [] }
    } catch {
      workOrderMap.value = { ...workOrderMap.value, [orderId]: [] }
    }
  }
}

async function selectOrder(orderId) {
  selectedOrderId.value = orderId
  await ensureLoaded(orderId)
}

function orderDetailPath(order) {
  if (selectedOrderSource.value === 'pending') {
    return { name: 'dispatcher-order-detail', params: { orderId: order.id } }
  }
  return { name: 'dispatcher-my-order-detail', params: { orderId: order.id } }
}

function stageHint(order) {
  const detail = detailMap.value[order.id]
  if (!detail?.stages?.length) return '阶段待加载'
  const active = detail.stages.find((item) => item.status !== 'completed')
  return active ? `${stageText(active.stage_type)} 阶段` : '阶段完成'
}

function firstChar(value) {
  if (!value) return '?'
  return String(value).slice(0, 1)
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

function stageText(stageType) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[stageType] || stageType
}

function stageStatusText(status) {
  return {
    not_started: '待处理',
    in_progress: '作业中',
    completed: '已完成',
  }[status] || status
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

function workerTone(status) {
  return {
    pending: 'amber',
    in_progress: 'blue',
    completed: 'green',
    terminated: 'red',
  }[status] || 'gray'
}

function workerStateText(workOrder) {
  return `${stageText(workOrder.stage_type)} · ${workOrderStatusText(workOrder.status)}`
}

function timeText(value) {
  if (!value) return '-'
  const diffMinutes = minutesSinceCn(value)
  if (Number.isNaN(diffMinutes)) return '-'
  if (diffMinutes < 1) return '刚刚'
  if (diffMinutes < 60) return `${diffMinutes}分钟前`
  const hours = Math.floor(diffMinutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

function formatYuan(yuan) {
  const value = Number(yuan || 0)
  return `${Number.isFinite(value) ? value.toFixed(2) : '0.00'}元`
}

onMounted(fetchWorkbench)
</script>

<style scoped>
.dispatcher-workbench {
  display: grid;
  gap: 14px;
}

.top-strip {
  border: 1px solid #d2c9ba;
  border-radius: 14px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f9f7f2 0%, #f1ece2 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.head-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.head-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.pill.warn {
  background: #fbe9cf;
  color: #8f5f1f;
}

.pill.active {
  background: #e4effd;
  color: #1f5c9a;
}

.pill.danger {
  background: #f9dfdc;
  color: #a0433f;
}

.bench-grid {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 300px;
  gap: 12px;
  min-height: 640px;
}

.bench-panel {
  border: 1px solid #d6d0c4;
  border-radius: 14px;
  background: rgba(255, 253, 249, 0.92);
}

.queue-panel {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-label {
  margin: 0;
  font-size: 12px;
  color: #8a7f6d;
}

.queue-switcher {
  display: grid;
  gap: 6px;
}

.queue-tab {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  padding: 9px 10px;
  text-align: left;
  color: #4b4438;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.queue-tab.active {
  background: #f0ebe2;
  border-color: #c8bdab;
  font-weight: 700;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.dot-blue {
  background: #3a74b4;
}

.dot-orange {
  background: #ba6a1e;
}

.dot-red {
  background: #a03d38;
}

.queue-list {
  display: grid;
  gap: 8px;
  max-height: 430px;
  overflow: auto;
  padding-right: 4px;
}

.queue-card {
  text-align: left;
  border: 1px solid #ddd4c7;
  border-radius: 10px;
  padding: 10px;
  background: #fffdf9;
  cursor: pointer;
}

.queue-card.selected {
  border-color: #7b98bc;
  box-shadow: inset 0 0 0 1px rgba(64, 108, 163, 0.22);
}

.queue-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.queue-meta,
.queue-sub {
  margin: 6px 0 0;
  font-size: 12px;
}

.queue-sub {
  color: #7c7265;
}

.priority-chip {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.priority-high {
  background: #f8dddd;
  color: #a0443f;
}

.priority-medium {
  background: #f7ead6;
  color: #7a4a16;
}

.priority-low {
  background: #e7efdd;
  color: #436c25;
}

.placeholder-card {
  border: 1px dashed #cabdaa;
  border-radius: 10px;
  background: #f8f2e8;
  padding: 10px;
}

.placeholder-card p {
  margin: 0;
  font-size: 12px;
  color: #6f6456;
}

.placeholder-card p + p {
  margin-top: 6px;
}

.center-panel {
  display: flex;
  flex-direction: column;
}

.order-head {
  padding: 12px 14px;
  border-bottom: 1px solid #ddd4c7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.order-head h3,
.order-head p {
  margin: 0;
}

.order-head p {
  margin-top: 4px;
  color: #756a5b;
  font-size: 12px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.line-btn,
.solid-btn {
  border-radius: 8px;
  padding: 6px 10px;
  text-decoration: none;
  font-size: 12px;
}

.line-btn {
  border: 1px solid #c9beae;
  color: #4f4539;
  background: #fffdf9;
}

.solid-btn {
  border: 1px solid #859cb9;
  color: #123e73;
  background: #e9f1fd;
  font-weight: 600;
}

.stage-tabs {
  padding: 8px 12px;
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #eee7dd;
  overflow: auto;
}

.stage-tab {
  border: none;
  background: transparent;
  color: #665b4c;
  padding: 8px 10px;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  white-space: nowrap;
}

.stage-tab small {
  display: block;
  margin-top: 3px;
  color: #9a8f7f;
  font-size: 11px;
}

.stage-tab.active {
  border-bottom-color: #3f6ca3;
  color: #1f4574;
  font-weight: 700;
}

.work-body {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  min-height: 0;
}

.task-column,
.items-column {
  min-width: 0;
}

.task-list {
  display: grid;
  gap: 8px;
  max-height: 320px;
  overflow: auto;
  padding-right: 2px;
}

.task-card {
  border: 1px solid #ddd4c7;
  border-left: 3px solid #7b98bc;
  border-radius: 10px;
  background: #fffdfa;
  padding: 8px 10px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.task-card p {
  margin: 2px 0 0;
  color: #756a5b;
  font-size: 12px;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ece5d9;
  color: #5c5246;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}

.tag-pending {
  color: #8f6d42;
  background: #f7ead6;
}

.tag-in_progress {
  color: #1f5c9a;
  background: #e5f0fc;
}

.tag-completed {
  color: #22663f;
  background: #dcf3e4;
}

.tag-terminated {
  color: #9d4e3b;
  background: #f9e6df;
}

.right-stack {
  display: grid;
  gap: 10px;
}

.side-panel {
  padding: 10px 12px;
}

.worker-list {
  display: grid;
  gap: 7px;
  margin-top: 8px;
}

.worker-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.signal {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.signal-blue {
  background: #2c6db2;
}

.signal-amber {
  background: #ba6a1e;
}

.signal-green {
  background: #2e7f4f;
}

.signal-red {
  background: #ab4743;
}

.signal-gray {
  background: #8f877a;
}

.worker-state {
  color: #6f6456;
  font-size: 12px;
}

.summary-box {
  margin-top: 10px;
  border-top: 1px solid #ece3d7;
  padding-top: 10px;
  display: grid;
  gap: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.timeline-list {
  margin-top: 8px;
  display: grid;
  gap: 8px;
  max-height: 280px;
  overflow: auto;
  padding-right: 2px;
}

.timeline-item {
  border-bottom: 1px solid #ece3d7;
  padding-bottom: 6px;
}

.timeline-item p,
.timeline-item small {
  margin: 0;
}

.timeline-item p {
  color: #4f4539;
  font-size: 13px;
}

.timeline-item small {
  color: #8a7f6d;
  font-size: 12px;
  margin-top: 2px;
  display: inline-block;
}

@media (max-width: 1280px) {
  .bench-grid {
    grid-template-columns: 1fr;
  }

  .work-body {
    grid-template-columns: 1fr;
  }
}
</style>
