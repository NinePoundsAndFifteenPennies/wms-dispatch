<template>
  <div class="warehouses-page">
    <section class="toolbar">
      <div>
        <h3>仓库管理</h3>
        <p>维护仓库基础信息与仓库图片（地图解析功能后续接入）。</p>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="searchQuery"
          placeholder="按仓库名称/地址搜索"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
        <el-button type="danger" plain :disabled="selectedIds.length === 0" @click="handleBatchDelete">
          批量禁用
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增仓库
        </el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-table :data="warehouses" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="52" />
        <el-table-column label="图片" width="88">
          <template #default="{ row }">
            <el-image
              v-if="row.cover_image"
              :src="row.cover_image"
              fit="cover"
              class="thumb"
              :preview-src-list="[row.cover_image]"
              preview-teleported
            />
            <span v-else class="empty-thumb"><el-icon><Picture /></el-icon></span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="仓库名称" min-width="170" />
        <el-table-column prop="address" label="地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="capacity" label="容量" width="100" />
        <el-table-column label="经纬度" min-width="180">
          <template #default="{ row }">
            <span>{{ row.latitude ?? '-' }}, {{ row.longitude ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" :before-change="() => beforeStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210">
          <template #default="{ row }">
            <el-button type="success" link @click="openDetailDialog(row)">详情</el-button>
            <el-button type="success" link @click="openImageDialog(row)">图片</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增仓库' : '编辑仓库'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="仓库地址" prop="address">
          <el-input v-model="form.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="纬度" prop="latitude">
              <el-input-number v-model="form.latitude" :step="0.000001" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="经度" prop="longitude">
              <el-input-number v-model="form.longitude" :step="0.000001" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="容量" prop="capacity">
          <el-input-number v-model="form.capacity" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveWarehouse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="仓库详情" width="760px">
      <div class="detail-grid">
        <el-card shadow="never" class="detail-card image-card">
          <template #header>
            <span>仓库图片</span>
          </template>
          <div class="detail-image-wrap">
            <el-image
              v-if="detailForm.cover_image"
              :src="detailForm.cover_image"
              fit="cover"
              class="detail-image"
              :preview-src-list="[detailForm.cover_image]"
              preview-teleported
            />
            <div v-else class="detail-image-placeholder">
              <el-icon><Picture /></el-icon>
              <span>暂无图片</span>
            </div>
          </div>
          <el-button style="margin-top: 10px" @click="openImageDialog({ id: detailEditingId, name: detailForm.name, cover_image: detailForm.cover_image })">
            管理图片
          </el-button>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>基础信息</span>
          </template>
          <el-form ref="detailFormRef" :model="detailForm" :rules="rules" label-width="110px">
            <el-form-item label="仓库名称" prop="name">
              <el-input v-model="detailForm.name" />
            </el-form-item>
            <el-form-item label="仓库地址" prop="address">
              <el-input v-model="detailForm.address" type="textarea" :rows="2" />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="纬度" prop="latitude">
                  <el-input-number v-model="detailForm.latitude" :step="0.000001" :precision="6" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="经度" prop="longitude">
                  <el-input-number v-model="detailForm.longitude" :step="0.000001" :precision="6" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="容量" prop="capacity">
              <el-input-number v-model="detailForm.capacity" :min="0" style="width: 100%" />
            </el-form-item>
            <el-form-item label="状态">
              <el-switch v-model="detailForm.is_active" />
            </el-form-item>
            <el-form-item label="备注" prop="description">
              <el-input v-model="detailForm.description" type="textarea" :rows="3" />
            </el-form-item>
          </el-form>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :loading="detailSaving" @click="saveDetail">保存详情</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="imageDialogVisible" width="520px" :title="`图片管理 - ${imageTargetName || ''}`" @closed="onImageDialogClosed">
      <div class="image-panel">
        <div class="image-preview-box">
          <el-image
            v-if="imagePreviewUrl"
            :src="imagePreviewUrl"
            fit="cover"
            class="image-preview"
            :preview-src-list="[imagePreviewUrl]"
            preview-teleported
          />
          <div v-else class="image-empty">当前无图片</div>
        </div>

        <el-upload
          accept=".jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif"
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          :on-change="onImageDialogFileChange"
          :before-upload="beforeImageUpload"
        >
          <el-button>选择新图片</el-button>
        </el-upload>

        <div class="image-actions">
          <el-button type="danger" plain :disabled="!imagePreviewUrl" @click="markRemoveImage">
            移除当前图片
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="closeImageDialog">取消</el-button>
        <el-button type="primary" :loading="savingImage" @click="saveImageChanges">保存图片变更</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Plus, Search } from '@element-plus/icons-vue'
import { warehousesApi } from '../api/warehouses'

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
const formRef = ref()
const detailVisible = ref(false)
const detailSaving = ref(false)
const detailEditingId = ref(null)
const detailFormRef = ref()
const form = reactive({
  name: '',
  address: '',
  latitude: null,
  longitude: null,
  capacity: 0,
  description: '',
})
const detailForm = reactive({
  name: '',
  address: '',
  latitude: null,
  longitude: null,
  capacity: 0,
  description: '',
  cover_image: '',
  is_active: true,
})

const imageDialogVisible = ref(false)
const imageTargetWarehouseId = ref(null)
const imageTargetName = ref('')
const imagePreviewUrl = ref('')
const imagePreviewObjectUrl = ref('')
const imageOriginalUrl = ref('')
const imageSelectedFile = ref(null)
const imageRemoveRequested = ref(false)
const savingImage = ref(false)

const rules = {
  name: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
  address: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }],
}

function onSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

function beforeImageUpload(file) {
  const typeOk = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)
  if (!typeOk) {
    ElMessage.error('仅支持 JPG/PNG/WEBP/GIF 图片')
  }
  return typeOk
}

function revokeImagePreviewObjectUrl() {
  if (imagePreviewObjectUrl.value) {
    URL.revokeObjectURL(imagePreviewObjectUrl.value)
    imagePreviewObjectUrl.value = ''
  }
}

function onImageDialogFileChange(file) {
  imageSelectedFile.value = file.raw || null
  if (file.raw) {
    revokeImagePreviewObjectUrl()
    imagePreviewObjectUrl.value = URL.createObjectURL(file.raw)
    imagePreviewUrl.value = imagePreviewObjectUrl.value
  }
  imageRemoveRequested.value = false
}

async function fetchWarehouses() {
  loading.value = true
  try {
    const res = await warehousesApi.getWarehouses({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
    })
    warehouses.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchWarehouses()
}

function handleSizeChange(size) {
  pageSize.value = size
  fetchWarehouses()
}

function handleCurrentChange(page) {
  currentPage.value = page
  fetchWarehouses()
}

function resetForm() {
  form.name = ''
  form.address = ''
  form.latitude = null
  form.longitude = null
  form.capacity = 0
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
  form.address = row.address || ''
  form.latitude = row.latitude !== null && row.latitude !== undefined ? Number(row.latitude) : null
  form.longitude = row.longitude !== null && row.longitude !== undefined ? Number(row.longitude) : null
  form.capacity = row.capacity || 0
  form.description = row.description || ''
  dialogVisible.value = true
  if (formRef.value) formRef.value.clearValidate()
}

function openImageDialog(row) {
  revokeImagePreviewObjectUrl()
  imageTargetWarehouseId.value = row.id
  imageTargetName.value = row.name
  imagePreviewUrl.value = row.cover_image || ''
  imageOriginalUrl.value = row.cover_image || ''
  imageSelectedFile.value = null
  imageRemoveRequested.value = false
  imageDialogVisible.value = true
}

function openDetailDialog(row) {
  detailEditingId.value = row.id
  detailForm.name = row.name
  detailForm.address = row.address || ''
  detailForm.latitude = row.latitude !== null && row.latitude !== undefined ? Number(row.latitude) : null
  detailForm.longitude = row.longitude !== null && row.longitude !== undefined ? Number(row.longitude) : null
  detailForm.capacity = row.capacity || 0
  detailForm.description = row.description || ''
  detailForm.cover_image = row.cover_image || ''
  detailForm.is_active = row.is_active
  detailVisible.value = true
  if (detailFormRef.value) detailFormRef.value.clearValidate()
}

function markRemoveImage() {
  revokeImagePreviewObjectUrl()
  imageRemoveRequested.value = true
  imageSelectedFile.value = null
  imagePreviewUrl.value = ''
}

function closeImageDialog() {
  imageDialogVisible.value = false
}

function onImageDialogClosed() {
  revokeImagePreviewObjectUrl()
}

async function saveImageChanges() {
  if (!imageTargetWarehouseId.value) return

  if (!imageSelectedFile.value && !imageRemoveRequested.value) {
    ElMessage.info('没有图片变更')
    return
  }

  savingImage.value = true
  try {
    if (imageSelectedFile.value) {
      await warehousesApi.uploadWarehouseImage(imageTargetWarehouseId.value, imageSelectedFile.value)
      ElMessage.success('图片已更新')
    } else if (imageRemoveRequested.value && imageOriginalUrl.value) {
      await warehousesApi.removeWarehouseImage(imageTargetWarehouseId.value)
      ElMessage.success('图片已移除')
    }

    imageDialogVisible.value = false
    revokeImagePreviewObjectUrl()
    await fetchWarehouses()
    if (detailVisible.value && detailEditingId.value === imageTargetWarehouseId.value) {
      const latest = warehouses.value.find((item) => item.id === detailEditingId.value)
      detailForm.cover_image = latest?.cover_image || ''
    }
  } finally {
    savingImage.value = false
  }
}

async function saveWarehouse() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      name: form.name,
      address: form.address,
      latitude: form.latitude,
      longitude: form.longitude,
      capacity: form.capacity ?? 0,
      description: form.description || null,
    }
    if (dialogMode.value === 'create') {
      await warehousesApi.createWarehouse(payload)
      ElMessage.success('新增成功')
    } else {
      await warehousesApi.updateWarehouse(editingId.value, payload)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    fetchWarehouses()
  } finally {
    saving.value = false
  }
}

async function saveDetail() {
  const valid = await detailFormRef.value.validate().catch(() => false)
  if (!valid) return

  detailSaving.value = true
  try {
    await warehousesApi.updateWarehouse(detailEditingId.value, {
      name: detailForm.name,
      address: detailForm.address,
      latitude: detailForm.latitude,
      longitude: detailForm.longitude,
      capacity: detailForm.capacity ?? 0,
      description: detailForm.description || null,
    })
    await warehousesApi.updateWarehouseStatus(detailEditingId.value, detailForm.is_active)
    ElMessage.success('详情保存成功')
    detailVisible.value = false
    fetchWarehouses()
  } finally {
    detailSaving.value = false
  }
}

async function beforeStatusChange(row) {
  const targetStatus = !row.is_active
  try {
    await warehousesApi.updateWarehouseStatus(row.id, targetStatus)
    ElMessage.success('状态更新成功')
    return true
  } catch {
    return false
  }
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认禁用选中的 ${selectedIds.value.length} 个仓库吗？`, '提示', {
    type: 'warning',
  })
  await warehousesApi.batchDeleteWarehouses(selectedIds.value)
  ElMessage.success('批量禁用成功')
  selectedIds.value = []
  fetchWarehouses()
}

onMounted(() => {
  fetchWarehouses()
})
</script>

<style scoped>
.warehouses-page {
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

.thumb {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  border: 1px solid #dce6ef;
}

.empty-thumb {
  display: inline-grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 8px;
  border: 1px dashed #d4dce6;
  color: #94a3b8;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.image-panel {
  display: grid;
  gap: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 12px;
}

.detail-card {
  border-radius: 12px;
}

.image-card {
  align-self: start;
}

.detail-image-wrap {
  width: 100%;
  min-height: 220px;
  border-radius: 10px;
  border: 1px dashed #cbd5e1;
  display: grid;
  place-items: center;
}

.detail-image {
  width: 100%;
  min-height: 220px;
  max-height: 300px;
  border-radius: 10px;
}

.detail-image-placeholder {
  color: #94a3b8;
  display: grid;
  gap: 8px;
  place-items: center;
}

.image-preview-box {
  border: 1px dashed #d5dee9;
  border-radius: 12px;
  padding: 10px;
  min-height: 190px;
  display: grid;
  place-items: center;
  background: #f8fbff;
}

.image-preview {
  width: 100%;
  max-height: 240px;
  border-radius: 10px;
}

.image-empty {
  color: #94a3b8;
}

.image-actions {
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

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
