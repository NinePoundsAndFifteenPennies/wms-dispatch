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
            <p class="queue-sub">
              {{ statusText(order.status) }} · {{ timeText(order.updated_at) }}
              <template v-if="queueMode === 'alert'"> · {{ alertReasonText(order) }}</template>
            </p>
          </button>
        </div>
        <el-empty v-else :description="emptyText" :image-size="90" />

        <section class="placeholder-card">
          <div class="exception-head">
            <p class="panel-label">异常中心</p>
            <el-button link type="primary" :disabled="dispatcherNotificationUnread <= 0" @click="markAllDispatcherNotificationsRead">
              全部已读
            </el-button>
          </div>
          <div v-if="dispatcherNotifications.length > 0" class="exception-list">
            <button
              v-for="notice in dispatcherNotifications"
              :key="notice.id"
              type="button"
              class="exception-item"
              :class="{ unread: !notice.is_read }"
              @click="markDispatcherNotificationRead(notice)"
            >
              <p class="exception-title">{{ notice.title }}</p>
              <p class="exception-body">{{ notice.body || '无详情' }}</p>
              <small>{{ formatNotificationTime(notice.created_at) }}</small>
            </button>
          </div>
          <el-empty v-else description="暂无异常通知" :image-size="72" />
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
                  <img class="avatar" :src="getAvatarUrl(work.worker_avatar)" alt="工人头像" />
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
            <button
              v-for="row in workerStatusRows"
              :key="row.id"
              type="button"
              class="worker-row"
              @click="openWorkerDetail(row)"
            >
              <img class="worker-avatar" :src="getAvatarUrl(row.avatar)" alt="工人头像" />
              <span class="signal" :class="`signal-${row.tone}`"></span>
              <span class="worker-name">{{ row.name }}</span>
              <span class="worker-state">{{ row.state }}</span>
            </button>
          </div>
          <el-empty v-else description="当前仓库暂无工人" :image-size="72" />

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

    <el-dialog
      v-model="workerDetailVisible"
      width="760px"
      title="工人详情"
      @closed="closeWorkerDetail"
    >
      <div v-loading="workerDetailLoading">
        <template v-if="workerDetail">
          <section class="worker-detail-head">
            <img class="worker-detail-avatar" :src="getAvatarUrl(workerDetail.avatar)" alt="工人头像" />
            <div>
              <h3>{{ workerDetail.username }}</h3>
              <p>{{ workerDetail.email }}</p>
              <p>{{ workerDetail.phone || '电话未填写' }}</p>
            </div>
          </section>

          <el-descriptions :column="3" border>
            <el-descriptions-item label="拣货技能">{{ workerDetail.skill_picking }}</el-descriptions-item>
            <el-descriptions-item label="备货技能">{{ workerDetail.skill_staging }}</el-descriptions-item>
            <el-descriptions-item label="发货技能">{{ workerDetail.skill_shipping }}</el-descriptions-item>
            <el-descriptions-item label="待开始工单">{{ workerDetail.pending_count }}</el-descriptions-item>
            <el-descriptions-item label="进行中工单">{{ workerDetail.in_progress_count }}</el-descriptions-item>
            <el-descriptions-item label="在途总量">
              {{ workerDetail.active_work_order_count }}/{{ workerDetail.active_work_order_limit }}
            </el-descriptions-item>
            <el-descriptions-item label="个人说明" :span="3">
              {{ workerDetail.description || '暂无' }}
            </el-descriptions-item>
          </el-descriptions>

          <p class="panel-label detail-table-label">手头工单（待开始/进行中）</p>
          <el-table :data="workerDetail.work_orders || []" max-height="300" stripe>
            <el-table-column prop="order_no" label="订单号" min-width="130" />
            <el-table-column prop="customer_name" label="客户" min-width="120" />
            <el-table-column label="阶段" width="100">
              <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">{{ workOrderStatusText(row.status) }}</template>
            </el-table-column>
            <el-table-column label="优先级" width="90">
              <template #default="{ row }">{{ priorityText(row.priority) }}</template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="160">
              <template #default="{ row }">{{ formatCnDateTime(row.updated_at) }}</template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import { notificationsApi } from '../../api/common/notifications'
import { getAvatarUrl } from '../../utils/avatar'
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
const warehouseWorkers = ref([])
const detailMap = ref({})
const workOrderMap = ref({})
const sourceMap = ref({})
const selectedOrderId = ref(null)
const selectedStageId = ref(null)
const workerDetailVisible = ref(false)
const workerDetailLoading = ref(false)
const workerDetail = ref(null)
const dispatcherNotifications = ref([])
const dispatcherNotificationUnread = ref(0)

const queueTabs = [
  { key: 'in_progress', label: '进行中订单', tone: 'blue' },
  { key: 'pending', label: '待接单', tone: 'orange' },
  { key: 'alert', label: '告警 & 超时', tone: 'red' },
]

const alertSlaMinutes = 24 * 60

const queueCatalog = computed(() => {
  const inProgress = myOrders.value.filter((item) => item.status === 'in_progress').length
  const pending = pendingOrders.value.length
  const alert = myOrders.value.filter((item) => item.status === 'in_progress' && isCnOvertime(item.updated_at, alertSlaMinutes)).length
  return {
    in_progress: inProgress,
    pending,
    alert,
  }
})

const queueList = computed(() => {
  if (queueMode.value === 'pending') return pendingOrders.value
  if (queueMode.value === 'alert') {
    return myOrders.value.filter((item) => item.status === 'in_progress' && isCnOvertime(item.updated_at, alertSlaMinutes))
  }
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
  return [...warehouseWorkers.value]
    .map((worker) => {
      const pendingCount = Number(worker.pending_count || 0)
      const inProgressCount = Number(worker.in_progress_count || 0)
      return {
        id: worker.id,
        name: worker.username,
        avatar: worker.avatar,
        pending_count: pendingCount,
        in_progress_count: inProgressCount,
        active_work_order_count: Number(worker.active_work_order_count || 0),
        tone: workerToneByLoad(pendingCount, inProgressCount),
        state: `待开始 ${pendingCount} · 进行中 ${inProgressCount} · ${workerLoadLabel(pendingCount, inProgressCount)}`,
      }
    })
    .sort((a, b) => {
      const toneRank = { crimson: 0, red: 1, indigo: 2, blue: 3, amber: 4, lime: 5, green: 6, gray: 7 }
      const rankDiff = (toneRank[a.tone] ?? 99) - (toneRank[b.tone] ?? 99)
      if (rankDiff !== 0) return rankDiff
      return a.name.localeCompare(b.name, 'zh-CN')
    })
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
    const [myRes, pendingRes, workersRes] = await Promise.all([
      dispatcherOrdersApi.getMyOrders(),
      dispatcherOrdersApi.getPendingOrders(),
      dispatcherOrdersApi.getWorkers(),
    ])
    myOrders.value = (myRes.data.items || []).sort((a, b) => compareCnDateDesc(a.updated_at, b.updated_at))
    pendingOrders.value = (pendingRes.data.items || []).sort((a, b) => compareCnDateDesc(a.updated_at, b.updated_at))
    warehouseWorkers.value = workersRes.data || []

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

    await fetchDispatcherNotifications()
  } catch {
    myOrders.value = []
    pendingOrders.value = []
    warehouseWorkers.value = []
    detailMap.value = {}
    workOrderMap.value = {}
    sourceMap.value = {}
    selectedOrderId.value = null
    dispatcherNotifications.value = []
    dispatcherNotificationUnread.value = 0
  } finally {
    loading.value = false
  }
}

async function fetchDispatcherNotifications() {
  try {
    const res = await notificationsApi.listMyNotifications({ limit: 50 })
    const data = res.data?.data || {}
    dispatcherNotifications.value = (data.items || []).filter((item) => {
      const type = String(item.type || '')
      return type.includes('timeout') || type.includes('exception') || type.includes('inbound')
    })
    dispatcherNotificationUnread.value = dispatcherNotifications.value.filter((item) => !item.is_read).length
  } catch {
    dispatcherNotifications.value = []
    dispatcherNotificationUnread.value = 0
  }
}

async function markDispatcherNotificationRead(item) {
  if (!item || item.is_read) return
  try {
    await notificationsApi.markNotificationRead(item.id)
    item.is_read = true
    dispatcherNotificationUnread.value = Math.max(0, dispatcherNotificationUnread.value - 1)
  } catch {
    // no-op
  }
}

async function markAllDispatcherNotificationsRead() {
  try {
    await notificationsApi.markAllNotificationsRead()
    dispatcherNotifications.value = dispatcherNotifications.value.map((item) => ({ ...item, is_read: true }))
    dispatcherNotificationUnread.value = 0
  } catch {
    // no-op
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

function workerToneByLoad(pendingCount, inProgressCount) {
  if (inProgressCount >= 2 && pendingCount >= 3) return 'crimson'
  if (inProgressCount >= 2 || (inProgressCount >= 1 && pendingCount >= 4)) return 'red'
  if (inProgressCount === 1 && pendingCount >= 2) return 'indigo'
  if (inProgressCount === 1) return 'blue'
  if (pendingCount >= 3) return 'amber'
  if (pendingCount >= 1) return 'lime'
  return 'green'
}

function workerLoadLabel(pendingCount, inProgressCount) {
  const tone = workerToneByLoad(pendingCount, inProgressCount)
  return {
    crimson: '负载极高',
    red: '负载高',
    indigo: '负载偏高',
    blue: '执行中',
    amber: '待分配积压',
    lime: '待分配',
    green: '空闲',
  }[tone] || '未知'
}

function workerStateText(workOrder) {
  return `${stageText(workOrder.stage_type)} · ${workOrderStatusText(workOrder.status)}`
}

async function openWorkerDetail(workerRow) {
  workerDetailVisible.value = true
  workerDetailLoading.value = true
  workerDetail.value = null
  try {
    const res = await dispatcherOrdersApi.getWorkerDetail(workerRow.id)
    workerDetail.value = res.data
  } catch {
    ElMessage.error('获取工人详情失败，请稍后重试')
  } finally {
    workerDetailLoading.value = false
  }
}

function closeWorkerDetail() {
  workerDetailVisible.value = false
  workerDetail.value = null
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

function alertReasonText(order) {
  const diffMinutes = minutesSinceCn(order?.updated_at)
  if (Number.isNaN(diffMinutes)) return `超时阈值 ${alertSlaMinutes} 分钟`
  const overtimeMinutes = Math.max(0, diffMinutes - alertSlaMinutes)
  if (overtimeMinutes < 60) {
    return `超时 ${overtimeMinutes} 分钟（阈值 ${alertSlaMinutes} 分钟）`
  }
  const hours = Math.floor(overtimeMinutes / 60)
  const minutes = overtimeMinutes % 60
  return `超时 ${hours}小时${minutes}分钟（阈值 ${alertSlaMinutes} 分钟）`
}

function formatNotificationTime(value) {
  if (!value) return '-'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '-'
  return dt.toLocaleString('zh-CN', { hour12: false })
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

.exception-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.exception-list {
  display: grid;
  gap: 6px;
}

.exception-item {
  border: 1px solid #d9cdbb;
  background: #fffaf1;
  border-radius: 8px;
  padding: 8px;
  text-align: left;
  cursor: pointer;
}

.exception-item.unread {
  border-color: #e4ab56;
  background: #fff5e5;
}

.exception-title,
.exception-body {
  margin: 0;
}

.exception-title {
  font-size: 12px;
  font-weight: 700;
  color: #5a4121;
}

.exception-body {
  margin-top: 4px;
  font-size: 12px;
  color: #6f6456;
}

.exception-item small {
  margin-top: 4px;
  display: inline-block;
  font-size: 11px;
  color: #8f877a;
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
  object-fit: cover;
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
  width: 100%;
  border: 1px solid #e2d9cb;
  border-radius: 10px;
  background: #fffdf9;
  padding: 8px;
  display: grid;
  grid-template-columns: 30px 10px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.worker-row:hover {
  border-color: #b2c5dd;
  box-shadow: 0 0 0 1px rgba(70, 112, 168, 0.2) inset;
}

.worker-avatar {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  object-fit: cover;
}

.worker-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.signal-crimson {
  background: #7f1d1d;
}

.signal-indigo {
  background: #4f46e5;
}

.signal-lime {
  background: #65a30d;
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

.worker-detail-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.worker-detail-head h3,
.worker-detail-head p {
  margin: 0;
}

.worker-detail-head p + p {
  margin-top: 4px;
}

.worker-detail-avatar {
  width: 52px;
  height: 52px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid #d9e1ec;
}

.detail-table-label {
  margin-top: 12px;
  margin-bottom: 8px;
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
