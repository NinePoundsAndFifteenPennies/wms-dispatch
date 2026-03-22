<template>
  <div class="detail-page" v-loading="loading">
    <header class="detail-head">
      <div>
        <h3>工单详情</h3>
        <p>查看当前工单执行状态、时间节点与备注信息。</p>
      </div>
      <el-button @click="goBack">返回工单列表</el-button>
    </header>

    <el-empty v-if="!detail" description="未找到工单" :image-size="100" />

    <template v-else>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="工单ID">#{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :class="statusTagClass(detail.status)" effect="light" round>
            {{ workOrderStatusText(detail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="阶段">{{ stageText(detail.stage_type) }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
        <el-descriptions-item label="调度员">{{ detail.dispatcher_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ sourceText(detail.source) }}</el-descriptions-item>
        <el-descriptions-item label="截止时间">{{ formatDate(detail.deadline) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatDate(detail.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDate(detail.completed_at) }}</el-descriptions-item>
        <el-descriptions-item label="终止时间">{{ formatDate(detail.terminated_at) }}</el-descriptions-item>
      </el-descriptions>

      <div class="panel" v-if="parsedOverrideInfo.hasOverride">
        <p class="panel-title">风险放行信息</p>
        <p>风险类型：{{ parsedOverrideInfo.riskLabels.join(' / ') || '-' }}</p>
        <p>放行原因：{{ parsedOverrideInfo.overrideReason || '-' }}</p>
      </div>

      <div class="panel" v-if="detail.status === 'terminated'">
        <p class="panel-title">终止信息</p>
        <p>终止原因：{{ detail.termination_reason || '-' }}</p>
      </div>

      <div class="panel" v-if="!parsedOverrideInfo.hasOverride">
        <p class="panel-title">备注内容</p>
        <p>{{ parsedOverrideInfo.remarkText || detail.description || '无备注' }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { workerWorkOrdersApi } from '../../api/worker/workOrders'
import { formatCnDateTime } from '../../utils/cnTime'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const detail = ref(null)

const parsedOverrideInfo = computed(() => {
  const raw = String(detail.value?.description || '').trim()
  if (!raw) {
    return {
      hasOverride: false,
      riskCodes: [],
      riskLabels: [],
      overrideReason: '',
      remarkText: '',
    }
  }

  const matched = raw.match(/^\[override\]\[([^\]]+)\]\s*([^\n]*)(?:\n([\s\S]*))?$/)
  if (!matched) {
    return {
      hasOverride: false,
      riskCodes: [],
      riskLabels: [],
      overrideReason: '',
      remarkText: raw,
    }
  }

  const riskCodeMap = {
    skill_gap: '技能风险',
    worker_overload: '负载风险',
  }
  const riskCodes = (matched[1] || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  return {
    hasOverride: true,
    riskCodes,
    riskLabels: riskCodes.map((item) => riskCodeMap[item] || item),
    overrideReason: (matched[2] || '').trim(),
    remarkText: (matched[3] || '').trim(),
  }
})

function formatDate(value) {
  return formatCnDateTime(value)
}

function stageText(stage) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[stage] || stage
}

function priorityText(priority) {
  return {
    high: '高',
    medium: '中',
    low: '低',
  }[priority] || priority
}

function sourceText(source) {
  return {
    manual: '人工派发',
    agent: '智能派发',
  }[source] || source
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

function statusTagClass(status) {
  return {
    pending: 'tag-pending',
    in_progress: 'tag-progress',
    completed: 'tag-completed',
    terminated: 'tag-terminated',
  }[status]
}

function goBack() {
  router.push({ name: 'worker-work-orders' })
}

async function fetchDetail() {
  loading.value = true
  try {
    const res = await workerWorkOrdersApi.getMyWorkOrderDetail(route.params.workOrderId)
    detail.value = res.data || null
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '获取工单详情失败')
    detail.value = null
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail-page {
  display: grid;
  gap: 14px;
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-head h3 {
  margin: 0;
  font-size: 22px;
}

.detail-head p {
  margin: 6px 0 0;
  color: #64748b;
}

.panel {
  border: 1px solid #d8e1eb;
  border-radius: 12px;
  background: #f8fbfd;
  padding: 12px;
}

.panel-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: #16202a;
}

.panel p {
  margin: 6px 0 0;
  color: #334155;
}

:deep(.el-tag.tag-pending) {
  color: #9a5b18;
  background-color: #fbe9cf;
  border-color: #efca95;
}

:deep(.el-tag.tag-progress) {
  color: #1f5c9a;
  background-color: #e4effc;
  border-color: #b9d4f7;
}

:deep(.el-tag.tag-completed) {
  color: #24633f;
  background-color: #ddf4e6;
  border-color: #b6dfc8;
}

:deep(.el-tag.tag-terminated) {
  color: #97463a;
  background-color: #f8e3de;
  border-color: #efbfb4;
}
</style>