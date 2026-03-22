<template>
  <div class="detail-page" v-loading="loading">
    <section class="page-head">
      <el-button @click="goBack">返回接单中心</el-button>
      <el-button type="primary" :loading="accepting" @click="acceptOrder">
        {{ accepting ? '检测库存并接单中...' : '接单' }}
      </el-button>
    </section>
    <p v-if="accepting" class="accept-hint">正在检测可用库存并锁定预留，请稍候...</p>

    <el-descriptions v-if="detail" :column="3" border>
      <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
      <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
      <el-descriptions-item label="客户联系方式">{{ detail.customer_contact || '-' }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
      <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
      <el-descriptions-item label="总件数">{{ detail.total_items }}</el-descriptions-item>
      <el-descriptions-item label="总金额(元)">{{ detail.total_amount }}</el-descriptions-item>
      <el-descriptions-item label="备注" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
    </el-descriptions>

    <DetailInfoBlock title="订单明细" v-if="detail">
      <el-table :data="detail.items" stripe>
        <el-table-column prop="product_sku" label="SKU" width="130" />
        <el-table-column prop="product_name" label="产品名称" min-width="200" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column label="技能要求" min-width="260">
          <template #default="{ row }">
            拣{{ row.req_skill_picking }} / 备{{ row.req_skill_staging }} / 发{{ row.req_skill_shipping }}
          </template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价(元)" width="110" />
      </el-table>
    </DetailInfoBlock>

    <el-dialog v-model="shortageDialogVisible" title="可用库存不足" width="680px">
      <p class="shortage-intro">以下商品可用库存不足，无法接单：</p>
      <el-table :data="shortageItems" border size="small">
        <el-table-column prop="sku" label="SKU" min-width="120" />
        <el-table-column prop="product_name" label="产品名称" min-width="160" />
        <el-table-column prop="required_qty" label="需求量" width="90" />
        <el-table-column prop="available_qty" label="可用量" width="100" />
        <el-table-column prop="shortage_qty" label="缺口" width="90" />
      </el-table>
      <template #footer>
        <el-button @click="shortageDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="goInventoryCenter">前往库存中心</el-button>
      </template>
    </el-dialog>
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
const shortageDialogVisible = ref(false)
const shortageItems = ref([])

async function fetchDetail() {
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getPendingOrderDetail(route.params.orderId)
    detail.value = res.data
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取订单详情失败')
  } finally {
    loading.value = false
  }
}

async function acceptOrder() {
  accepting.value = true
  try {
    ElMessage.info('正在检测可用库存...')
    await dispatcherOrdersApi.acceptOrder(route.params.orderId, { silentError: true })
    ElMessage.success('接单成功')
    router.push({ name: 'dispatcher-my-order-detail', params: { orderId: route.params.orderId } })
  } catch (error) {
    const shortages = error.response?.data?.data?.shortages
    if (Array.isArray(shortages) && shortages.length > 0) {
      shortageItems.value = shortages
      shortageDialogVisible.value = true
      return
    }
    ElMessage.error(error.response?.data?.message || '接单失败')
  } finally {
    accepting.value = false
  }
}

function goInventoryCenter() {
  shortageDialogVisible.value = false
  router.push({ name: 'dispatcher-inventory' })
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

.accept-hint {
  margin: 0;
  color: #7a6348;
  font-size: 13px;
}

.shortage-intro {
  margin: 0 0 12px;
  color: #5f5444;
  font-size: 13px;
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
