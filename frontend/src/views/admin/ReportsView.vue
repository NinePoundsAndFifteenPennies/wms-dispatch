<template>
  <div class="reports-page">
    <section class="toolbar">
      <div>
        <h3>效率报告中心</h3>
        <p>管理员可基于时间范围与仓库维度生成 AI 分析报告，结果支持富文本展示和历史追溯。</p>
      </div>
      <div class="actions">
        <el-button type="primary" :loading="generating" @click="generateReport">生成报告</el-button>
      </div>
    </section>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <section class="filters">
        <el-date-picker
          v-model="filters.period_start"
          type="date"
          placeholder="开始日期"
          value-format="YYYY-MM-DD"
          style="width: 160px"
        />
        <span class="date-sep">至</span>
        <el-date-picker
          v-model="filters.period_end"
          type="date"
          placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 160px"
        />
        <el-select v-model="filters.warehouse_id" placeholder="全部仓库" clearable style="width: 220px">
          <el-option v-for="item in warehouseOptions" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-switch v-model="filters.include_llm_analysis" inline-prompt active-text="AI" inactive-text="无AI" />
        <el-button @click="loadReports">查询历史</el-button>
      </section>

      <el-table :data="reports" stripe>
        <el-table-column prop="id" label="报告ID" width="100" />
        <el-table-column label="统计周期" min-width="220">
          <template #default="{ row }">{{ row.period_start }} ~ {{ row.period_end }}</template>
        </el-table-column>
        <el-table-column label="仓库" min-width="180">
          <template #default="{ row }">{{ row.warehouse_name || '全部仓库' }}</template>
        </el-table-column>
        <el-table-column prop="generated_by_name" label="生成人" min-width="120" />
        <el-table-column label="生成时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadReports"
          @current-change="loadReports"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" width="1080px" title="报告详情" destroy-on-close>
      <template v-if="detail">
        <div class="summary-grid">
          <el-card shadow="never">
            <p class="metric-label">工单总量</p>
            <p class="metric-value">{{ detail.stats_json?.summary?.total_work_orders || 0 }}</p>
          </el-card>
          <el-card shadow="never">
            <p class="metric-label">完成率</p>
            <p class="metric-value">{{ detail.stats_json?.summary?.completion_rate || 0 }}%</p>
          </el-card>
          <el-card shadow="never">
            <p class="metric-label">超时率</p>
            <p class="metric-value">{{ detail.stats_json?.summary?.timeout_rate || 0 }}%</p>
          </el-card>
          <el-card shadow="never">
            <p class="metric-label">平均耗时</p>
            <p class="metric-value">{{ detail.stats_json?.summary?.avg_completion_hours || 0 }}h</p>
          </el-card>
        </div>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <strong>图表看板</strong>
          </template>
          <ReportChartsPanel :stats="detail.stats_json" />
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <strong>阶段分析</strong>
          </template>
          <el-table :data="detail.stats_json?.by_stage || []" size="small" border>
            <el-table-column prop="stage_type" label="阶段" min-width="120" />
            <el-table-column prop="total" label="工单总量" width="110" />
            <el-table-column prop="completed" label="完成数" width="100" />
            <el-table-column prop="timeout" label="超时数" width="100" />
            <el-table-column prop="avg_completion_hours" label="平均耗时(h)" width="120" />
          </el-table>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <strong>调度员分析</strong>
          </template>
          <el-table :data="detail.stats_json?.by_dispatcher || []" size="small" border>
            <el-table-column prop="dispatcher_name" label="调度员" min-width="140" />
            <el-table-column prop="total" label="工单总量" width="110" />
            <el-table-column prop="completed" label="完成数" width="100" />
            <el-table-column prop="avg_completion_hours" label="平均耗时(h)" width="120" />
          </el-table>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <strong>AI 富文本报告</strong>
          </template>
          <article class="markdown-body" v-html="renderedMarkdown" />
        </el-card>

        <el-collapse class="detail-card" v-if="detail.llm_workflow_trace?.length">
          <el-collapse-item title="模型调用工作流">
            <el-table :data="detail.llm_workflow_trace" size="small" border>
              <el-table-column prop="timestamp" label="时间" min-width="220" />
              <el-table-column prop="model" label="模型" min-width="170" />
              <el-table-column prop="status" label="状态" width="120" />
              <el-table-column prop="detail" label="说明" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-collapse-item>
        </el-collapse>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminReportsApi } from '../../api/admin/reports'
import { warehousesApi } from '../../api/admin/warehouses'
import ReportChartsPanel from '../../components/admin/reports/ReportChartsPanel.vue'

const loading = ref(false)
const generating = ref(false)
const detailVisible = ref(false)
const reports = ref([])
const detail = ref(null)
const warehouseOptions = ref([])

const filters = reactive({
  period_start: '',
  period_end: '',
  warehouse_id: undefined,
  include_llm_analysis: true,
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
})

const renderedMarkdown = computed(() => {
  const markdown = detail.value?.content || ''
  const html = marked.parse(markdown)
  return DOMPurify.sanitize(typeof html === 'string' ? html : '')
})

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadWarehouseOptions() {
  try {
    const res = await warehousesApi.getWarehouseOptions()
    warehouseOptions.value = res.data || []
  } catch {
    warehouseOptions.value = []
  }
}

async function loadReports() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      period_start: filters.period_start || undefined,
      period_end: filters.period_end || undefined,
      warehouse_id: filters.warehouse_id || undefined,
    }
    const res = await adminReportsApi.listReports(params)
    reports.value = res.data?.items || []
    pagination.total = Number(res.data?.total || 0)
  } catch {
    ElMessage.error('历史报告加载失败')
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  if (!filters.period_start || !filters.period_end) {
    ElMessage.warning('请先选择开始和结束日期')
    return
  }
  generating.value = true
  try {
    const payload = {
      period_start: filters.period_start,
      period_end: filters.period_end,
      warehouse_id: filters.warehouse_id || null,
      include_llm_analysis: filters.include_llm_analysis,
    }
    const res = await adminReportsApi.generateReport(payload)
    detail.value = res.data
    detailVisible.value = true
    ElMessage.success('报告生成完成')
    await loadReports()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '报告生成失败')
  } finally {
    generating.value = false
  }
}

async function openDetail(reportId) {
  try {
    const res = await adminReportsApi.getReportDetail(reportId)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    ElMessage.error('报告详情加载失败')
  }
}

onMounted(async () => {
  const now = new Date()
  const start = new Date(now)
  start.setDate(now.getDate() - 7)
  filters.period_start = start.toISOString().slice(0, 10)
  filters.period_end = now.toISOString().slice(0, 10)

  await Promise.all([loadWarehouseOptions(), loadReports()])
})
</script>

<style scoped>
.reports-page {
  display: grid;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.toolbar h3 {
  margin: 0;
}

.toolbar p {
  margin: 6px 0 0;
  color: #666;
}

.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.date-sep {
  color: #666;
}

.pagination-container {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-label {
  margin: 0;
  color: #666;
  font-size: 13px;
}

.metric-value {
  margin: 6px 0 0;
  font-size: 24px;
  font-weight: 700;
  color: #1f6f64;
}

.detail-card {
  margin-top: 12px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 10px 0;
}

.markdown-body :deep(p),
.markdown-body :deep(li) {
  line-height: 1.65;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 6px 8px;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .toolbar {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
