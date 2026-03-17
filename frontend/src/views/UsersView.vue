<template>
  <div class="users-page">
    <section class="toolbar">
      <div>
        <h3>用户管理</h3>
        <p>维护账号信息、角色与启用状态（演示页面，不落库）。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新增用户
      </el-button>
    </section>

    <el-card shadow="never" class="table-card">
      <el-table :data="users" stripe>
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="120" />
        <el-table-column prop="warehouse" label="所属仓库" min-width="140" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增用户' : '编辑用户'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="admin" value="admin" />
            <el-option label="dispatcher" value="dispatcher" />
            <el-option label="worker" value="worker" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库" prop="warehouse">
          <el-input v-model="form.warehouse" :disabled="form.role === 'admin'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const users = ref([
  { id: 1, username: 'admin', email: 'admin@wms.local', role: 'admin', warehouse: '-', is_active: true },
  {
    id: 2,
    username: 'dispatcher_zhang',
    email: 'dispatcher_zhang@wms.local',
    role: 'dispatcher',
    warehouse: '华南中心仓',
    is_active: true,
  },
  { id: 3, username: 'worker_li', email: 'worker_li@wms.local', role: 'worker', warehouse: '华南中心仓', is_active: true },
])

const dialogVisible = ref(false)
const dialogMode = ref('create')
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  username: '',
  email: '',
  role: 'worker',
  warehouse: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  warehouse: [
    {
      validator: (_, value, callback) => {
        if (form.role === 'admin' || value) {
          callback()
          return
        }
        callback(new Error('非管理员必须填写仓库'))
      },
      trigger: 'blur',
    },
  ],
}

function resetForm() {
  form.username = ''
  form.email = ''
  form.role = 'worker'
  form.warehouse = ''
  editingId.value = null
}

function openCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
  resetForm()
}

function openEditDialog(row) {
  dialogMode.value = 'edit'
  dialogVisible.value = true
  editingId.value = row.id
  form.username = row.username
  form.email = row.email
  form.role = row.role
  form.warehouse = row.role === 'admin' ? '' : row.warehouse
}

async function saveUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const payload = {
    username: form.username,
    email: form.email,
    role: form.role,
    warehouse: form.role === 'admin' ? '-' : form.warehouse,
    is_active: true,
  }

  if (dialogMode.value === 'create') {
    const nextId = users.value.reduce((maxId, item) => Math.max(maxId, item.id), 0) + 1
    users.value.unshift({ ...payload, id: nextId })
    ElMessage.success('已新增用户（演示数据）')
  } else {
    const target = users.value.find((item) => item.id === editingId.value)
    if (target) {
      Object.assign(target, payload)
    }
    ElMessage.success('已更新用户（演示数据）')
  }
  dialogVisible.value = false
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

@media (max-width: 860px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
