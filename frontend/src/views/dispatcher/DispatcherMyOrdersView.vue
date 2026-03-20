<template>
  <div class="dispatcher-orders-page">
    <section class="page-head">
      <h3>我的订单</h3>
      <OrderSearchBox v-model="search" />
    </section>

    <section class="columns-grid" v-loading="loading">
      <PriorityOrderColumn
        title="高优先级"
        :items="grouped.high"
        :sort-order="sortOrder.high"
        @sort-change="sortOrder.high = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>

      <PriorityOrderColumn
        title="中优先级"
        :items="grouped.medium"
        :sort-order="sortOrder.medium"
        @sort-change="sortOrder.medium = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>

      <PriorityOrderColumn
        title="低优先级"
        :items="grouped.low"
        :sort-order="sortOrder.low"
        @sort-change="sortOrder.low = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>
    </section>

    <el-dialog v-model="detailVisible" title="订单详情（我的订单）" width="980px">
      <el-descriptions v-if="detail" :column="3" border>
        <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
        <el-descriptions-item label="总件数">{{ detail.total_items }}</el-descriptions-item>
        <el-descriptions-item label="总金额(分)">{{ detail.total_amount }}</el-descriptions-item>
      </el-descriptions>

      <DetailInfoBlock title="阶段进度" v-if="detail">
        <el-table :data="detail.stages || []" stripe>
          <el-table-column prop="stage_type" label="阶段" min-width="120" />
          <el-table-column prop="status" label="状态" min-width="120" />
          <el-table-column label="工单概况" min-width="240">
            <template #default="{ row }">
              总{{ row.work_orders.total }} / 待{{ row.work_orders.pending }} / 进{{ row.work_orders.in_progress }} / 完{{
                row.work_orders.completed
              }}
            </template>
          </el-table-column>
          <el-table-column prop="completion_type" label="完成方式" min-width="100" />
        </el-table>
      </DetailInfoBlock>

      <DetailInfoBlock title="工单总览" v-if="detail">
        <p class="summary-text">
          总数 {{ detail.work_order_summary.total }}，待处理 {{ detail.work_order_summary.pending }}，进行中
          {{ detail.work_order_summary.in_progress }}，已完成 {{ detail.work_order_summary.completed }}，已终止
          {{ detail.work_order_summary.terminated }}
        </p>
      </DetailInfoBlock>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import DispatcherOrderCard from '../../components/dispatcher/DispatcherOrderCard.vue'
import PriorityOrderColumn from '../../components/dispatcher/PriorityOrderColumn.vue'
import DetailInfoBlock from '../../components/shared/DetailInfoBlock.vue'
import OrderSearchBox from '../../components/shared/OrderSearchBox.vue'

const loading = ref(false)
const orders = ref([])
const search = ref('')
const detailVisible = ref(false)
const detail = ref(null)

const sortOrder = reactive({
  high: 'desc',
  medium: 'desc',
  low: 'desc',
})

const filtered = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return orders.value
  return orders.value.filter(
    (item) =>
      String(item.order_no).toLowerCase().includes(keyword) ||
      String(item.customer_name).toLowerCase().includes(keyword)
  )
})

const grouped = computed(() => {
  const groups = { high: [], medium: [], low: [] }
  for (const item of filtered.value) {
    if (groups[item.priority]) groups[item.priority].push(item)
  }
  for (const key of ['high', 'medium', 'low']) {
    groups[key].sort((a, b) => {
      const diff = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
      return sortOrder[key] === 'asc' ? diff : -diff
    })
  }
  return groups
})

async function fetchOrders() {
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getMyOrders({ search: search.value || undefined })
    orders.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

async function openDetail(orderId) {
  const res = await dispatcherOrdersApi.getMyOrderDetail(orderId)
  detail.value = res.data
  detailVisible.value = true
}

function statusText(status) {
  return {
    pending_acceptance: '待接单',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }[status] || status
}

function priorityText(priority) {
  return {
    high: '高',
    medium: '中',
    low: '低',
  }[priority] || priority
}

onMounted(fetchOrders)
watch(search, fetchOrders)
</script>

<style scoped>
.dispatcher-orders-page {
  display: grid;
  gap: 12px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.page-head h3 {
  margin: 0;
}

.columns-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-text {
  margin: 0;
}

@media (max-width: 980px) {
  .columns-grid {
    grid-template-columns: 1fr;
  }
}
</style>
