<template>
  <div class="dispatcher-inventory-page">
    <section class="hero-card">
      <img :src="heroImageUrl" :alt="`${warehouse.name || '仓库'} 封面图片`" class="hero-image" />
      <div class="hero-overlay">
        <p class="hero-description">{{ warehouse.description || '暂无仓库备注' }}</p>
        <p class="hero-address">{{ warehouse.address || '-' }}</p>
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
      <span class="toolbar-meta">共 {{ total }} 项</span>
    </section>

    <el-card shadow="never" v-loading="loading" class="inventory-card">
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Search } from '@element-plus/icons-vue'
import { dispatcherInventoryApi } from '../../api/dispatcher/inventory'

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
  description: '',
  cover_image: '',
  is_active: true,
})

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

async function fetchInventory() {
  loading.value = true
  try {
    const res = await dispatcherInventoryApi.getInventory({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
    })
    const data = res.data || {}
    Object.assign(warehouse, data.warehouse || {})
    items.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取库存失败')
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

onMounted(fetchInventory)
</script>

<style scoped>
.dispatcher-inventory-page {
  display: grid;
  gap: 14px;
}

.hero-card {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #d6d0c4;
}

.hero-image {
  width: 100%;
  height: 180px;
  object-fit: cover;
  display: block;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 14px 18px;
  background: linear-gradient(180deg, rgba(12, 12, 12, 0.08) 20%, rgba(12, 12, 12, 0.58) 100%);
  color: #fff;
}

.hero-description,
.hero-address {
  margin: 0;
}

.hero-description {
  font-size: 16px;
  font-weight: 600;
}

.hero-address {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar :deep(.el-input) {
  max-width: 560px;
}

.toolbar-meta {
  margin-left: auto;
  color: #6f675a;
  font-size: 13px;
}

.inventory-card {
  border: 1px solid #d6d0c4;
}

:deep(.el-table th.el-table__cell) {
  background: #f5ece0;
  color: #6a5338;
}

.thumb {
  width: 52px;
  height: 52px;
  border-radius: 10px;
}

.empty-thumb {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f2e9dd;
  color: #8a7763;
}

.pagination-container {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 720px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-meta {
    margin-left: 0;
  }
}
</style>
