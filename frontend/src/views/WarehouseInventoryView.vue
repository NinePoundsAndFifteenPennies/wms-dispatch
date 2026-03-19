<template>
  <div class="warehouse-inventory-page">
    <section class="hero-card">
      <img :src="heroImageUrl" :alt="`${warehouse.name || '仓库'} 封面图片`" class="hero-image" />
      <div class="hero-overlay">
        <p class="hero-description">{{ warehouse.description || '暂无仓库备注' }}</p>
        <p class="hero-address">{{ warehouse.address || '-' }}</p>
        <el-button text class="back-btn" @click="router.push('/warehouses')">← 返回仓库管理</el-button>
      </div>
    </section>

    <section class="toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="按产品名称 / SKU / 类别搜索库存项"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
      <el-button type="primary" :disabled="!warehouse.is_active" @click="openInboundDialog">进货</el-button>
    </section>

    <el-card shadow="never" v-loading="loading">
      <el-table :data="items" stripe>
        <el-table-column label="图片" width="88">
          <template #default="{ row }">
            <el-image
              v-if="row.product_cover_image"
              :src="row.product_cover_image"
              fit="cover"
              class="thumb"
              :preview-src-list="[row.product_cover_image]"
              preview-teleported
            />
            <span v-else class="empty-thumb"><el-icon><Picture /></el-icon></span>
          </template>
        </el-table-column>
        <el-table-column prop="sku" label="SKU" min-width="130" />
        <el-table-column prop="product_name" label="产品名称" min-width="180" />
        <el-table-column prop="category" label="类别" min-width="130">
          <template #default="{ row }">
            <span>{{ row.category || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="可用状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.product_is_active ? 'success' : 'danger'" effect="light">
              {{ row.product_is_active ? '可用' : '不可用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="qty_on_hand" label="现存量" width="100" />
        <el-table-column prop="qty_reserved" label="预留量" width="100" />
        <el-table-column prop="qty_locked" label="锁定量" width="100" />
        <el-table-column prop="qty_available" label="可用量" width="100" />
        <el-table-column prop="qty_threshold" label="阈值" width="100" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <span v-if="!canAdjustStocktake(row)" class="action-disabled">盘点修正</span>
            <el-button
              v-else
              type="primary"
              link
              :aria-label="`为 ${row.product_name} 进行盘点修正`"
              @click="openAdjustDialog(row)"
            >
              盘点修正
            </el-button>
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

    <el-dialog v-model="adjustDialogVisible" title="人工盘点修正" width="560px">
      <el-form ref="adjustFormRef" :model="adjustForm" :rules="adjustRules" label-width="120px">
        <el-form-item label="产品">
          <span>{{ adjustingItem?.product_name || '-' }}（{{ adjustingItem?.sku || '-' }}）</span>
        </el-form-item>
        <el-form-item label="最小允许值">
          <span>{{ minAllowedQty }}</span>
        </el-form-item>
        <el-form-item label="修正现存量" prop="qty_on_hand">
          <el-input-number
            v-model="adjustForm.qty_on_hand"
            :min="minAllowedQty"
            :step="1"
            :precision="0"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="库存阈值" prop="qty_threshold">
          <el-input-number
            v-model="adjustForm.qty_threshold"
            :min="0"
            :step="1"
            :precision="0"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="修正原因">
          <el-input v-model="adjustForm.reason" type="textarea" :rows="2" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingAdjust" @click="submitAdjust">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="inboundDialogVisible" title="进货" width="560px">
      <el-form ref="inboundFormRef" :model="inboundForm" :rules="inboundRules" label-width="110px">
        <el-form-item label="选择产品" prop="product_id">
          <el-select
            v-model="inboundForm.product_id"
            filterable
            remote
            reserve-keyword
            clearable
            placeholder="输入产品名称 / SKU / 类别搜索"
            :remote-method="searchInboundProducts"
            :loading="inboundProductsLoading"
            style="width: 100%"
          >
            <el-option
              v-for="option in inboundProductOptions"
              :key="option.id"
              :label="`${option.name}（${option.sku}）`"
              :value="option.id"
              :disabled="!option.is_active"
            >
              <div class="product-option">
                <span>{{ option.name }}（{{ option.sku }}）</span>
                <el-tag size="small" :type="option.is_active ? 'success' : 'danger'" effect="plain">
                  {{ option.is_active ? '可用' : '不可用' }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="进货数量" prop="qty">
          <el-input-number v-model="inboundForm.qty" :min="1" :step="1" :precision="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="说明（可选）">
          <el-input v-model="inboundForm.reason" type="textarea" :rows="2" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inboundDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingInbound" @click="submitInbound">确认进货</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Search } from '@element-plus/icons-vue'
import { warehousesApi } from '../api/warehouses'
import { productsApi } from '../api/products'

const route = useRoute()
const router = useRouter()
const warehouseId = Number(route.params.id)

const loading = ref(false)
const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const warehouse = reactive({
  id: warehouseId,
  name: '',
  address: '',
  description: '',
  cover_image: '',
  is_active: true,
})

const adjustDialogVisible = ref(false)
const adjustingItem = ref(null)
const adjustFormRef = ref()
const adjustForm = reactive({
  qty_on_hand: 0,
  qty_threshold: 0,
  reason: '',
})
const savingAdjust = ref(false)

const inboundDialogVisible = ref(false)
const inboundFormRef = ref()
const inboundForm = reactive({
  product_id: null,
  qty: 1,
  reason: '',
})
const savingInbound = ref(false)
const inboundProductOptions = ref([])
const inboundProductsLoading = ref(false)

const adjustRules = {
  qty_on_hand: [{ required: true, message: '请输入盘点后的现存量', trigger: 'change' }],
  qty_threshold: [{ required: true, message: '请输入库存阈值', trigger: 'change' }],
}

const inboundRules = {
  product_id: [{ required: true, message: '请选择产品', trigger: 'change' }],
  qty: [{ required: true, message: '请输入进货数量', trigger: 'change' }],
}

const defaultHeroImage = `data:image/svg+xml;utf8,${encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="1400" height="360" viewBox="0 0 1400 360">
    <defs>
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#0f766e"/>
        <stop offset="100%" stop-color="#1d4ed8"/>
      </linearGradient>
    </defs>
    <rect width="1400" height="360" fill="url(#g)"/>
    <g opacity="0.22" fill="#ffffff">
      <rect x="100" y="90" width="210" height="190" rx="12"/>
      <rect x="350" y="70" width="210" height="210" rx="12"/>
      <rect x="600" y="110" width="210" height="170" rx="12"/>
      <rect x="850" y="80" width="210" height="200" rx="12"/>
      <rect x="1100" y="95" width="210" height="185" rx="12"/>
    </g>
  </svg>
`)}`

const heroImageUrl = computed(() => warehouse.cover_image || defaultHeroImage)
const minAllowedQty = computed(() => {
  if (!adjustingItem.value) return 0
  return adjustingItem.value.qty_reserved + adjustingItem.value.qty_locked
})

function canAdjustStocktake(row) {
  return Boolean(warehouse.is_active && row.product_is_active)
}

async function fetchInventory() {
  if (!warehouseId) return
  loading.value = true
  try {
    const res = await warehousesApi.getWarehouseInventory(warehouseId, {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
    })
    const data = res.data || {}
    Object.assign(warehouse, data.warehouse || {})
    if (warehouse.name) {
      await router.replace({
        path: route.path,
        query: { ...route.query, name: warehouse.name },
      })
    }
    items.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取仓库库存失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchInventory()
}

function handleSizeChange(size) {
  pageSize.value = size
  fetchInventory()
}

function handleCurrentChange(page) {
  currentPage.value = page
  fetchInventory()
}

function openAdjustDialog(row) {
  if (!canAdjustStocktake(row)) return
  adjustingItem.value = row
  adjustForm.qty_on_hand = row.qty_on_hand
  adjustForm.qty_threshold = row.qty_threshold
  adjustForm.reason = ''
  adjustDialogVisible.value = true
  if (adjustFormRef.value) adjustFormRef.value.clearValidate()
}

async function submitAdjust() {
  const valid = await adjustFormRef.value.validate().catch(() => false)
  if (!valid || !adjustingItem.value) return

  const loweringToBelowThreshold =
    adjustingItem.value.qty_on_hand >= adjustingItem.value.qty_threshold &&
    adjustForm.qty_on_hand < adjustForm.qty_threshold

  if (loweringToBelowThreshold) {
    await ElMessageBox.confirm(
      '修正后现存量将低于库存阈值，可能触发库存预警。是否继续？',
      '库存预警提示',
      { type: 'warning' },
    ).catch(() => {
      return Promise.reject(new Error('cancel'))
    })
  }

  savingAdjust.value = true
  try {
    await warehousesApi.adjustWarehouseInventoryStocktake(warehouseId, adjustingItem.value.id, {
      qty_on_hand: adjustForm.qty_on_hand,
      qty_threshold: adjustForm.qty_threshold,
      reason: adjustForm.reason || null,
    })
    ElMessage.success('库存修正成功')
    adjustDialogVisible.value = false
    await fetchInventory()
  } catch (error) {
    if (error.message !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '库存修正失败')
    }
  } finally {
    savingAdjust.value = false
  }
}

async function searchInboundProducts(keyword = '') {
  inboundProductsLoading.value = true
  try {
    const res = await productsApi.getProducts({
      page: 1,
      page_size: 10,
      search: keyword || undefined,
    })
    inboundProductOptions.value = res.data?.items || []
  } finally {
    inboundProductsLoading.value = false
  }
}

async function openInboundDialog() {
  if (!warehouse.is_active) {
    ElMessage.warning('禁用仓库不支持进货')
    return
  }
  inboundForm.product_id = null
  inboundForm.qty = 1
  inboundForm.reason = ''
  inboundDialogVisible.value = true
  if (inboundFormRef.value) inboundFormRef.value.clearValidate()
  await searchInboundProducts('')
}

async function submitInbound() {
  const valid = await inboundFormRef.value.validate().catch(() => false)
  if (!valid) return

  savingInbound.value = true
  try {
    await warehousesApi.warehouseInventoryInbound(warehouseId, {
      product_id: inboundForm.product_id,
      qty: inboundForm.qty,
      reason: inboundForm.reason || null,
    })
    ElMessage.success('进货成功')
    inboundDialogVisible.value = false
    await fetchInventory()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '进货失败')
  } finally {
    savingInbound.value = false
  }
}

onMounted(() => {
  fetchInventory()
})
</script>

<style scoped>
.warehouse-inventory-page {
  display: grid;
  gap: 12px;
}

.hero-card {
  position: relative;
  height: 220px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #d8e1eb;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 8px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.12) 5%, rgba(0, 0, 0, 0.56) 100%);
}

.hero-description {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  max-width: min(920px, 100%);
}

.hero-address {
  margin: 0;
  opacity: 0.92;
}

.back-btn {
  align-self: flex-start;
  margin-top: 6px;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  padding: 6px 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #d8e1eb;
  border-radius: 12px;
  background: #ffffff;
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

.action-disabled {
  color: #c0cad6;
  cursor: not-allowed;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.product-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

@media (max-width: 980px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
