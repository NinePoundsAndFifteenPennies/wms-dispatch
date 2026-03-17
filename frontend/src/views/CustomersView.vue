<template>
  <div class="customers-page">
    <section class="toolbar">
      <div>
        <h3>客户管理</h3>
        <p>维护客户基础信息，支持搜索与批量删除。</p>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="searchQuery"
          placeholder="按客户名称/联系方式搜索"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
        <el-button type="danger" plain :disabled="selectedIds.length === 0" @click="handleBatchDelete">
          批量删除
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增客户
        </el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-table :data="customers" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="52" />
        <el-table-column prop="name" label="客户名称" min-width="180" />
        <el-table-column prop="contact" label="联系方式" min-width="180" />
        <el-table-column prop="address" label="地址" min-width="240" show-overflow-tooltip />
        <el-table-column prop="description" label="备注" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="val => onStatusChange(row, val)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button type="success" link @click="openDetailDialog(row)">详情</el-button>
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增客户' : '编辑客户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="客户名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="form.contact" />
        </el-form-item>
        <el-form-item label="地址" prop="address">
          <el-input v-model="form.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCustomer">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="客户详情" width="680px">
      <el-card shadow="never" class="detail-card">
        <el-form ref="detailFormRef" :model="detailForm" :rules="rules" label-width="90px">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="客户名称" prop="name">
                <el-input v-model="detailForm.name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="联系方式" prop="contact">
                <el-input v-model="detailForm.contact" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="地址" prop="address">
            <el-input v-model="detailForm.address" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="备注" prop="description">
            <el-input v-model="detailForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="detailForm.is_active" />
          </el-form-item>
        </el-form>
      </el-card>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :loading="detailSaving" @click="saveDetail">保存详情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { customersApi } from '../api/customers'

const customers = ref([])
const loading = ref(false)
const saving = ref(false)

const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchQuery = ref('')
const selectedIds = ref([])

const dialogVisible = ref(false)
const dialogMode = ref('create')
const editingId = ref(null)
const formRef = ref()
const detailVisible = ref(false)
const detailSaving = ref(false)
const detailEditingId = ref(null)
const detailFormRef = ref()
const form = reactive({
  name: '',
  contact: '',
  address: '',
  description: '',
})
const detailForm = reactive({
  name: '',
  contact: '',
  address: '',
  description: '',
  is_active: true,
})

const rules = {
  name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  contact: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
}

function onSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

async function fetchCustomers() {
  loading.value = true
  try {
    const res = await customersApi.getCustomers({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
    })
    customers.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchCustomers()
}

function handleSizeChange(size) {
  pageSize.value = size
  fetchCustomers()
}

function handleCurrentChange(page) {
  currentPage.value = page
  fetchCustomers()
}

function resetForm() {
  form.name = ''
  form.contact = ''
  form.address = ''
  form.description = ''
  editingId.value = null
}

function openCreateDialog() {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
  if (formRef.value) formRef.value.clearValidate()
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.name = row.name
  form.contact = row.contact
  form.address = row.address || ''
  form.description = row.description || ''
  dialogVisible.value = true
  if (formRef.value) formRef.value.clearValidate()
}

function openDetailDialog(row) {
  detailEditingId.value = row.id
  detailForm.name = row.name
  detailForm.contact = row.contact
  detailForm.address = row.address || ''
  detailForm.description = row.description || ''
  detailForm.is_active = row.is_active
  detailVisible.value = true
  if (detailFormRef.value) detailFormRef.value.clearValidate()
}

async function saveDetail() {
  const valid = await detailFormRef.value.validate().catch(() => false)
  if (!valid) return

  detailSaving.value = true
  try {
    await customersApi.updateCustomer(detailEditingId.value, {
      name: detailForm.name,
      contact: detailForm.contact,
      address: detailForm.address || null,
      description: detailForm.description || null,
    })
    await customersApi.updateCustomerStatus(detailEditingId.value, detailForm.is_active)
    ElMessage.success('详情保存成功')
    detailVisible.value = false
    fetchCustomers()
  } finally {
    detailSaving.value = false
  }
}

async function saveCustomer() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      name: form.name,
      contact: form.contact,
      address: form.address || null,
      description: form.description || null,
    }
    if (dialogMode.value === 'create') {
      await customersApi.createCustomer(payload)
      ElMessage.success('新增成功')
    } else {
      await customersApi.updateCustomer(editingId.value, payload)
      ElMessage.success('更新成功')
    }

    dialogVisible.value = false
    fetchCustomers()
  } finally {
    saving.value = false
  }
}

async function onStatusChange(row, targetStatus) {
  try {
    await customersApi.updateCustomerStatus(row.id, targetStatus)
    ElMessage.success('状态更新成功')
  } catch {
    row.is_active = !targetStatus
  }
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 位客户吗？`, '提示', {
    type: 'warning',
  })
  await customersApi.batchDeleteCustomers(selectedIds.value)
  ElMessage.success('批量删除成功')
  selectedIds.value = []
  fetchCustomers()
}

onMounted(() => {
  fetchCustomers()
})
</script>

<style scoped>
.customers-page {
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

.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

h3 {
  margin: 0;
  font-size: 22px;
}

p {
  margin: 6px 0 0;
  color: #475569;
}

.table-card {
  border-radius: 12px;
}

.detail-card {
  border-radius: 12px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 980px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .toolbar-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
