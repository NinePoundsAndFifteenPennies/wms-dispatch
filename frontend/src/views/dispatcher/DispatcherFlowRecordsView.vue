<template>
  <div class="dispatcher-flow-page">
    <section class="page-header">
      <div>
        <h3>本仓流水记录</h3>
        <p>点击折线节点查看当日明细，点击放大可聚焦分析波峰波谷。</p>
      </div>
      <el-select v-model="days" style="width: 160px" @change="fetchTrend">
        <el-option :value="7" label="近 7 天" />
        <el-option :value="14" label="近 14 天" />
        <el-option :value="30" label="近 30 天" />
      </el-select>
    </section>

    <InventoryFlowLineChart
      v-if="trend"
      :title="trend.warehouse_name || '仓库流水'"
      subtitle="纵轴为流水笔数，节点可点击查看明细"
      :points="trend.points || []"
      :loading="loading"
      @point-click="openNodeDetails"
    />

    <el-empty v-else-if="!loading" description="暂无流水数据" />

    <InventoryFlowNodeDetailDialog
      v-model="nodeDialogVisible"
      title="流水节点详情"
      :warehouse-name="trend?.warehouse_name || ''"
      :date="activeDate"
      :movement-count="nodeSummary.movement_count"
      :total-abs-delta="nodeSummary.total_abs_delta"
      :positive-delta-on-hand="nodeSummary.positive_delta_on_hand"
      :negative-delta-on-hand-abs="nodeSummary.negative_delta_on_hand_abs"
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
import { dispatcherInventoryApi } from '../../api/dispatcher/inventory'
import InventoryFlowLineChart from '../../components/shared/InventoryFlowLineChart.vue'
import InventoryFlowNodeDetailDialog from '../../components/shared/InventoryFlowNodeDetailDialog.vue'

const loading = ref(false)
const days = ref(14)
const trend = ref(null)

const nodeDialogVisible = ref(false)
const nodeLoading = ref(false)
const nodeRows = ref([])
const nodeTotal = ref(0)
const nodePage = ref(1)
const nodePageSize = ref(20)
const activeDate = ref('')
const nodeSummary = ref({
  movement_count: 0,
  total_abs_delta: 0,
  positive_delta_on_hand: 0,
  negative_delta_on_hand_abs: 0,
})

async function fetchTrend() {
  loading.value = true
  try {
    const res = await dispatcherInventoryApi.getFlowTrend({ days: days.value })
    trend.value = res.data || null
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载仓库流水趋势失败')
  } finally {
    loading.value = false
  }
}

async function fetchNodeDetails() {
  if (!activeDate.value) return

  nodeLoading.value = true
  try {
    const res = await dispatcherInventoryApi.getFlowNodeDetails({
      date: activeDate.value,
      page: nodePage.value,
      page_size: nodePageSize.value,
    })
    const data = res.data || {}
    nodeSummary.value = {
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

function openNodeDetails(point) {
  activeDate.value = point.date
  nodeSummary.value = {
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

onMounted(fetchTrend)
</script>

<style scoped>
.dispatcher-flow-page {
  display: grid;
  gap: 14px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 12px;
  background: var(--dispatcher-surface);
}

.page-header h3 {
  margin: 0;
  font-size: 18px;
}

.page-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--dispatcher-muted);
}

@media (max-width: 720px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
