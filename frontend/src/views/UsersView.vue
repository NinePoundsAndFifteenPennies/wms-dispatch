<template>
  <div class="users-page">
    <section class="toolbar">
      <div>
        <h3>用户管理</h3>
        <p>维护账号信息、角色与启用状态。</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户..."
          clearable
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
        <el-button type="danger" plain :disabled="selectedIds.length === 0" @click="handleBatchDisable">
          批量禁用
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增用户
        </el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-table :data="users" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="52" :selectable="isSelectableUser" />
        <el-table-column label="头像" width="84">
          <template #default="{ row }">
            <el-avatar v-if="row.avatar" :src="row.avatar" :size="36" />
            <el-avatar v-else :size="36">
              <el-icon><UserFilled /></el-icon>
            </el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="120" />
        <el-table-column prop="warehouse_id" label="所属仓库" min-width="140">
          <template #default="{ row }">
            {{ getWarehouseName(row.warehouse_id) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-if="row.role !== 'admin'" v-model="row.is_active" @change="val => onStatusChange(row, val)" />
            <span v-else style="color: #909399; font-size: 13px;">始终启用</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button type="success" link @click="openDetailDialog(row)">详情</el-button>
            <el-button type="primary" link :disabled="!canEditUser(row)" @click="openEditDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" style="margin-top: 16px; display: flex; justify-content: flex-end;">
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

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增用户' : '编辑用户'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="dialogMode === 'create'">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="admin" value="admin" />
            <el-option label="dispatcher" value="dispatcher" />
            <el-option label="worker" value="worker" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库" prop="warehouse_id" v-if="form.role !== 'admin'">
          <el-select v-model="form.warehouse_id" placeholder="选择仓库" style="width: 100%" teleported="false">
            <el-option
              v-for="wh in warehouses"
              :key="wh.id"
              :label="wh.name"
              :value="wh.id"
            />
          </el-select>
        </el-form-item>
        <template v-if="form.role === 'worker'">
          <el-form-item label="分拣技能" prop="skill_picking">
            <el-input-number v-model="form.skill_picking" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="备货技能" prop="skill_staging">
            <el-input-number v-model="form.skill_staging" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="发货技能" prop="skill_shipping">
            <el-input-number v-model="form.skill_shipping" :min="0" :max="10" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="用户详情" width="720px">
      <div class="detail-grid">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>基础信息</span>
          </template>
          <el-form ref="detailFormRef" :model="detailForm" :rules="detailRules" label-width="98px">
            <el-form-item label="头像">
              <div class="avatar-inline">
                <el-avatar v-if="detailForm.avatar" :src="detailForm.avatar" :size="54" />
                <el-avatar v-else :size="54">
                  <el-icon><UserFilled /></el-icon>
                </el-avatar>
                <span class="placeholder-note">头像编辑功能待开放</span>
              </div>
            </el-form-item>
            <el-form-item label="用户名" prop="username">
              <el-input v-model="detailForm.username" :disabled="detailReadOnly" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="detailForm.email" :disabled="detailReadOnly" />
            </el-form-item>
            <el-form-item label="角色" prop="role">
              <el-select v-model="detailForm.role" style="width: 100%" :disabled="detailReadOnly">
                <el-option label="admin" value="admin" />
                <el-option label="dispatcher" value="dispatcher" />
                <el-option label="worker" value="worker" />
              </el-select>
            </el-form-item>
            <el-form-item label="仓库" prop="warehouse_id" v-if="detailForm.role !== 'admin'">
              <el-select
                v-model="detailForm.warehouse_id"
                placeholder="选择仓库"
                style="width: 100%"
                teleported="false"
                :disabled="detailReadOnly"
              >
                <el-option v-for="wh in warehouses" :key="wh.id" :label="wh.name" :value="wh.id" />
              </el-select>
            </el-form-item>
            <template v-if="detailForm.role === 'worker'">
              <el-form-item label="分拣技能" prop="skill_picking">
                <el-input-number v-model="detailForm.skill_picking" :min="0" :max="10" :disabled="detailReadOnly" />
              </el-form-item>
              <el-form-item label="备货技能" prop="skill_staging">
                <el-input-number v-model="detailForm.skill_staging" :min="0" :max="10" :disabled="detailReadOnly" />
              </el-form-item>
              <el-form-item label="发货技能" prop="skill_shipping">
                <el-input-number v-model="detailForm.skill_shipping" :min="0" :max="10" :disabled="detailReadOnly" />
              </el-form-item>
            </template>
          </el-form>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>个人资料（占位）</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="昵称">待实现</el-descriptions-item>
            <el-descriptions-item label="手机号">待实现</el-descriptions-item>
            <el-descriptions-item label="个人简介">待实现</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="detailReadOnly" :loading="detailSaving" @click="saveDetail">保存详情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, UserFilled } from '@element-plus/icons-vue'
import { adminApi } from '../api/admin'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const users = ref([])
const warehouses = ref([])
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
const detailVisible = ref(false)
const detailEditingId = ref(null)
const detailIsOtherAdmin = ref(false)
const detailSaving = ref(false)
const formRef = ref()
const detailFormRef = ref()
const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'worker',
  warehouse_id: null,
  skill_picking: 0,
  skill_staging: 0,
  skill_shipping: 0,
})
const detailForm = reactive({
  username: '',
  email: '',
  role: 'worker',
  warehouse_id: null,
  skill_picking: 0,
  skill_staging: 0,
  skill_shipping: 0,
  avatar: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  warehouse_id: [
    {
      validator: (_, value, callback) => {
        if (form.role === 'admin' || value) {
          callback()
          return
        }
        callback(new Error('非管理员必须填写仓库'))
      },
      trigger: 'change',
    },
  ],
}

const detailRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  warehouse_id: [
    {
      validator: (_, value, callback) => {
        if (detailForm.role === 'admin' || value) {
          callback()
          return
        }
        callback(new Error('非管理员必须填写仓库'))
      },
      trigger: 'change',
    },
  ],
}

function getWarehouseName(id) {
  const wh = warehouses.value.find(w => w.id === id)
  return wh ? wh.name : (id || '-')
}

function canEditUser(row) {
  return !(row.role === 'admin' && row.id !== authStore.currentUser?.id)
}

const detailReadOnly = computed(() => detailIsOtherAdmin.value)

function isSelectableUser(row) {
  return row.role !== 'admin'
}

function onSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined
    }
    const res = await adminApi.getUsers(params)
    users.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchUsers()
}

function handleSizeChange(val) {
  pageSize.value = val
  fetchUsers()
}

function handleCurrentChange(val) {
  currentPage.value = val
  fetchUsers()
}

async function fetchWarehouses() {
  try {
    const res = await adminApi.getWarehouses()
    warehouses.value = res.data || []
  } catch (error) {
    ElMessage.error('获取仓库列表失败')
  }
}

onMounted(() => {
  fetchUsers()
  fetchWarehouses()
})

function resetForm() {
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'worker'
  form.warehouse_id = null
  form.skill_picking = 0
  form.skill_staging = 0
  form.skill_shipping = 0
  editingId.value = null
}

function openCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
  resetForm()
  if (formRef.value) formRef.value.clearValidate()
}

function openEditDialog(row) {
  if (!canEditUser(row)) {
    ElMessage.warning('管理员只能编辑自己的账号')
    return
  }
  dialogMode.value = 'edit'
  dialogVisible.value = true
  editingId.value = row.id
  form.username = row.username
  form.email = row.email
  form.role = row.role
  form.warehouse_id = row.role === 'admin' ? null : (row.warehouse_id || null)
  form.skill_picking = row.skill_picking || 0
  form.skill_staging = row.skill_staging || 0
  form.skill_shipping = row.skill_shipping || 0
  if (formRef.value) formRef.value.clearValidate()
}

function openDetailDialog(row) {
  detailIsOtherAdmin.value = row.role === 'admin' && row.id !== authStore.currentUser?.id
  detailEditingId.value = row.id
  detailForm.username = row.username
  detailForm.email = row.email
  detailForm.role = row.role
  detailForm.warehouse_id = row.role === 'admin' ? null : (row.warehouse_id || null)
  detailForm.skill_picking = row.skill_picking || 0
  detailForm.skill_staging = row.skill_staging || 0
  detailForm.skill_shipping = row.skill_shipping || 0
  detailForm.avatar = row.avatar || ''
  detailVisible.value = true
  if (detailFormRef.value) detailFormRef.value.clearValidate()
}

async function saveDetail() {
  const valid = await detailFormRef.value.validate().catch(() => false)
  if (!valid) return

  detailSaving.value = true
  try {
    const payload = {
      username: detailForm.username,
      email: detailForm.email,
      role: detailForm.role,
      warehouse_id: detailForm.role === 'admin' ? null : detailForm.warehouse_id,
      skill_picking: detailForm.role === 'worker' ? detailForm.skill_picking : 0,
      skill_staging: detailForm.role === 'worker' ? detailForm.skill_staging : 0,
      skill_shipping: detailForm.role === 'worker' ? detailForm.skill_shipping : 0,
    }
    await adminApi.updateUser(detailEditingId.value, payload)
    ElMessage.success('详情保存成功')
    detailVisible.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    detailSaving.value = false
  }
}

async function onStatusChange(row, targetStatus) {
  try {
    await adminApi.updateUserStatus(row.id, targetStatus)
    ElMessage.success('状态更新成功')
  } catch (error) {
    row.is_active = !targetStatus
    ElMessage.error(error.response?.data?.detail || '更新状态失败')
  }
}

async function handleBatchDisable() {
  await ElMessageBox.confirm(`确认禁用选中的 ${selectedIds.value.length} 个用户吗？`, '提示', {
    type: 'warning',
  })
  await adminApi.batchDisableUsers(selectedIds.value)
  ElMessage.success('批量禁用成功')
  selectedIds.value = []
  fetchUsers()
}

async function saveUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      username: form.username,
      email: form.email,
      role: form.role,
      warehouse_id: form.role === 'admin' ? null : form.warehouse_id,
      skill_picking: form.role === 'worker' ? form.skill_picking : 0,
      skill_staging: form.role === 'worker' ? form.skill_staging : 0,
      skill_shipping: form.role === 'worker' ? form.skill_shipping : 0,
    }

    if (dialogMode.value === 'create') {
      payload.password = form.password
      await adminApi.createUser(payload)
      ElMessage.success('新增成功')
    } else {
      await adminApi.updateUser(editingId.value, payload)
      ElMessage.success('更新成功')
    }
    
    dialogVisible.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.users-page {
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

.table-card {
  border-radius: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.detail-card {
  border-radius: 12px;
}

.avatar-inline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.placeholder-note {
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 860px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
