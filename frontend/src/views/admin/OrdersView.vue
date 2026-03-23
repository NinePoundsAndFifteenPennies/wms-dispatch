<template>
  <div class="orders-page">
    <section class="toolbar">
      <div>
        <h3>订单中枢</h3>
        <p>管理员订单列表、创建、详情与导出。</p>
      </div>
      <div class="actions">
        <el-dropdown @command="handleExport">
          <el-button>
            <el-icon><Download /></el-icon>
            导出
          </el-button>
          <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                <el-dropdown-item command="markdown">导出 Markdown</el-dropdown-item>
                <el-dropdown-item command="pdf">导出 PDF</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新建订单
        </el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <section class="filters">
        <el-input
          v-model="searchQuery"
          placeholder="搜索订单号/客户"
          clearable
          @keyup.enter="handleSearch"
          style="max-width: 260px"
        />
        <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 180px">
          <el-option label="待接单" value="pending_acceptance" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>

        <!-- 日期范围：拆成两个独立 DatePicker，互不联动，可单独设置 -->
        <div class="date-range-wrap">
          <el-date-picker
            v-model="startDate"
            type="date"
            placeholder="开始日期"
            value-format="YYYY-MM-DD"
            :disabled-date="disableStartDate"
            clearable
            style="width: 160px"
            @change="handleSearch"
          />
          <span class="date-sep">至</span>
          <el-date-picker
            v-model="endDate"
            type="date"
            placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :disabled-date="disableEndDate"
            clearable
            style="width: 160px"
            @change="handleSearch"
          />
          <el-button
            v-if="startDate || endDate"
            link
            type="info"
            @click="clearDateRange"
            style="margin-left: 2px"
          >清除</el-button>
        </div>

        <el-button type="primary" @click="handleSearch">查询</el-button>
      </section>

      <el-table :data="orders" stripe>
        <el-table-column prop="order_no" label="订单号" min-width="150" />
        <el-table-column prop="customer_name" label="客户" min-width="140" />
        <el-table-column label="仓库" min-width="140">
          <template #default="{ row }">{{ row.warehouse_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">{{ priorityText(row.priority) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">{{ statusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="责任调度员" min-width="120">
          <template #default="{ row }">{{ row.dispatcher_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="total_items" label="总件数" width="100" />
        <el-table-column prop="total_amount" label="总金额(元)" width="120" />
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending_acceptance'"
              link
              type="primary"
              @click="openEditDialog(row.id)"
            >编辑</el-button>
            <el-button
              v-if="row.status === 'pending_acceptance'"
              link
              type="danger"
              @click="openCancelDialog(row.id)"
            >取消</el-button>
            <el-button
              v-if="row.status === 'cancelled'"
              link
              type="success"
              @click="reopenOrder(row.id)"
            >重开</el-button>
            <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新建订单" width="860px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="客户" prop="customer_id">
              <el-select
                v-model="createForm.customer_id"
                filterable
                remote
                reserve-keyword
                :remote-method="fetchCustomerOptions"
                :loading="customerLoading"
                placeholder="搜索客户名称/联系方式"
                style="width: 100%"
              >
                <el-option
                  v-for="customer in customerOptions"
                  :key="customer.id"
                  :label="`${customer.name}（${customer.contact}）`"
                  :value="customer.id"
                  :disabled="!customer.is_active"
                  :class="{ 'option-disabled': !customer.is_active }"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="createForm.priority" style="width: 100%">
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="订单明细" prop="items">
          <div class="item-editor">
            <div class="item-header">
              <span class="col-product">产品</span>
              <span class="col-qty">数量</span>
              <span class="col-price">单价(元)</span>
            </div>
            <div v-for="(item, index) in createForm.items" :key="index" class="item-row">
              <el-select
                v-model="item.product_id"
                filterable
                remote
                reserve-keyword
                :remote-method="fetchProductOptions"
                :loading="productLoading"
                placeholder="搜索产品（名称/SKU/类别）"
                class="col-product"
              >
                <el-option
                  v-for="product in getProductOptionsForRow(index)"
                  :key="product.id"
                  :label="`${product.name}（${product.sku}）`"
                  :value="product.id"
                />
              </el-select>
              <el-input-number v-model="item.qty" :min="1" :precision="0" controls-position="right" class="col-qty" />
              <el-input-number v-model="item.unit_price" :min="0" :precision="0" controls-position="right" class="col-price" />
              <el-button type="danger" plain @click="removeItem(index)" :disabled="createForm.items.length <= 1">
                删除
              </el-button>
            </div>
            <el-button type="primary" plain @click="addItem">新增明细</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="订单详情" width="980px">
      <el-descriptions v-if="detail" :column="3" border>
        <el-descriptions-item label="订单ID">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="客户联系方式">{{ detail.customer_contact }}</el-descriptions-item>
        <el-descriptions-item label="客户地址">{{ detail.customer_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="仓库">{{ detail.warehouse_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任调度员">{{ detail.dispatcher_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
        <el-descriptions-item label="接单时间">{{ formatDateTime(detail.accepted_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDateTime(detail.completed_at) }}</el-descriptions-item>
        <el-descriptions-item label="取消时间">{{ formatDateTime(detail.cancelled_at) }}</el-descriptions-item>
        <el-descriptions-item label="取消人">{{ detail.cancelled_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="取消原因" :span="2">{{ detail.cancellation_reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="总金额/总件数">{{ detail.total_amount }} / {{ detail.total_items }}</el-descriptions-item>
      </el-descriptions>

      <el-card shadow="never" style="margin-top: 12px" v-if="detail">
        <template #header>
          <div class="detail-header">
            <span>订单明细</span>
            <el-button type="primary" link @click="handleDetailPdfExport">导出详情 PDF</el-button>
          </div>
        </template>
        <el-table :data="detail.items" stripe>
          <el-table-column prop="product_sku" label="SKU" width="130" />
          <el-table-column prop="product_name" label="产品名称" min-width="200" />
          <el-table-column prop="product_category" label="类别" min-width="120" />
          <el-table-column prop="qty" label="数量" width="90" />
          <el-table-column prop="unit_price" label="单价(元)" width="110" />
          <el-table-column prop="subtotal" label="小计(元)" width="110" />
        </el-table>
      </el-card>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑待接单订单" width="860px">
      <el-form ref="editFormRef" :model="editForm" :rules="createRules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="editForm.priority" style="width: 100%">
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="订单号">
              <el-input v-model="editForm.order_no" disabled />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="订单明细" prop="items">
          <div class="item-editor">
            <div class="item-header">
              <span class="col-product">产品</span>
              <span class="col-qty">数量</span>
              <span class="col-price">单价(元)</span>
            </div>
            <div v-for="(item, index) in editForm.items" :key="index" class="item-row">
              <el-select
                v-model="item.product_id"
                filterable
                remote
                reserve-keyword
                :remote-method="fetchProductOptions"
                :loading="productLoading"
                placeholder="搜索产品（名称/SKU/类别）"
                class="col-product"
              >
                <el-option
                  v-for="product in getEditProductOptionsForRow(index)"
                  :key="product.id"
                  :label="`${product.name}（${product.sku}）`"
                  :value="product.id"
                />
              </el-select>
              <el-input-number v-model="item.qty" :min="1" :precision="0" controls-position="right" class="col-qty" />
              <el-input-number v-model="item.unit_price" :min="0" :precision="0" controls-position="right" class="col-price" />
              <el-button type="danger" plain @click="removeEditItem(index)" :disabled="editForm.items.length <= 1">
                删除
              </el-button>
            </div>
            <el-button type="primary" plain @click="addEditItem">新增明细</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="submitEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消订单" width="520px">
      <el-form ref="cancelFormRef" :model="cancelForm" :rules="cancelRules" label-width="100px">
        <el-form-item label="取消原因" prop="cancellation_reason">
          <el-input
            v-model="cancelForm.cancellation_reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="请输入取消原因（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">返回</el-button>
        <el-button type="danger" :loading="cancelling" @click="submitCancel">确认取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus } from '@element-plus/icons-vue'
import { customersApi } from '../../api/admin/customers'
import { ordersApi } from '../../api/admin/orders'
import { productsApi } from '../../api/admin/products'

const route = useRoute()

const orders = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')

// 拆分为两个独立日期，替代原来的 dateRange 数组
const startDate = ref('')
const endDate = ref('')

const detailVisible = ref(false)
const detail = ref(null)

const editDialogVisible = ref(false)
const editFormRef = ref()
const updating = ref(false)
const editingOrderId = ref(null)
const editForm = reactive({
  order_no: '',
  priority: 'medium',
  description: '',
  items: [{ product_id: null, qty: 1, unit_price: 0 }],
})

const cancelDialogVisible = ref(false)
const cancelFormRef = ref()
const cancelling = ref(false)
const cancellingOrderId = ref(null)
const cancelForm = reactive({
  cancellation_reason: '',
})

const createDialogVisible = ref(false)
const createFormRef = ref()
const creating = ref(false)
const customerLoading = ref(false)
const productLoading = ref(false)
const customerOptions = ref([])
const productOptions = ref([])

const createForm = reactive({
  customer_id: null,
  priority: 'medium',
  description: '',
  items: [{ product_id: null, qty: 1, unit_price: 0 }],
})

const createRules = {
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  items: [{ required: true, message: '请至少填写一条订单明细', trigger: 'change' }],
}

const cancelRules = {
  cancellation_reason: [{ required: true, message: '请输入取消原因', trigger: 'blur' }],
}

// ── 日期约束：开始日期不能晚于已选的结束日期 ──────────────────────────
function disableStartDate(time) {
  if (!endDate.value) return false
  return time.getTime() > new Date(endDate.value).getTime()
}

// 结束日期不能早于已选的开始日期
function disableEndDate(time) {
  if (!startDate.value) return false
  return time.getTime() < new Date(startDate.value).getTime()
}

function clearDateRange() {
  startDate.value = ''
  endDate.value = ''
  handleSearch()
}

// ── 工具函数 ───────────────────────────────────────────────────────────
function statusText(status) {
  return (
    {
      pending_acceptance: '待接单',
      in_progress: '进行中',
      completed: '已完成',
      cancelled: '已取消',
    }[status] || status
  )
}

function priorityText(priority) {
  return { high: '高', medium: '中', low: '低' }[priority] || priority
}

function formatDateTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}

function buildQueryParams() {
  return {
    page: currentPage.value,
    page_size: pageSize.value,
    search: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
    start_date: startDate.value || undefined,
    end_date: endDate.value || undefined,
  }
}

function syncFiltersFromRoute() {
  const { status, search, start_date: startDateQuery, end_date: endDateQuery } = route.query
  statusFilter.value = typeof status === 'string' ? status : ''
  searchQuery.value = typeof search === 'string' ? search : ''
  startDate.value = typeof startDateQuery === 'string' ? startDateQuery : ''
  endDate.value = typeof endDateQuery === 'string' ? endDateQuery : ''
  currentPage.value = 1
}

// ── 数据加载 ───────────────────────────────────────────────────────────
async function fetchOrders() {
  loading.value = true
  try {
    const res = await ordersApi.getOrders(buildQueryParams())
    orders.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchOrders()
}

function handleSizeChange(size) {
  pageSize.value = size
  fetchOrders()
}

function handleCurrentChange(page) {
  currentPage.value = page
  fetchOrders()
}

async function openDetail(orderId) {
  const res = await ordersApi.getOrderDetail(orderId)
  detail.value = res.data
  detailVisible.value = true
}

// ── 新建订单 ───────────────────────────────────────────────────────────
function resetCreateForm() {
  createForm.customer_id = null
  createForm.priority = 'medium'
  createForm.description = ''
  createForm.items = [{ product_id: null, qty: 1, unit_price: 0 }]
}

async function fetchCustomerOptions(keyword = '') {
  customerLoading.value = true
  try {
    const res = await customersApi.getCustomerOptions({ search: keyword || undefined })
    customerOptions.value = res.data || []
  } finally {
    customerLoading.value = false
  }
}

async function fetchProductOptions(keyword = '') {
  productLoading.value = true
  try {
    const res = await productsApi.getProducts({
      page: 1,
      page_size: 100,
      search: keyword || undefined,
    })
    productOptions.value = res.data.items || []
  } finally {
    productLoading.value = false
  }
}

function getProductOptionsForRow(index) {
  const selectedElsewhere = createForm.items
    .map((item, i) => (i !== index ? item.product_id : null))
    .filter(Boolean)
  return productOptions.value.filter((p) => !selectedElsewhere.includes(p.id))
}

function getEditProductOptionsForRow(index) {
  const selectedElsewhere = editForm.items
    .map((item, i) => (i !== index ? item.product_id : null))
    .filter(Boolean)
  return productOptions.value.filter((p) => !selectedElsewhere.includes(p.id))
}

function openCreateDialog() {
  resetCreateForm()
  createDialogVisible.value = true
  fetchCustomerOptions('')
  fetchProductOptions('')
}

function addItem() {
  createForm.items.push({ product_id: null, qty: 1, unit_price: 0 })
}

function removeItem(index) {
  if (createForm.items.length <= 1) return
  createForm.items.splice(index, 1)
}

function addEditItem() {
  editForm.items.push({ product_id: null, qty: 1, unit_price: 0 })
}

function removeEditItem(index) {
  if (editForm.items.length <= 1) return
  editForm.items.splice(index, 1)
}

async function submitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (createForm.items.some((item) => !item.product_id || item.qty <= 0 || item.unit_price < 0)) {
    ElMessage.error('请完整填写订单明细')
    return
  }

  creating.value = true
  try {
    await ordersApi.createOrder({
      customer_id: createForm.customer_id,
      priority: createForm.priority,
      description: createForm.description || null,
      items: createForm.items.map((item) => ({
        product_id: item.product_id,
        qty: item.qty,
        unit_price: item.unit_price,
      })),
    })
    ElMessage.success('订单创建成功')
    createDialogVisible.value = false
    fetchOrders()
  } finally {
    creating.value = false
  }
}

async function openEditDialog(orderId) {
  const res = await ordersApi.getOrderDetail(orderId)
  const data = res.data
  if (data.status !== 'pending_acceptance') {
    ElMessage.warning('仅待接单订单可编辑')
    return
  }

  editingOrderId.value = orderId
  editForm.order_no = data.order_no
  editForm.priority = data.priority
  editForm.description = data.description || ''
  editForm.items = (data.items || []).map((item) => ({
    product_id: item.product_id,
    qty: item.qty,
    unit_price: item.unit_price,
  }))
  if (!editForm.items.length) {
    editForm.items = [{ product_id: null, qty: 1, unit_price: 0 }]
  }
  await fetchProductOptions('')
  editDialogVisible.value = true
}

async function submitEdit() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid || !editingOrderId.value) return

  if (editForm.items.some((item) => !item.product_id || item.qty <= 0 || item.unit_price < 0)) {
    ElMessage.error('请完整填写订单明细')
    return
  }

  updating.value = true
  try {
    await ordersApi.updatePendingOrder(editingOrderId.value, {
      priority: editForm.priority,
      description: editForm.description || null,
      items: editForm.items.map((item) => ({
        product_id: item.product_id,
        qty: item.qty,
        unit_price: item.unit_price,
      })),
    })
    ElMessage.success('订单已更新')
    editDialogVisible.value = false
    await fetchOrders()
    if (detailVisible.value && detail.value?.id === editingOrderId.value) {
      await openDetail(editingOrderId.value)
    }
  } finally {
    updating.value = false
  }
}

function openCancelDialog(orderId) {
  cancellingOrderId.value = orderId
  cancelForm.cancellation_reason = ''
  cancelDialogVisible.value = true
}

async function submitCancel() {
  const valid = await cancelFormRef.value?.validate().catch(() => false)
  if (!valid || !cancellingOrderId.value) return

  cancelling.value = true
  try {
    await ordersApi.cancelPendingOrder(cancellingOrderId.value, {
      cancellation_reason: cancelForm.cancellation_reason,
    })
    ElMessage.success('订单已取消')
    cancelDialogVisible.value = false
    await fetchOrders()
  } finally {
    cancelling.value = false
  }
}

async function reopenOrder(orderId) {
  try {
    await ElMessageBox.confirm(
      '将基于该已取消订单重开一个新订单（新订单号，优先级/备注/明细默认一致）。是否继续？',
      '重开订单确认',
      {
        confirmButtonText: '继续重开',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  const res = await ordersApi.reopenCancelledOrder(orderId)
  const newOrderId = res.data.id
  ElMessage.success(`已重开新订单：${res.data.order_no}`)
  await fetchOrders()
  await openDetail(newOrderId)
}

// ── 导出 ───────────────────────────────────────────────────────────────
function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType || 'text/plain;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

function downloadBase64File(filename, base64Content, mimeType) {
  const byteCharacters = atob(base64Content)
  const byteArrays = []
  for (let offset = 0; offset < byteCharacters.length; offset += 1024) {
    const slice = byteCharacters.slice(offset, offset + 1024)
    const byteNumbers = new Array(slice.length)
    for (let byteIndex = 0; byteIndex < slice.length; byteIndex += 1) {
      byteNumbers[byteIndex] = slice.charCodeAt(byteIndex)
    }
    byteArrays.push(new Uint8Array(byteNumbers))
  }
  const blob = new Blob(byteArrays, { type: mimeType || 'application/octet-stream' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

async function handleExport(format) {
  const res = await ordersApi.exportOrders({
    export_format: format,
    search: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
    start_date: startDate.value || undefined,
    end_date: endDate.value || undefined,
  })
  if (format === 'pdf') {
    downloadBase64File(res.data.filename, res.data.content_base64, res.data.mime_type)
  } else {
    downloadTextFile(res.data.filename, res.data.content, res.data.mime_type)
  }
  ElMessage.success('导出成功')
}

async function handleDetailPdfExport() {
  if (!detail.value?.id) return
  const res = await ordersApi.exportOrderDetail(detail.value.id, { export_format: 'pdf' })
  downloadBase64File(res.data.filename, res.data.content_base64, res.data.mime_type)
  ElMessage.success('详情 PDF 导出成功')
}

onMounted(() => {
  syncFiltersFromRoute()
  fetchOrders()
})

watch(
  () => route.query,
  () => {
    syncFiltersFromRoute()
    fetchOrders()
  },
)
</script>

<style scoped>
.orders-page {
  display: grid;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

h3 {
  margin: 0;
  font-size: 22px;
}

p {
  margin: 6px 0 0;
  color: #475569;
}

.actions {
  display: flex;
  gap: 8px;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}

/* 两个独立日期选择器的容器 */
.date-range-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.date-sep {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

.table-card {
  border-radius: 12px;
}

.pagination-container {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.item-editor {
  width: 100%;
  display: grid;
  gap: 8px;
}

.item-header {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  padding: 0 2px;
}

.item-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.col-product {
  width: 42%;
  flex-shrink: 0;
}

.col-qty {
  width: 18%;
  flex-shrink: 0;
}

.col-price {
  width: 22%;
  flex-shrink: 0;
}

.option-disabled {
  color: #a0a0a0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 860px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .date-range-wrap {
    flex-wrap: wrap;
  }
}
</style>
