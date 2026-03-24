<template>
  <div class="flow-record-page">
    <section class="flow-toolbar">
      <p>按仓库展示库存流水曲线，点击节点可查看当日流水明细。</p>
      <el-select v-model="days" style="width: 160px" @change="fetchTrends">
        <el-option :value="7" label="近 7 天" />
        <el-option :value="14" label="近 14 天" />
        <el-option :value="30" label="近 30 天" />
      </el-select>
    </section>

    <el-empty v-if="!loading && !warehouseSeries.length" description="暂无仓库流水数据" />

    <section class="flow-grid" v-loading="loading">
      <InventoryFlowLineChart
        v-for="item in warehouseSeries"
        :key="item.warehouse_id"
        :title="item.warehouse_name"
        subtitle="纵轴为流水笔数，悬停可查看变动总量"
        :points="item.points"
        @point-click="(point) => openNodeDetails(item, point)"
      />
    </section>

    <InventoryFlowNodeDetailDialog
      v-model="nodeDialogVisible"
      title="仓库流水节点详情"
      :warehouse-name="activeNode.warehouse_name"
      :date="activeNode.date"
      :movement-count="activeNode.movement_count"
      :total-abs-delta="activeNode.total_abs_delta"
      :positive-delta-on-hand="activeNode.positive_delta_on_hand"
      :negative-delta-on-hand-abs="activeNode.negative_delta_on_hand_abs"
      :rows="nodeRows"
      :loading="nodeLoading"
      :total="nodeTotal"
      :page="nodePage"
      :page-size="nodePageSize"
      @current-change="handleNodePageChange"
      @size-change="handleNodePageSizeChange"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { warehousesApi } from '../../api/admin/warehouses'
import InventoryFlowLineChart from '../../components/shared/InventoryFlowLineChart.vue'
import InventoryFlowNodeDetailDialog from '../../components/shared/InventoryFlowNodeDetailDialog.vue'

const loading = ref(false)
const days = ref(14)
const warehouseSeries = ref([])

const nodeDialogVisible = ref(false)
const nodeLoading = ref(false)
const nodeRows = ref([])
const nodeTotal = ref(0)
const nodePage = ref(1)
const nodePageSize = ref(20)
const activeNode = ref({
  warehouse_id: null,
  warehouse_name: '',
  date: '',
  movement_count: 0,
  total_abs_delta: 0,
  positive_delta_on_hand: 0,
  negative_delta_on_hand_abs: 0,
})

async function fetchTrends() {
  loading.value = true
  try {
    const res = await warehousesApi.getInventoryFlowTrends({ days: days.value })
    warehouseSeries.value = res.data?.warehouses || []
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载仓库流水趋势失败')
  } finally {
    loading.value = false
  }
}

async function fetchNodeDetails() {
  if (!activeNode.value.warehouse_id || !activeNode.value.date) return

  nodeLoading.value = true
  try {
    const res = await warehousesApi.getWarehouseInventoryFlowNodeDetails(activeNode.value.warehouse_id, {
      date: activeNode.value.date,
      page: nodePage.value,
      page_size: nodePageSize.value,
    })
    const data = res.data || {}
    activeNode.value = {
      ...activeNode.value,
      warehouse_name: data.warehouse_name || activeNode.value.warehouse_name,
      movement_count: data.movement_count || 0,
      total_abs_delta: data.total_abs_delta || 0,
      positive_delta_on_hand: data.positive_delta_on_hand || 0,
      negative_delta_on_hand_abs: data.negative_delta_on_hand_abs || 0,
    }
    nodeRows.value = data.items || []
    nodeTotal.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载流水节点详情失败')
  } finally {
    nodeLoading.value = false
  }
}

function openNodeDetails(warehouse, point) {
  activeNode.value = {
    warehouse_id: warehouse.warehouse_id,
    warehouse_name: warehouse.warehouse_name,
    date: point.date,
    movement_count: point.movement_count,
    total_abs_delta: point.total_abs_delta,
    positive_delta_on_hand: 0,
    negative_delta_on_hand_abs: 0,
  }
  nodePage.value = 1
  nodeDialogVisible.value = true
  fetchNodeDetails()
}

function handleNodePageChange(page) {
  nodePage.value = page
  fetchNodeDetails()
}

function handleNodePageSizeChange(size) {
  nodePageSize.value = size
  nodePage.value = 1
  fetchNodeDetails()
}

onMounted(fetchTrends)
</script>

<style scoped>
.flow-record-page {
  display: grid;
  gap: 14px;
}

.flow-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #d8e1eb;
  border-radius: 12px;
  background: #ffffff;
}

.flow-toolbar p {
  margin: 0;
  color: #586178;
}

.flow-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1100px) {
  .flow-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .flow-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
