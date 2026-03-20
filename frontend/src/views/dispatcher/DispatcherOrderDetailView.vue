<template>
  <div class="detail-page" v-loading="loading">
    <section class="page-head">
      <el-button @click="goBack">返回接单中心</el-button>
      <el-button type="primary" :loading="accepting" @click="acceptOrder">接单</el-button>
    </section>

    <el-descriptions v-if="detail" :column="3" border>
      <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
      <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
      <el-descriptions-item label="客户联系方式">{{ detail.customer_contact || '-' }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
      <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
      <el-descriptions-item label="总件数">{{ detail.total_items }}</el-descriptions-item>
      <el-descriptions-item label="总金额(分)">{{ detail.total_amount }}</el-descriptions-item>
      <el-descriptions-item label="备注" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
    </el-descriptions>

    <DetailInfoBlock title="订单明细" v-if="detail">
      <el-table :data="detail.items" stripe>
        <el-table-column prop="product_sku" label="SKU" width="130" />
        <el-table-column prop="product_name" label="产品名称" min-width="200" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column prop="unit_price" label="单价(分)" width="110" />
      </el-table>
    </DetailInfoBlock>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import DetailInfoBlock from '../../components/shared/DetailInfoBlock.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const accepting = ref(false)
const detail = ref(null)

async function fetchDetail() {
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getPendingOrderDetail(route.params.orderId)
    detail.value = res.data
  } finally {
    loading.value = false
  }
}

async function acceptOrder() {
  accepting.value = true
  try {
    await dispatcherOrdersApi.acceptOrder(route.params.orderId)
    ElMessage.success('接单成功')
    router.push({ name: 'dispatcher-my-order-detail', params: { orderId: route.params.orderId } })
  } finally {
    accepting.value = false
  }
}

function goBack() {
  router.push({ name: 'dispatcher-orders' })
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
