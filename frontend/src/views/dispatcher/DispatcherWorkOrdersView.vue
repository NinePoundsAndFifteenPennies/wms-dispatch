<template>
  <div class="dispatcher-page" v-loading="loading">
    <section class="page-hero">
      <p class="section-kicker">Work Order Center</p>
      <h2>工单中心</h2>
      <p>按状态筛选、按时间排序并快速检索工单，超时告警暂由前端规则占位提示。</p>
    </section>

    <section class="toolbar">
      <el-select v-model="statusFilter" class="toolbar-item" placeholder="按状态筛选" clearable>
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已终止" value="terminated" />
      </el-select>

      <el-select v-model="sortBy" class="toolbar-item" placeholder="按时间字段">
        <el-option label="更新时间" value="updated_at" />
        <el-option label="创建时间" value="created_at" />
        <el-option label="截止时间" value="deadline" />
      </el-select>

      <el-select v-model="sortOrder" class="toolbar-item order-item" placeholder="排序方向">
        <el-option label="从新到旧" value="desc" />
        <el-option label="从旧到新" value="asc" />
      </el-select>

      <OrderSearchBox
        v-model="search"
        placeholder="搜索工单ID/订单号/客户/工人"
      />
    </section>

    <section class="board-grid">
      <article v-for="column in columns" :key="column.key" class="board-column">
        <header>
          <p class="section-kicker">{{ column.label }}</p>
          <strong>{{ getItems(column.matcher).length }} 条</strong>
        </header>

        <div class="board-list">
          <div
            v-for="item in getItems(column.matcher)"
            :key="item.id"
            class="board-card"
            :class="statusClass(item.status)"
            @click="openOrder(item.order_id)"
          >
            <div class="card-head">
              <strong>#{{ item.id }}</strong>
              <span class="priority-chip">{{ priorityText(item.priority) }}</span>
            </div>
            <p class="card-title">{{ item.order_no || `订单${item.order_id}` }} · {{ item.customer_name || '-' }}</p>
            <p>{{ stageText(item.stage_type) }} · {{ item.worker_name || '-' }}</p>
            <div class="meta-line">
              <small>{{ workOrderStatusText(item.status) }}</small>
              <small>{{ sortLabel }} {{ formatCnDateTime(item[sortBy]) }}</small>
            </div>
            <small>截止 {{ formatCnDateTime(item.deadline) }}</small>
            <small v-if="item._overtime" class="alert-text">超时告警（占位）</small>
          </div>
          <p v-if="!getItems(column.matcher).length" class="empty-tip">暂无数据</p>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import OrderSearchBox from '../../components/shared/OrderSearchBox.vue'
import { formatCnDateTime, isCnOvertime, parseCnDate } from '../../utils/cnTime'

const router = useRouter()
const loading = ref(false)
const items = ref([])
const search = ref('')
const statusFilter = ref('')
const sortBy = ref('updated_at')
const sortOrder = ref('desc')
let searchTimer = null
let lastRequestId = 0

const columns = [
  { key: 'pending', label: '待处理', matcher: (item) => item.status === 'pending' && !item._overtime },
  { key: 'active', label: '进行中', matcher: (item) => item.status === 'in_progress' && !item._overtime },
  { key: 'risk', label: '超时告警', matcher: (item) => item._overtime },
  { key: 'done', label: '已完成/已终止', matcher: (item) => ['completed', 'terminated'].includes(item.status) },
]

const normalizedItems = computed(() =>
  (items.value || []).map((item) => ({
    ...item,
    _overtime: isOvertimePlaceholder(item),
  }))
)

const sortLabel = computed(() => {
  return {
    updated_at: '更新于',
    created_at: '创建于',
    deadline: '排序时间',
  }[sortBy.value]
})

async function fetchWorkOrders() {
  const requestId = ++lastRequestId
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getWorkOrders({
      search: search.value || undefined,
      status: statusFilter.value || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    })
    if (requestId === lastRequestId) {
      items.value = res.data?.items || []
    }
  } catch (error) {
    if (requestId === lastRequestId) {
      ElMessage.error(error?.response?.data?.detail || '工单中心加载失败，请稍后重试')
    }
  } finally {
    if (requestId === lastRequestId) {
      loading.value = false
    }
  }
}

function getItems(matcher) {
  return normalizedItems.value.filter(matcher)
}

function statusClass(status) {
  return {
    pending: 'status-pending',
    in_progress: 'status-active',
    completed: 'status-done',
    terminated: 'status-alert',
  }[status]
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

function stageText(stage) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[stage] || stage
}

function priorityText(priority) {
  return {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级',
  }[priority] || priority
}

function isOvertimePlaceholder(item) {
  if (!item || ['completed', 'terminated'].includes(item.status)) {
    return false
  }
  if (item.deadline) {
    const parsed = parseCnDate(item.deadline)
    if (parsed) {
      return parsed.getTime() < Date.now()
    }
  }
  return isCnOvertime(item.created_at, 180)
}

function openOrder(orderId) {
  router.push({ name: 'dispatcher-my-order-detail', params: { orderId } })
}

onMounted(fetchWorkOrders)

watch([statusFilter, sortBy, sortOrder], () => {
  fetchWorkOrders()
})

watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchWorkOrders()
  }, 250)
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.dispatcher-page {
  display: grid;
  gap: 14px;
}

.page-hero,
.toolbar,
.board-column {
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.88);
}

.page-hero {
  padding: 18px 20px;
}

.page-hero h2,
.page-hero p,
.section-kicker {
  margin: 0;
}

.section-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.page-hero h2 {
  margin-top: 6px;
  font-size: 24px;
}

.page-hero p:last-of-type:not(.mock-badge) {
  margin-top: 8px;
  color: var(--dispatcher-muted);
  line-height: 1.6;
}

.toolbar {
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-item {
  width: 170px;
}

.order-item {
  width: 130px;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.board-column {
  padding: 14px;
}

.board-column header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.board-list {
  display: grid;
  gap: 10px;
}

.board-card {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--dispatcher-border);
  background: var(--dispatcher-surface);
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.board-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}

.card-head,
.board-card p,
.board-card small {
  margin: 0;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.card-title {
  margin-top: 8px;
  font-weight: 600;
}

.board-card small {
  display: block;
  margin-top: 4px;
  color: var(--dispatcher-muted);
}

.meta-line {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.priority-chip {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
  font-size: 11px;
}

.alert-text {
  color: #a54343;
  font-weight: 600;
}

.empty-tip {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--dispatcher-soft);
  text-align: center;
  padding: 8px 0;
}

.status-pending {
  border-left: 4px solid #bb8137;
}

.status-active {
  border-left: 4px solid #35679c;
}

.status-alert {
  border-left: 4px solid #a54343;
}

.status-done {
  border-left: 4px solid #5f7c48;
}

@media (max-width: 1180px) {
  .board-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .toolbar-item,
  .order-item {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .board-grid {
    grid-template-columns: 1fr;
  }
}
</style>
