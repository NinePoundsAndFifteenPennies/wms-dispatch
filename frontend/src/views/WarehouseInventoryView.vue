<template>
  <div class="warehouse-inventory-page">
    <section class="hero-card">
      <img :src="heroImageUrl" alt="warehouse cover" class="hero-image" />
      <div class="hero-overlay">
        <el-button text class="back-btn" @click="router.push('/warehouses')">← 返回仓库管理</el-button>
        <h2>{{ warehouse.name || '仓库库存详情' }}</h2>
        <p>{{ warehouse.address || '-' }}</p>
      </div>
    </section>

    <section class="toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="按产品名称 / SKU / 类别搜索库存项"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
    </section>

    <el-card shadow="never" v-loading="loading">
      <el-table :data="items" stripe>
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
            <el-button type="primary" link @click="openAdjustDialog(row)">盘点修正</el-button>
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

    <el-dialog v-model="adjustDialogVisible" title="人工盘点修正" width="520px">
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
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingAdjust" @click="submitAdjust">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { warehousesApi } from '../api/warehouses'

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
  id: null,
  name: '',
  address: '',
  cover_image: '',
})

const adjustDialogVisible = ref(false)
const adjustingItem = ref(null)
const adjustFormRef = ref()
const adjustForm = reactive({
  qty_on_hand: 0,
})
const savingAdjust = ref(false)

const adjustRules = {
  qty_on_hand: [{ required: true, message: '请输入盘点后的现存量', trigger: 'change' }],
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
  adjustingItem.value = row
  adjustForm.qty_on_hand = row.qty_on_hand
  adjustDialogVisible.value = true
  if (adjustFormRef.value) adjustFormRef.value.clearValidate()
}

async function submitAdjust() {
  const valid = await adjustFormRef.value.validate().catch(() => false)
  if (!valid || !adjustingItem.value) return

  savingAdjust.value = true
  try {
    await warehousesApi.adjustWarehouseInventoryStocktake(
      warehouseId,
      adjustingItem.value.id,
      adjustForm.qty_on_hand,
    )
    ElMessage.success('盘点修正成功')
    adjustDialogVisible.value = false
    await fetchInventory()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '盘点修正失败')
  } finally {
    savingAdjust.value = false
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

.hero-overlay h2 {
  margin: 0;
}

.hero-overlay p {
  margin: 0;
  opacity: 0.92;
}

.back-btn {
  align-self: flex-start;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  padding: 6px 12px;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 12px 14px;
  border: 1px solid #d8e1eb;
  border-radius: 12px;
  background: #ffffff;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
