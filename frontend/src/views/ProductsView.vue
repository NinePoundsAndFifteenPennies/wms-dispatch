<template>
  <div class="products-page">
    <section class="toolbar">
      <div>
        <h3>产品管理</h3>
        <p>维护 SKU 主数据，支持图片上传、搜索与批量禁用。</p>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="searchQuery"
          placeholder="按 SKU / 名称 / 类别搜索"
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
          新增产品
        </el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-table :data="products" stripe @selection-change="onSelectionChange">
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
        <el-table-column prop="name" label="产品名称" min-width="180" />
        <el-table-column prop="sku" label="SKU" min-width="120" />
        <el-table-column prop="category" label="类别" min-width="130" />
        <el-table-column prop="unit_of_measure" label="单位" width="96" />
        <el-table-column prop="unit_weight" label="重量(g)" width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="val => onStatusChange(row, val)" />
          </template>
        </el-table-column>
        <el-table-column label="技能要求" min-width="200">
          <template #default="{ row }">
            P:{{ row.req_skill_picking }} / S:{{ row.req_skill_staging }} / H:{{ row.req_skill_shipping }}
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

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增产品' : '编辑产品'" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="SKU" prop="sku">
              <el-input v-model="form.sku" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="产品名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="类别" prop="category">
              <el-input v-model="form.category" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计量单位" prop="unit_of_measure">
              <el-input v-model="form.unit_of_measure" placeholder="piece / box / kg" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="单位重量(g)" prop="unit_weight">
          <el-input-number v-model="form.unit_weight" :min="0" :precision="2" :step="0.1" style="width: 100%" />
        </el-form-item>

        <el-alert
          type="info"
          show-icon
          :closable="false"
          title="图片管理请使用列表中的“图片”按钮，可执行添加、替换、移除。"
          style="margin-bottom: 12px"
        />

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="分拣要求" prop="req_skill_picking">
              <el-input-number v-model="form.req_skill_picking" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备货要求" prop="req_skill_staging">
              <el-input-number v-model="form.req_skill_staging" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="发货要求" prop="req_skill_shipping">
              <el-input-number v-model="form.req_skill_shipping" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProduct">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="产品详情" width="760px">
      <div class="detail-grid">
        <el-card shadow="never" class="detail-card image-card">
          <template #header>
            <span>产品图片</span>
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
          <el-button style="margin-top: 10px" @click="openImageDialog({ id: detailEditingId.value, name: detailForm.name, cover_image: detailForm.cover_image })">
            管理图片
          </el-button>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>基础信息</span>
          </template>
          <el-form ref="detailFormRef" :model="detailForm" :rules="rules" label-width="110px">
            <el-form-item label="产品名称" prop="name">
              <el-input v-model="detailForm.name" />
            </el-form-item>
            <el-form-item label="SKU" prop="sku">
              <el-input v-model="detailForm.sku" />
            </el-form-item>
            <el-form-item label="类别" prop="category">
              <el-input v-model="detailForm.category" />
            </el-form-item>
            <el-form-item label="计量单位" prop="unit_of_measure">
              <el-input v-model="detailForm.unit_of_measure" />
            </el-form-item>
            <el-form-item label="单位重量(g)" prop="unit_weight">
              <el-input-number v-model="detailForm.unit_weight" :min="0" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="分拣要求" prop="req_skill_picking">
              <el-input-number v-model="detailForm.req_skill_picking" :min="0" :max="10" />
            </el-form-item>
            <el-form-item label="备货要求" prop="req_skill_staging">
              <el-input-number v-model="detailForm.req_skill_staging" :min="0" :max="10" />
            </el-form-item>
            <el-form-item label="发货要求" prop="req_skill_shipping">
              <el-input-number v-model="detailForm.req_skill_shipping" :min="0" :max="10" />
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
import { productsApi } from '../api/products'

const products = ref([])
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
const detailSaving = ref(false)
const imageDialogVisible = ref(false)
const imageTargetProductId = ref(null)
const imageTargetName = ref('')
const imagePreviewUrl = ref('')
const imagePreviewObjectUrl = ref('')
const imageOriginalUrl = ref('')
const imageSelectedFile = ref(null)
const imageRemoveRequested = ref(false)
const savingImage = ref(false)
const formRef = ref()
const detailFormRef = ref()
const form = reactive({
  sku: '',
  name: '',
  category: '',
  unit_weight: 0,
  unit_of_measure: 'piece',
  req_skill_picking: 0,
  req_skill_staging: 0,
  req_skill_shipping: 0,
  description: '',
})
const detailForm = reactive({
  sku: '',
  name: '',
  category: '',
  unit_weight: 0,
  unit_of_measure: 'piece',
  req_skill_picking: 0,
  req_skill_staging: 0,
  req_skill_shipping: 0,
  description: '',
  cover_image: '',
  is_active: true,
})

const rules = {
  sku: [{ required: true, message: '请输入 SKU', trigger: 'blur' }],
  name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  unit_of_measure: [{ required: true, message: '请输入计量单位', trigger: 'blur' }],
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

async function fetchProducts() {
  loading.value = true
  try {
    const res = await productsApi.getProducts({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
    })
    products.value = res.data.items || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchProducts()
}

function handleSizeChange(size) {
  pageSize.value = size
  fetchProducts()
}

function handleCurrentChange(page) {
  currentPage.value = page
  fetchProducts()
}

function resetForm() {
  form.sku = ''
  form.name = ''
  form.category = ''
  form.unit_weight = 0
  form.unit_of_measure = 'piece'
  form.req_skill_picking = 0
  form.req_skill_staging = 0
  form.req_skill_shipping = 0
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
  form.sku = row.sku
  form.name = row.name
  form.category = row.category || ''
  form.unit_weight = Number(row.unit_weight || 0)
  form.unit_of_measure = row.unit_of_measure || 'piece'
  form.req_skill_picking = Number(row.req_skill_picking || 0)
  form.req_skill_staging = Number(row.req_skill_staging || 0)
  form.req_skill_shipping = Number(row.req_skill_shipping || 0)
  form.description = row.description || ''
  dialogVisible.value = true
  if (formRef.value) formRef.value.clearValidate()
}

function openImageDialog(row) {
  revokeImagePreviewObjectUrl()
  imageTargetProductId.value = row.id
  imageTargetName.value = row.name
  imagePreviewUrl.value = row.cover_image || ''
  imageOriginalUrl.value = row.cover_image || ''
  imageSelectedFile.value = null
  imageRemoveRequested.value = false
  imageDialogVisible.value = true
}

function openDetailDialog(row) {
  detailEditingId.value = row.id
  detailForm.sku = row.sku
  detailForm.name = row.name
  detailForm.category = row.category || ''
  detailForm.unit_weight = Number(row.unit_weight || 0)
  detailForm.unit_of_measure = row.unit_of_measure || 'piece'
  detailForm.req_skill_picking = Number(row.req_skill_picking || 0)
  detailForm.req_skill_staging = Number(row.req_skill_staging || 0)
  detailForm.req_skill_shipping = Number(row.req_skill_shipping || 0)
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
  if (!imageTargetProductId.value) return

  if (!imageSelectedFile.value && !imageRemoveRequested.value) {
    ElMessage.info('没有图片变更')
    return
  }

  savingImage.value = true
  try {
    if (imageSelectedFile.value) {
      await productsApi.uploadProductImage(imageTargetProductId.value, imageSelectedFile.value)
      ElMessage.success('图片已更新')
    } else if (imageRemoveRequested.value && imageOriginalUrl.value) {
      await productsApi.removeProductImage(imageTargetProductId.value)
      ElMessage.success('图片已移除')
    }

    imageDialogVisible.value = false
    revokeImagePreviewObjectUrl()
    await fetchProducts()
    if (detailVisible.value && detailEditingId.value === imageTargetProductId.value) {
      const latest = products.value.find((item) => item.id === detailEditingId.value)
      detailForm.cover_image = latest?.cover_image || ''
    }
  } finally {
    savingImage.value = false
  }
}

async function saveProduct() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      sku: form.sku,
      name: form.name,
      category: form.category || null,
      unit_weight: form.unit_weight || null,
      unit_of_measure: form.unit_of_measure,
      req_skill_picking: form.req_skill_picking,
      req_skill_staging: form.req_skill_staging,
      req_skill_shipping: form.req_skill_shipping,
      description: form.description || null,
    }

    if (dialogMode.value === 'create') {
      await productsApi.createProduct(payload)
      ElMessage.success('新增成功')
    } else {
      await productsApi.updateProduct(editingId.value, payload)
      ElMessage.success('更新成功')
    }

    dialogVisible.value = false
    fetchProducts()
  } finally {
    saving.value = false
  }
}

async function onStatusChange(row, targetStatus) {
  try {
    await productsApi.updateProductStatus(row.id, targetStatus)
    ElMessage.success('状态更新成功')
  } catch {
    row.is_active = !targetStatus
  }
}

async function saveDetail() {
  const valid = await detailFormRef.value.validate().catch(() => false)
  if (!valid) return

  detailSaving.value = true
  try {
    await productsApi.updateProduct(detailEditingId.value, {
      sku: detailForm.sku,
      name: detailForm.name,
      category: detailForm.category || null,
      unit_weight: detailForm.unit_weight || null,
      unit_of_measure: detailForm.unit_of_measure,
      req_skill_picking: detailForm.req_skill_picking,
      req_skill_staging: detailForm.req_skill_staging,
      req_skill_shipping: detailForm.req_skill_shipping,
      description: detailForm.description || null,
    })
    await productsApi.updateProductStatus(detailEditingId.value, detailForm.is_active)
    ElMessage.success('详情保存成功')
    detailVisible.value = false
    fetchProducts()
  } finally {
    detailSaving.value = false
  }
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认禁用选中的 ${selectedIds.value.length} 个产品吗？`, '提示', {
    type: 'warning',
  })
  await productsApi.batchDeleteProducts(selectedIds.value)
  ElMessage.success('批量禁用成功')
  selectedIds.value = []
  fetchProducts()
}

onMounted(() => {
  fetchProducts()
})
</script>

<style scoped>
.products-page {
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
  background: #f8fafc;
}

.detail-image {
  width: 210px;
  height: 210px;
  border-radius: 8px;
}

.detail-image-placeholder {
  color: #94a3b8;
  display: grid;
  place-items: center;
  gap: 6px;
}

.detail-image-placeholder .el-icon {
  font-size: 26px;
}

.image-preview-box {
  width: 180px;
  height: 180px;
  border-radius: 10px;
  border: 1px dashed #cbd5e1;
  display: grid;
  place-items: center;
  background: #f8fafc;
}

.image-preview {
  width: 160px;
  height: 160px;
  border-radius: 8px;
}

.image-empty {
  color: #94a3b8;
  font-size: 13px;
}

.image-actions {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1060px) {
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
