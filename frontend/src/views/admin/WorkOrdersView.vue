<template>
  <div class="work-order-page" v-loading="loading">
    <header>
      <h3>我的工单</h3>
      <p v-if="isWorker">按状态推进你被分配的工单。</p>
      <p v-else>管理员视图暂不接入工人执行接口。</p>
    </header>

    <el-empty v-if="!isWorker" description="当前账号为管理员，请使用调度员端进行派单与管理" />

    <template v-else>
      <el-table :data="workOrders" stripe>
        <el-table-column prop="id" label="工单ID" width="90" />
        <el-table-column prop="order_no" label="订单号" min-width="120" />
        <el-table-column label="阶段" min-width="100">
          <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">{{ workOrderStatusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="优先级" min-width="100">
          <template #default="{ row }">{{ priorityText(row.priority) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="row.status !== 'pending' || submitting"
              @click="startWorkOrder(row)"
            >
              开始
            </el-button>
            <el-button
              size="small"
              type="success"
              plain
              :disabled="row.status !== 'in_progress' || submitting"
              @click="openCompleteDialog(row)"
            >
              完成
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="completeDialogVisible" title="完成工单" width="520px">
        <el-form label-width="90px">
          <el-form-item label="备注类型">
            <el-select v-model="completeForm.note_type" class="w-full">
              <el-option label="正常" value="normal" />
              <el-option label="破损" value="damaged" />
              <el-option label="数量不符" value="qty_mismatch" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注内容">
            <el-input
              v-model="completeForm.content"
              type="textarea"
              :rows="3"
              placeholder="可选；填写后将写入工单备注"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="completeDialogVisible = false">取消</el-button>
          <el-button type="success" :loading="submitting" @click="completeWorkOrder">确认完成</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { workerWorkOrdersApi } from '../../api/worker/workOrders'

const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const workOrders = ref([])
const completeDialogVisible = ref(false)
const selectedWorkOrderId = ref(null)
const completeForm = ref({ note_type: 'normal', content: '' })

const isWorker = computed(() => authStore.currentUser?.role === 'worker')

async function fetchWorkOrders() {
  if (!isWorker.value) return
  loading.value = true
  try {
    const res = await workerWorkOrdersApi.getMyWorkOrders()
    workOrders.value = res.data?.items || []
  } finally {
    loading.value = false
  }
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
    high: '高',
    medium: '中',
    low: '低',
  }[priority] || priority
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

async function startWorkOrder(row) {
  submitting.value = true
  try {
    await workerWorkOrdersApi.startWorkOrder(row.id)
    ElMessage.success('工单已开始执行')
    await fetchWorkOrders()
  } finally {
    submitting.value = false
  }
}

function openCompleteDialog(row) {
  selectedWorkOrderId.value = row.id
  completeForm.value = { note_type: 'normal', content: '' }
  completeDialogVisible.value = true
}

async function completeWorkOrder() {
  if (!selectedWorkOrderId.value) return
  submitting.value = true
  try {
    const payload = completeForm.value.content.trim()
      ? {
          note: {
            note_type: completeForm.value.note_type,
            content: completeForm.value.content.trim(),
          },
        }
      : { note: null }

    await workerWorkOrdersApi.completeWorkOrder(selectedWorkOrderId.value, payload)
    completeDialogVisible.value = false
    ElMessage.success('工单已完成')
    await fetchWorkOrders()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchWorkOrders)
</script>

<style scoped>
header {
  margin-bottom: 12px;
}

h3 {
  margin: 0;
  font-size: 22px;
}

p {
  margin: 6px 0 0;
  color: #475569;
}

.w-full {
  width: 100%;
}
</style>
