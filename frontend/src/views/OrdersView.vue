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
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 320px"
        />
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
        <el-table-column prop="total_amount" label="总金额(分)" width="120" />
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="96" fixed="right">
          <template #default="{ row }">
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
            <div v-for="(item, index) in createForm.items" :key="index" class="item-row">
              <el-select
                v-model="item.product_id"
                filterable
                remote
                reserve-keyword
                :remote-method="fetchProductOptions"
                :loading="productLoading"
                placeholder="搜索产品（名称/SKU/类别）"
                style="width: 42%"
              >
                <el-option
                  v-for="product in productOptions"
                  :key="product.id"
                  :label="`${product.name}（${product.sku}）`"
                  :value="product.id"
                />
              </el-select>
              <el-input-number v-model="item.qty" :min="1" :precision="0" style="width: 18%" />
              <el-input-number v-model="item.unit_price" :min="0" :precision="0" style="width: 22%" />
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
        <el-descriptions-item label="更新时间">{{ formatDateTime(detail.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="总金额/总件数">{{ detail.total_amount }} / {{ detail.total_items }}</el-descriptions-item>
      </el-descriptions>

      <el-card shadow="never" style="margin-top: 12px" v-if="detail">
        <template #header>订单明细</template>
        <el-table :data="detail.items" stripe>
          <el-table-column prop="product_sku" label="SKU" width="130" />
          <el-table-column prop="product_name" label="产品名称" min-width="200" />
          <el-table-column prop="product_category" label="类别" min-width="120" />
          <el-table-column prop="qty" label="数量" width="90" />
          <el-table-column prop="unit_price" label="单价(分)" width="110" />
          <el-table-column prop="subtotal" label="小计(分)" width="110" />
        </el-table>
      </el-card>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Plus } from '@element-plus/icons-vue'
import { customersApi } from '../api/customers'
import { ordersApi } from '../api/orders'
import { productsApi } from '../api/products'

const orders = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])

const detailVisible = ref(false)
const detail = ref(null)

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

function formatDateTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}

function buildQueryParams() {
  const [startDate, endDate] = dateRange.value || []
  return {
    page: currentPage.value,
    page_size: pageSize.value,
    search: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }
}

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
    productOptions.value = (res.data.items || []).filter((item) => item.is_active)
  } finally {
    productLoading.value = false
  }
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

async function handleExport(format) {
  const [startDate, endDate] = dateRange.value || []
  const res = await ordersApi.exportOrders({
    export_format: format,
    search: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  })
  downloadTextFile(res.data.filename, res.data.content, res.data.mime_type)
  ElMessage.success('导出成功')
}

onMounted(() => {
  fetchOrders()
})
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

.item-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.option-disabled {
  color: #a0a0a0;
}

@media (max-width: 860px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
