<template>
  <div class="work-order-page" v-loading="loading">
    <header>
      <h3>我的工单</h3>
      <p>按状态推进你被分配的工单。</p>
    </header>

    <div class="toolbar">
      <el-select v-model="statusFilter" placeholder="按状态筛选" clearable class="toolbar-item">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已终止" value="terminated" />
      </el-select>
      <el-input
        v-model="keyword"
        class="toolbar-item"
        clearable
        placeholder="搜索工单ID/订单号/备注"
      />
    </div>

    <section class="worker-card-grid">
      <el-empty v-if="workOrders.length === 0" description="暂无匹配工单" :image-size="96" />

      <article
        v-for="row in workOrders"
        :key="row.id"
        class="worker-order-card"
        @click="openDetail(row.id)"
      >
        <header class="card-head">
          <strong>#{{ row.id }} · {{ row.order_no }}</strong>
          <el-tag :class="statusTagClass(row.status)" effect="light" round>{{ workOrderStatusText(row.status) }}</el-tag>
        </header>

        <p class="card-line">阶段：{{ stageText(row.stage_type) }} ｜ 优先级：{{ priorityText(row.priority) }}</p>
        <p class="card-line">调度员：{{ row.dispatcher_name || '-' }}</p>
        <p class="card-line">截止：{{ formatDate(row.deadline) }}</p>
        <p class="card-line">备注：{{ row.description || '-' }}</p>

        <footer class="card-actions">
          <el-button
            size="small"
            type="primary"
            plain
            :disabled="row.status !== 'pending' || submitting"
            @click.stop="startWorkOrder(row)"
          >
            接单开始
          </el-button>
          <el-button
            size="small"
            type="success"
            plain
            :disabled="row.status !== 'in_progress' || submitting"
            @click.stop="openCompleteDialog(row)"
          >
            完成工单
          </el-button>
        </footer>
      </article>
    </section>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
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
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { workerWorkOrdersApi } from '../../api/worker/workOrders'
import { formatCnDateTime } from '../../utils/cnTime'

const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const workOrders = ref([])
const statusFilter = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const completeDialogVisible = ref(false)
const selectedWorkOrderId = ref(null)
const completeForm = ref({ note_type: 'normal', content: '' })
let searchTimer = null
let lastRequestId = 0

async function fetchWorkOrders() {
  const requestId = ++lastRequestId
  loading.value = true
  try {
    const res = await workerWorkOrdersApi.getMyWorkOrders({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      search: keyword.value.trim() || undefined,
    })
    if (requestId !== lastRequestId) return

    workOrders.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (error) {
    if (requestId === lastRequestId) {
      ElMessage.error(error?.response?.data?.detail || '获取工单失败，请稍后重试')
    }
  } finally {
    if (requestId === lastRequestId) {
      loading.value = false
    }
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

function openDetail(workOrderId) {
  router.push({ name: 'worker-work-order-detail', params: { workOrderId } })
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

function handlePageChange(nextPage) {
  page.value = nextPage
  fetchWorkOrders()
}

function handlePageSizeChange(nextSize) {
  pageSize.value = nextSize
  page.value = 1
  fetchWorkOrders()
}

watch(statusFilter, () => {
  page.value = 1
  fetchWorkOrders()
})

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchWorkOrders()
  }, 300)
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

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

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-item {
  width: 260px;
}

.pagination-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.worker-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.worker-order-card {
  border: 1px solid #d8e1eb;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fcfb 100%);
  padding: 12px;
  display: grid;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(22, 32, 42, 0.05);
  border-left: 4px solid #1c9c89;
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
}

.worker-order-card:hover {
  box-shadow: 0 10px 22px rgba(17, 114, 100, 0.14);
  border-color: #b7d8d2;
  transform: translateY(-1px);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.card-line {
  margin: 0;
  color: #475569;
  font-size: 13px;
}

.card-actions {
  display: flex;
  gap: 8px;
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

@media (max-width: 1200px) {
  .worker-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .worker-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
