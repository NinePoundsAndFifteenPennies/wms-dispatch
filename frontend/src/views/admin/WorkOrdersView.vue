<template>
  <div class="work-order-page" v-loading="loading">
    <header>
      <h3>工单总览（只读）</h3>
      <p>管理员可按状态、阶段、优先级、人员与关键词进行多维筛选。</p>
    </header>

    <section class="toolbar">
      <el-input
        v-model="filters.search"
        class="toolbar-item"
        clearable
        :placeholder="searchPlaceholder"
      />
      <el-select v-model="filters.status" clearable placeholder="状态" class="toolbar-item mini">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已终止" value="terminated" />
      </el-select>
      <el-select v-model="filters.stage_type" clearable placeholder="阶段" class="toolbar-item mini">
        <el-option label="拣货" value="picking" />
        <el-option label="备货" value="staging" />
        <el-option label="发货" value="shipping" />
      </el-select>
      <el-select v-model="filters.priority" clearable placeholder="优先级" class="toolbar-item mini">
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
      </el-select>
      <el-input
        v-if="isAdmin"
        v-model.number="filters.worker_id"
        type="number"
        min="1"
        class="toolbar-item mini"
        clearable
        placeholder="工人ID"
      />
      <el-input
        v-if="isAdmin"
        v-model.number="filters.dispatcher_id"
        type="number"
        min="1"
        class="toolbar-item mini"
        clearable
        placeholder="调度员ID"
      />
      <el-button type="primary" @click="refresh">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <el-table :data="tableRows" stripe>
      <el-table-column prop="id" label="工单ID" width="90" />
      <el-table-column prop="order_no" label="订单号" min-width="120" />
      <el-table-column label="阶段" min-width="100">
        <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
      </el-table-column>
      <el-table-column label="状态" min-width="110">
        <template #default="{ row }">
          <el-tag :class="statusTagClass(row.status)" effect="light" round>
            {{ workOrderStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" min-width="100">
        <template #default="{ row }">{{ priorityText(row.priority) }}</template>
      </el-table-column>
      <el-table-column v-if="isAdmin" prop="warehouse_name" label="仓库" min-width="140" />
      <el-table-column v-if="isAdmin" prop="worker_name" label="工人" min-width="120" />
      <el-table-column prop="dispatcher_name" label="调度员" min-width="120" />
      <el-table-column prop="description" label="备注" min-width="180" show-overflow-tooltip />
      <el-table-column label="更新时间" min-width="170">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="refresh"
        @current-change="refresh"
      />
    </div>

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

    <el-dialog v-model="workerDetailVisible" title="工单详情" width="720px">
      <el-descriptions v-if="selectedWorkOrder" :column="2" border>
        <el-descriptions-item label="工单ID">{{ selectedWorkOrder.id }}</el-descriptions-item>
        <el-descriptions-item label="订单号">{{ selectedWorkOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="阶段">{{ stageText(selectedWorkOrder.stage_type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ workOrderStatusText(selectedWorkOrder.status) }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(selectedWorkOrder.priority) }}</el-descriptions-item>
        <el-descriptions-item label="调度员">{{ selectedWorkOrder.dispatcher_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="派发时间">{{ formatDate(selectedWorkOrder.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="截止时间">{{ formatDate(selectedWorkOrder.deadline) }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="selectedWorkOrder && parsedOverrideInfo.hasOverride" class="override-box">
        <p class="override-title">风险放行信息</p>
        <p>风险类型：{{ parsedOverrideInfo.riskLabels.join(' / ') || '-' }}</p>
        <p>放行原因：{{ parsedOverrideInfo.overrideReason || '-' }}</p>
      </div>

      <div class="extra-box" v-if="selectedWorkOrder">
        <p class="override-title">备注详情</p>
        <p>{{ parsedOverrideInfo.remarkText || '无备注' }}</p>
      </div>

      <template #footer>
        <el-button @click="workerDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { adminWorkOrdersApi } from '../../api/admin/workOrders'
import { formatCnDateTime } from '../../utils/cnTime'

const route = useRoute()
const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const workOrders = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const completeDialogVisible = ref(false)
const selectedWorkOrderId = ref(null)
const completeForm = ref({ note_type: 'normal', content: '' })
const workerDetailVisible = ref(false)
const selectedWorkOrder = ref(null)

const filters = reactive({
  search: '',
  status: '',
  stage_type: '',
  priority: '',
  worker_id: undefined,
  dispatcher_id: undefined,
})

const isAdmin = computed(() => authStore.currentUser?.role === 'admin')
const tableRows = computed(() => workOrders.value)
const searchPlaceholder = computed(() => '搜索 工单ID/订单号/仓库/工人/调度员')

const parsedOverrideInfo = computed(() => {
  const raw = String(selectedWorkOrder.value?.description || '').trim()
  if (!raw) {
    return {
      hasOverride: false,
      riskCodes: [],
      riskLabels: [],
      overrideReason: '',
      remarkText: '',
    }
  }

  const matched = raw.match(/^\[override\]\[([^\]]+)\]\s*([^\n]*)(?:\n([\s\S]*))?$/)
  if (!matched) {
    return {
      hasOverride: false,
      riskCodes: [],
      riskLabels: [],
      overrideReason: '',
      remarkText: raw,
    }
  }

  const riskCodeMap = {
    skill_gap: '技能风险',
    worker_overload: '负载风险',
  }
  const riskCodes = (matched[1] || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  return {
    hasOverride: true,
    riskCodes,
    riskLabels: riskCodes.map((item) => riskCodeMap[item] || item),
    overrideReason: (matched[2] || '').trim(),
    remarkText: (matched[3] || '').trim(),
  }
})

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

function statusTagClass(status) {
  return {
    pending: 'tag-pending',
    in_progress: 'tag-progress',
    completed: 'tag-completed',
    terminated: 'tag-terminated',
  }[status]
}

function formatDate(value) {
  return formatCnDateTime(value)
}

function openWorkOrderDetail(row) {
  selectedWorkOrder.value = row
  workerDetailVisible.value = true
}

function sanitizePositiveInt(value) {
  const num = Number(value)
  return Number.isInteger(num) && num > 0 ? num : undefined
}

function buildQueryParams() {
  return {
    search: filters.search || undefined,
    status: filters.status || undefined,
    stage_type: filters.stage_type || undefined,
    priority: filters.priority || undefined,
    worker_id: sanitizePositiveInt(filters.worker_id),
    dispatcher_id: sanitizePositiveInt(filters.dispatcher_id),
    page: currentPage.value,
    page_size: pageSize.value,
  }
}

function syncFiltersFromRoute() {
  const {
    search,
    status,
    stage_type: stageType,
    priority,
    worker_id: workerId,
    dispatcher_id: dispatcherId,
  } = route.query

  filters.search = typeof search === 'string' ? search : ''
  filters.status = typeof status === 'string' ? status : ''
  filters.stage_type = typeof stageType === 'string' ? stageType : ''
  filters.priority = typeof priority === 'string' ? priority : ''
  filters.worker_id = workerId ? Number(workerId) : undefined
  filters.dispatcher_id = dispatcherId ? Number(dispatcherId) : undefined
  currentPage.value = 1
}

async function fetchAdminWorkOrders() {
  loading.value = true
  try {
    const res = await adminWorkOrdersApi.getWorkOrders(buildQueryParams())
    workOrders.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await fetchAdminWorkOrders()
}

function resetFilters() {
  filters.search = ''
  filters.status = ''
  filters.stage_type = ''
  filters.priority = ''
  filters.worker_id = undefined
  filters.dispatcher_id = undefined
  currentPage.value = 1
  refresh()
}

async function startWorkOrder(row) {
  submitting.value = true
  try {
    await workerWorkOrdersApi.startWorkOrder(row.id)
    ElMessage.success('工单已开始执行')
    await refresh()
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
    await refresh()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  syncFiltersFromRoute()
  refresh()
})

watch(
  () => route.query,
  () => {
    syncFiltersFromRoute()
    refresh()
  },
)
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

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-item {
  width: 280px;
}

.toolbar-item.mini {
  width: 140px;
}

.w-full {
  width: 100%;
}

.pagination-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.override-box,
.extra-box {
  margin-top: 12px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: #f8fbfd;
  color: var(--ink-normal);
}

.override-title {
  margin: 0 0 6px;
  font-weight: 600;
  color: var(--ink-strong);
}

:deep(.el-tag.tag-pending) {
  color: #9a5b18;
  background-color: #fbe9cf;
  border-color: #efca95;
}

:deep(.el-tag.tag-progress) {
  color: #1f5c9a;
  background-color: #e4effc;
  border-color: #b9d4f7;
}

:deep(.el-tag.tag-completed) {
  color: #24633f;
  background-color: #ddf4e6;
  border-color: #b6dfc8;
}

:deep(.el-tag.tag-terminated) {
  color: #97463a;
  background-color: #f8e3de;
  border-color: #efbfb4;
}
</style>
