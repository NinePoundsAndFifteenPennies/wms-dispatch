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
      <el-descriptions-item label="总金额(元)">{{ detail.total_amount }}</el-descriptions-item>
      <el-descriptions-item label="订单备注" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
    </el-descriptions>

    <DetailInfoBlock title="阶段进度" v-if="detail">
      <el-table :data="detail.stages || []" stripe>
        <el-table-column label="阶段" min-width="120">
          <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">{{ stageStatusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="工单概况" min-width="240">
          <template #default="{ row }">
            总{{ row.work_orders.total }} / 待{{ row.work_orders.pending }} / 进{{ row.work_orders.in_progress }} / 完{{
              row.work_orders.completed
            }}
          </template>
        </el-table-column>
        <el-table-column label="完成方式" min-width="100">
          <template #default="{ row }">{{ completionTypeText(row.completion_type) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="row.status === 'completed' || stageCompleteSubmitting"
              @click="openManualComplete(row)"
            >
              手动标记完成
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </DetailInfoBlock>

    <DetailInfoBlock title="创建工单" v-if="detail">
      <el-form :model="createForm" label-width="100px" class="create-form">
        <el-form-item label="阶段">
          <el-select v-model="createForm.stage_id" placeholder="选择阶段" class="w-full">
            <el-option
              v-for="stage in detail.stages || []"
              :key="stage.id"
              :label="`${stageText(stage.stage_type)}（${stageStatusText(stage.status)}）`"
              :value="stage.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工人">
          <el-select v-model="createForm.worker_id" filterable placeholder="选择工人" class="w-full">
            <el-option
              v-for="worker in workers"
              :key="worker.id"
              :label="`${worker.username}（拣${worker.skill_picking}/备${worker.skill_staging}/发${worker.skill_shipping}）`"
              :value="worker.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" class="w-full">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务备注">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="选填，说明执行要求" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creatingWorkOrder" @click="submitCreateWorkOrder">创建工单</el-button>
          <el-button @click="resetCreateForm">重置</el-button>
        </el-form-item>
      </el-form>
    </DetailInfoBlock>

    <DetailInfoBlock title="工单列表" v-if="detail">
      <el-table :data="workOrders" stripe>
        <el-table-column prop="id" label="工单ID" width="90" />
        <el-table-column label="阶段" min-width="100">
          <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column prop="worker_name" label="工人" min-width="120" />
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">{{ workOrderStatusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="优先级" min-width="100">
          <template #default="{ row }">{{ priorityText(row.priority) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!['pending', 'in_progress'].includes(row.status) || terminateSubmitting"
              @click="openTerminate(row)"
            >
              终止
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </DetailInfoBlock>

    <el-dialog v-model="terminateDialogVisible" title="终止工单" width="500px">
      <el-input v-model="terminateReason" type="textarea" :rows="3" placeholder="请输入终止原因" />
      <template #footer>
        <el-button @click="terminateDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="terminateSubmitting" @click="submitTerminate">确认终止</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manualCompleteVisible" title="手动标记阶段完成" width="520px">
      <p class="summary-text" v-if="selectedStage">
        阶段：{{ stageText(selectedStage.stage_type) }}，当前状态：{{ stageStatusText(selectedStage.status) }}
      </p>
      <el-input v-model="manualCompleteRemark" type="textarea" :rows="3" placeholder="请输入手动完成原因" />
      <template #footer>
        <el-button @click="manualCompleteVisible = false">取消</el-button>
        <el-button type="primary" :loading="stageCompleteSubmitting" @click="submitManualComplete">确认完成</el-button>
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
const detail = ref(null)
const workOrders = ref([])
const workers = ref([])
const creatingWorkOrder = ref(false)
const terminateDialogVisible = ref(false)
const terminateSubmitting = ref(false)
const stageCompleteSubmitting = ref(false)
const manualCompleteVisible = ref(false)
const selectedStage = ref(null)
const selectedWorkOrderId = ref(null)
const terminateReason = ref('')
const manualCompleteRemark = ref('')

const createForm = ref({
  stage_id: null,
  worker_id: null,
  priority: 'medium',
  description: '',
})

async function fetchDetail() {
  loading.value = true
  try {
    const [detailRes, workersRes, workOrdersRes] = await Promise.all([
      dispatcherOrdersApi.getMyOrderDetail(route.params.orderId),
      dispatcherOrdersApi.getWorkers(),
      dispatcherOrdersApi.getOrderWorkOrders(route.params.orderId),
    ])

    detail.value = detailRes.data
    workers.value = workersRes.data || []
    workOrders.value = workOrdersRes.data?.items || []

    const firstStage = (detail.value?.stages || []).find((item) => item.status !== 'completed')
    if (!createForm.value.stage_id && firstStage) {
      createForm.value.stage_id = firstStage.id
    }
    if (!createForm.value.worker_id && workers.value.length > 0) {
      createForm.value.worker_id = workers.value[0].id
    }
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

function stageText(stage) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[stage] || stage
}

function stageStatusText(status) {
  return {
    not_started: '未开始',
    in_progress: '进行中',
    completed: '已完成',
  }[status] || status
}

function completionTypeText(type) {
  return {
    auto: '自动',
    manual: '手动',
  }[type] || '-'
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

function resetCreateForm() {
  createForm.value = {
    stage_id: detail.value?.stages?.find((item) => item.status !== 'completed')?.id || null,
    worker_id: workers.value?.[0]?.id || null,
    priority: 'medium',
    description: '',
  }
}

async function submitCreateWorkOrder() {
  if (!createForm.value.stage_id || !createForm.value.worker_id) {
    ElMessage.warning('请选择阶段和工人')
    return
  }

  creatingWorkOrder.value = true
  try {
    await dispatcherOrdersApi.createWorkOrder(route.params.orderId, {
      stage_id: createForm.value.stage_id,
      worker_id: createForm.value.worker_id,
      priority: createForm.value.priority,
      description: createForm.value.description || null,
    })
    ElMessage.success('工单创建成功')
    resetCreateForm()
    await fetchDetail()
  } finally {
    creatingWorkOrder.value = false
  }
}

function openTerminate(row) {
  selectedWorkOrderId.value = row.id
  terminateReason.value = ''
  terminateDialogVisible.value = true
}

async function submitTerminate() {
  if (!selectedWorkOrderId.value) return
  if (!terminateReason.value.trim()) {
    ElMessage.warning('请输入终止原因')
    return
  }

  terminateSubmitting.value = true
  try {
    await dispatcherOrdersApi.terminateWorkOrder(selectedWorkOrderId.value, {
      reason: terminateReason.value.trim(),
    })
    terminateDialogVisible.value = false
    ElMessage.success('工单已终止')
    await fetchDetail()
  } finally {
    terminateSubmitting.value = false
  }
}

function openManualComplete(stage) {
  selectedStage.value = stage
  manualCompleteRemark.value = ''
  manualCompleteVisible.value = true
}

async function submitManualComplete() {
  if (!selectedStage.value) return
  if (!manualCompleteRemark.value.trim()) {
    ElMessage.warning('请输入手动完成原因')
    return
  }

  stageCompleteSubmitting.value = true
  try {
    await dispatcherOrdersApi.manualCompleteStage(route.params.orderId, selectedStage.value.id, {
      remark: manualCompleteRemark.value.trim(),
    })
    manualCompleteVisible.value = false
    ElMessage.success('阶段已手动标记为完成')
    await fetchDetail()
  } finally {
    stageCompleteSubmitting.value = false
  }
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

.create-form {
  max-width: 720px;
}

.w-full {
  width: 100%;
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
