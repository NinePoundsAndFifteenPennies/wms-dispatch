<template>
  <div class="detail-page" v-loading="loading">
    <section class="page-head">
      <el-button @click="goBack">返回我的订单</el-button>
    </section>

    <el-descriptions v-if="detail" :column="3" border>
      <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
      <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
      <el-descriptions-item label="客户联系方式">{{ detail.customer_contact || '-' }}</el-descriptions-item>
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import DetailInfoBlock from '../../components/shared/DetailInfoBlock.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detail = ref(null)

async function fetchDetail() {
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getMyOrderDetail(route.params.orderId)
    detail.value = res.data
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push({ name: 'dispatcher-my-orders' })
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

onMounted(fetchDetail)
</script>

<style scoped>
.detail-page {
  display: grid;
  gap: 12px;
  background: transparent;
}

.page-head {
  display: flex;
  gap: 8px;
}

.summary-text {
  margin: 0;
}

:deep(.el-descriptions__label) {
  color: #5b4d3d;
  font-weight: 600;
}

:deep(.el-descriptions__content) {
  color: #2b2721;
}

:deep(.el-table th.el-table__cell) {
  background: #f5ece0;
  color: #6a5338;
}
</style>
