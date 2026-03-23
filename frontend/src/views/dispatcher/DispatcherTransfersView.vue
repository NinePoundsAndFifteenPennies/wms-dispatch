<template>
  <div class="dispatcher-transfer-workbench">
    <section class="hero-panel">
      <div>
        <p class="kicker">Transfer Workbench</p>
        <h2>跨仓调拨流转</h2>
        <p>覆盖申请、审批、执行扣减和待入库确认的全流程工作台。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">发起调拨申请</el-button>
    </section>

    <section class="metric-grid">
      <article class="metric-card">
        <span>待审批</span>
        <strong>{{ metrics.pending }}</strong>
      </article>
      <article class="metric-card">
        <span>待执行</span>
        <strong>{{ metrics.approved }}</strong>
      </article>
      <article class="metric-card">
        <span>已完成</span>
        <strong>{{ metrics.completed }}</strong>
      </article>
      <article class="metric-card">
        <span>待确认入库</span>
        <strong>{{ pendingInboundRecords.length }}</strong>
      </article>
    </section>

    <section class="toolbar">
      <el-radio-group v-model="filters.scope" @change="handleScopeChange">
        <el-radio-button v-for="option in scopeOptions" :key="option.value" :label="option.value">
          {{ option.label }}
        </el-radio-button>
      </el-radio-group>
      <el-select
        v-model="filters.status"
        placeholder="状态"
        clearable
        class="status-select"
        :disabled="statusSelectDisabled"
        @change="fetchTransfers"
      >
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input
        v-model="filters.search"
        clearable
        placeholder="搜索调拨单号 / SKU / 产品 / 仓库"
        class="search-input"
        @keyup.enter="fetchTransfers"
        @clear="fetchTransfers"
      />
      <el-button @click="fetchTransfers">刷新</el-button>
    </section>

    <section class="workbench-main" v-loading="loadingTransfers">
      <el-card shadow="never" class="list-panel">
        <template #header>
          <div class="panel-header">
            <span>调拨单列表</span>
            <small>共 {{ total }} 条</small>
          </div>
        </template>

        <div v-if="transferItems.length === 0" class="empty-copy">暂无匹配调拨单</div>

        <article
          v-for="item in transferItems"
          :key="item.id"
          class="transfer-row"
          :class="{ active: selectedTransferId === item.id }"
          @click="selectTransfer(item.id)"
        >
          <div class="row-top">
            <strong>{{ item.code }}</strong>
            <el-tag :type="tagType(item.status)" effect="light">{{ statusText(item.status) }}</el-tag>
          </div>
          <p>{{ item.product_name }} / {{ item.product_sku }}</p>
          <div class="row-meta">
            <span>{{ item.from_warehouse_name }} -> {{ item.to_warehouse_name }}</span>
            <span>x {{ item.qty }}</span>
          </div>
        </article>
      </el-card>

      <el-card shadow="never" class="detail-panel" v-loading="loadingDetail">
        <template #header>
          <div class="panel-header">
            <span>调拨详情</span>
            <small>{{ selectedTransfer?.code || '-' }}</small>
          </div>
        </template>

        <div v-if="!selectedTransfer" class="empty-copy">请选择左侧调拨单查看详情</div>

        <template v-else>
          <dl class="detail-grid">
            <div><dt>产品</dt><dd>{{ selectedTransfer.product_name }} / {{ selectedTransfer.product_sku }}</dd></div>
            <div><dt>数量</dt><dd>{{ selectedTransfer.qty }}</dd></div>
            <div><dt>供给仓</dt><dd>{{ selectedTransfer.from_warehouse_name }}</dd></div>
            <div><dt>申请仓</dt><dd>{{ selectedTransfer.to_warehouse_name }}</dd></div>
            <div><dt>申请人</dt><dd>{{ selectedTransfer.requested_by_name || '-' }}</dd></div>
            <div><dt>指定审批人</dt><dd>{{ selectedTransfer.review_dispatcher_name || '-' }}</dd></div>
            <div><dt>审批人</dt><dd>{{ selectedTransfer.approved_by_name || '-' }}</dd></div>
          </dl>

          <p v-if="selectedTransfer.description" class="reason-text">{{ selectedTransfer.description }}</p>
          <p v-if="selectedTransfer.rejection_reason" class="reject-text">驳回原因：{{ selectedTransfer.rejection_reason }}</p>

          <div class="action-row">
            <el-button
              v-if="selectedTransfer.status === 'pending' && canReviewSelected"
              type="success"
              :loading="actionLoading.approve"
              @click="handleApprove"
            >审批通过</el-button>
            <el-button
              v-if="selectedTransfer.status === 'pending' && canReviewSelected"
              type="danger"
              plain
              :loading="actionLoading.reject"
              @click="handleReject"
            >驳回</el-button>
            <el-button
              v-if="selectedTransfer.status === 'approved' && !selectedTransfer.executed_at && canExecuteSelected"
              type="primary"
              :loading="actionLoading.execute"
              @click="handleExecute"
            >执行调拨扣减</el-button>
          </div>

          <el-divider />

          <div class="timeline-block">
            <div><span>创建</span><strong>{{ formatDateTime(selectedTransfer.created_at) }}</strong></div>
            <div><span>审批</span><strong>{{ formatDateTime(selectedTransfer.approved_at) }}</strong></div>
            <div><span>执行</span><strong>{{ formatDateTime(selectedTransfer.executed_at) }}</strong></div>
            <div><span>完成</span><strong>{{ formatDateTime(selectedTransfer.completed_at) }}</strong></div>
          </div>
        </template>
      </el-card>
    </section>

    <el-card shadow="never" class="inbound-panel" v-loading="loadingInbound">
      <template #header>
        <div class="panel-header">
          <span>待入库确认（仅我发起）</span>
          <small>{{ pendingInboundRecords.length }} 条</small>
        </div>
      </template>

      <el-table :data="pendingInboundRecords" size="small">
        <el-table-column prop="transfer_order_id" label="调拨单" min-width="120" />
        <el-table-column label="产品" min-width="180">
          <template #default="{ row }">{{ row.product_name }} / {{ row.product_sku }}</template>
        </el-table-column>
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column prop="warehouse_name" label="仓库" min-width="140" />
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :loading="actionLoading.confirmId === row.id" @click="handleConfirmInbound(row)">
              确认入库
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="发起调拨申请" width="560px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="88px">
        <el-form-item label="供给仓" prop="from_warehouse_id">
          <el-select v-model="createForm.from_warehouse_id" placeholder="选择供给仓" @change="handleSourceWarehouseChange">
            <el-option v-for="item in sourceWarehouses" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批调度员" prop="review_dispatcher_id">
          <el-select
            v-model="createForm.review_dispatcher_id"
            placeholder="选择供给仓处理人"
            filterable
            :disabled="!createForm.from_warehouse_id"
          >
            <el-option
              v-for="item in sourceDispatchers"
              :key="item.id"
              :label="`${item.username} (${item.email})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="调拨商品" prop="product_id">
          <el-select v-model="createForm.product_id" placeholder="选择商品" filterable :disabled="!createForm.from_warehouse_id">
            <el-option
              v-for="item in sourceProducts"
              :key="item.product_id"
              :label="`${item.product_name} / ${item.sku} (可用${item.qty_available})`"
              :value="item.product_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" prop="qty">
          <el-input-number v-model="createForm.qty" :min="1" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading.create" @click="handleCreateTransfer">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dispatcherTransfersApi } from '../../api/dispatcher/transfers'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()

const loadingTransfers = ref(false)
const loadingDetail = ref(false)
const loadingInbound = ref(false)
const transferItems = ref([])
const total = ref(0)
const selectedTransferId = ref(null)
const selectedTransfer = ref(null)
const pendingInboundRecords = ref([])
const sourceWarehouses = ref([])
const sourceProducts = ref([])
const sourceDispatchers = ref([])
const createDialogVisible = ref(false)
const createFormRef = ref()

const scopeOptions = [
  { label: '全部相关', value: 'all' },
  { label: '我发起', value: 'requested' },
  { label: '我的审批', value: 'approval' },
  { label: '待我入库', value: 'inbound' },
]

const commonStatusOptions = [
  { label: '待审批', value: 'pending' },
  { label: '已审批', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
  { label: '已完成', value: 'completed' },
]

const filters = reactive({
  scope: 'all',
  status: '',
  search: '',
})

const createForm = reactive({
  from_warehouse_id: null,
  review_dispatcher_id: null,
  product_id: null,
  qty: 1,
  description: '',
})

const createRules = {
  from_warehouse_id: [{ required: true, message: '请选择供给仓', trigger: 'change' }],
  review_dispatcher_id: [{ required: true, message: '请选择审批调度员', trigger: 'change' }],
  product_id: [{ required: true, message: '请选择调拨商品', trigger: 'change' }],
  qty: [{ required: true, message: '请输入调拨数量', trigger: 'change' }],
}

const actionLoading = reactive({
  create: false,
  approve: false,
  reject: false,
  execute: false,
  confirmId: null,
})

const metrics = computed(() => {
  return transferItems.value.reduce(
    (acc, item) => {
      if (item.status === 'pending') acc.pending += 1
      if (item.status === 'approved' && !item.executed_at) acc.approved += 1
      if (item.status === 'completed') acc.completed += 1
      return acc
    },
    { pending: 0, approved: 0, completed: 0 },
  )
})

const statusOptions = computed(() => {
  if (filters.scope === 'inbound') return []
  if (filters.scope === 'approval') {
    return [
      { label: '待我审批', value: 'pending' },
      { label: '我已审批', value: 'approved' },
      { label: '我已驳回', value: 'rejected' },
      { label: '已完成', value: 'completed' },
    ]
  }
  return commonStatusOptions
})

const statusSelectDisabled = computed(() => filters.scope === 'inbound')

const currentWarehouseId = computed(() => Number(authStore.currentUser?.warehouse_id || 0))
const currentUserId = computed(() => Number(authStore.currentUser?.id || 0))

const canReviewSelected = computed(() => {
  if (!selectedTransfer.value) return false
  if (selectedTransfer.value.review_dispatcher_id) {
    return Number(selectedTransfer.value.review_dispatcher_id) === currentUserId.value
  }
  return Number(selectedTransfer.value.from_warehouse_id || 0) === currentWarehouseId.value
})

const canExecuteSelected = computed(() => {
  if (!selectedTransfer.value) return false
  return Number(selectedTransfer.value.approved_by || 0) === currentUserId.value
})

function tagType(status) {
  if (status === 'pending') return 'warning'
  if (status === 'approved') return 'primary'
  if (status === 'completed') return 'success'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function statusText(status) {
  return {
    pending: '待审批',
    approved: '已审批',
    rejected: '已驳回',
    cancelled: '已取消',
    completed: '已完成',
  }[status] || status
}

function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function handleScopeChange() {
  if (filters.scope === 'inbound') {
    filters.status = ''
  }
  fetchTransfers()
}

async function fetchTransfers() {
  loadingTransfers.value = true
  try {
    const res = await dispatcherTransfersApi.listTransfers({
      scope: filters.scope,
      status: filters.status || undefined,
      search: filters.search || undefined,
    })
    transferItems.value = res.data?.items || []
    total.value = res.data?.total || 0

    if (!transferItems.value.length) {
      selectedTransferId.value = null
      selectedTransfer.value = null
      return
    }

    const stillExists = transferItems.value.some((item) => item.id === selectedTransferId.value)
    const nextId = stillExists ? selectedTransferId.value : transferItems.value[0].id
    await selectTransfer(nextId)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取调拨列表失败')
  } finally {
    loadingTransfers.value = false
  }
}

async function selectTransfer(transferId) {
  if (!transferId) return
  selectedTransferId.value = transferId
  loadingDetail.value = true
  try {
    const res = await dispatcherTransfersApi.getTransferDetail(transferId)
    selectedTransfer.value = res.data || null
  } catch (error) {
    selectedTransfer.value = null
    ElMessage.error(error.response?.data?.message || '获取调拨详情失败')
  } finally {
    loadingDetail.value = false
  }
}

async function fetchPendingInbound() {
  loadingInbound.value = true
  try {
    const res = await dispatcherTransfersApi.listPendingInboundRecords()
    pendingInboundRecords.value = res.data?.items || []
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取待入库记录失败')
  } finally {
    loadingInbound.value = false
  }
}

async function openCreateDialog() {
  createDialogVisible.value = true
  await loadSourceWarehouses()
}

async function loadSourceWarehouses() {
  try {
    const res = await dispatcherTransfersApi.listSourceWarehouses()
    sourceWarehouses.value = res.data || []
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取供给仓列表失败')
  }
}

async function handleSourceWarehouseChange() {
  createForm.review_dispatcher_id = null
  createForm.product_id = null
  sourceProducts.value = []
  sourceDispatchers.value = []
  if (!createForm.from_warehouse_id) return

  try {
    const [inventoryRes, dispatcherRes] = await Promise.all([
      dispatcherTransfersApi.listSourceInventory({
        warehouse_id: createForm.from_warehouse_id,
      }),
      dispatcherTransfersApi.listSourceDispatchers({
        warehouse_id: createForm.from_warehouse_id,
      }),
    ])
    sourceProducts.value = inventoryRes.data || []
    sourceDispatchers.value = dispatcherRes.data || []
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取供给仓数据失败')
  }
}

async function handleCreateTransfer() {
  if (!createFormRef.value) return
  await createFormRef.value.validate()

  actionLoading.create = true
  try {
    await dispatcherTransfersApi.createTransfer({
      from_warehouse_id: createForm.from_warehouse_id,
      review_dispatcher_id: createForm.review_dispatcher_id,
      product_id: createForm.product_id,
      qty: Number(createForm.qty),
      description: createForm.description?.trim() || undefined,
    })
    ElMessage.success('调拨申请已提交')
    createDialogVisible.value = false
    Object.assign(createForm, {
      from_warehouse_id: null,
      review_dispatcher_id: null,
      product_id: null,
      qty: 1,
      description: '',
    })
    sourceProducts.value = []
    sourceDispatchers.value = []
    await Promise.all([fetchTransfers(), fetchPendingInbound()])
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '调拨申请提交失败')
  } finally {
    actionLoading.create = false
  }
}

async function handleApprove() {
  if (!selectedTransfer.value) return
  actionLoading.approve = true
  try {
    await dispatcherTransfersApi.approveTransfer(selectedTransfer.value.id)
    ElMessage.success('调拨单已审批通过')
    await Promise.all([fetchTransfers(), fetchPendingInbound()])
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '审批失败')
  } finally {
    actionLoading.approve = false
  }
}

async function handleReject() {
  if (!selectedTransfer.value) return
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回调拨单', {
      inputPlaceholder: '至少填写一个明确原因',
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputValidator: (val) => (val && val.trim() ? true : '驳回原因不能为空'),
    })

    actionLoading.reject = true
    await dispatcherTransfersApi.rejectTransfer(selectedTransfer.value.id, { reason: value.trim() })
    ElMessage.success('调拨单已驳回')
    await Promise.all([fetchTransfers(), fetchPendingInbound()])
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error(error.response?.data?.message || '驳回失败')
  } finally {
    actionLoading.reject = false
  }
}

async function handleExecute() {
  if (!selectedTransfer.value) return
  try {
    await ElMessageBox.confirm('执行后将扣减供给仓现存量并生成申请仓待入库记录，是否继续？', '执行调拨', {
      confirmButtonText: '立即执行',
      cancelButtonText: '取消',
      type: 'warning',
    })

    actionLoading.execute = true
    await dispatcherTransfersApi.executeTransfer(selectedTransfer.value.id)
    ElMessage.success('调拨执行成功，已生成待入库记录')
    await Promise.all([fetchTransfers(), fetchPendingInbound()])
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error(error.response?.data?.message || '执行失败')
  } finally {
    actionLoading.execute = false
  }
}

async function handleConfirmInbound(record) {
  actionLoading.confirmId = record.id
  try {
    await dispatcherTransfersApi.confirmInboundRecord(record.id)
    ElMessage.success('入库确认成功')
    await Promise.all([fetchTransfers(), fetchPendingInbound()])
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '入库确认失败')
  } finally {
    actionLoading.confirmId = null
  }
}

onMounted(async () => {
  await Promise.all([fetchTransfers(), fetchPendingInbound()])
})
</script>

<style scoped>
.dispatcher-transfer-workbench {
  display: grid;
  gap: 14px;
}

.hero-panel {
  border: 1px solid #d6d0c4;
  border-radius: 16px;
  padding: 18px 20px;
  background: linear-gradient(130deg, #fffaf2 0%, #f5efe5 45%, #efe9dc 100%);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.kicker {
  margin: 0;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8a7763;
}

.hero-panel h2 {
  margin: 8px 0 0;
  font-size: 24px;
}

.hero-panel p {
  margin: 8px 0 0;
  color: #655c50;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  border: 1px solid #d8d2c7;
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff;
}

.metric-card span {
  display: block;
  font-size: 12px;
  color: #8a7763;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  font-size: 22px;
  color: #2f2b26;
}

.toolbar {
  border: 1px solid #d8d2c7;
  border-radius: 14px;
  background: #fff;
  padding: 10px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.status-select {
  width: 130px;
}

.search-input {
  max-width: 320px;
}

.workbench-main {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
}

.list-panel,
.detail-panel,
.inbound-panel {
  border: 1px solid #d8d2c7;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header small {
  color: #8a7763;
}

.transfer-row {
  border: 1px solid #e7e1d6;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.transfer-row + .transfer-row {
  margin-top: 8px;
}

.transfer-row.active {
  border-color: #8a6a45;
  box-shadow: 0 0 0 1px #8a6a45 inset;
}

.row-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.transfer-row p {
  margin: 8px 0 0;
}

.row-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  color: #796d5d;
  font-size: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.detail-grid dt {
  color: #8a7763;
  font-size: 12px;
}

.detail-grid dd {
  margin: 4px 0 0;
  color: #2f2b26;
}

.reason-text,
.reject-text {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
}

.reason-text {
  background: #f7f2e9;
}

.reject-text {
  background: #fdeeee;
  color: #9f2b2b;
}

.action-row {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.timeline-block {
  display: grid;
  gap: 8px;
}

.timeline-block div {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed #e8dfd3;
  padding-bottom: 6px;
  font-size: 13px;
}

.timeline-block span {
  color: #8a7763;
}

.empty-copy {
  color: #8a7763;
  padding: 14px 0;
}

@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workbench-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero-panel {
    flex-direction: column;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .search-input {
    max-width: none;
    width: 100%;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
