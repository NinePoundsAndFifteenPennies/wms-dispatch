<template>
  <div class="detail-page" v-loading="loading">
    <header class="detail-head">
      <div>
        <h3>工单详情</h3>
        <p>查看当前工单执行状态、订单产品技能要求与备注信息。</p>
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

      <div class="panel" v-if="orderItems.length">
        <div class="panel-title-row">
          <p class="panel-title">订单产品</p>
          <el-tag :type="skillMismatchCount > 0 ? 'warning' : 'success'" effect="light" round>
            {{ skillMismatchCount > 0 ? `有${skillMismatchCount}个产品技能不匹配` : '当前阶段全部匹配' }}
          </el-tag>
        </div>
        <p class="panel-tip">
          当前阶段：{{ stageText(detail.stage_type) }}，你的阶段技能等级：Lv{{ detail.worker_stage_skill ?? 0 }}，本单阶段要求范围：Lv{{
            detail.stage_required_skill_min ?? 0
          }} - Lv{{ detail.stage_required_skill_max ?? 0 }}
        </p>

        <div class="product-list">
          <article
            v-for="item in orderItems"
            :key="`${item.product_id}-${item.current_stage_required_skill}-${item.qty}`"
            class="product-card"
            :class="{ 'product-card-mismatch': !item.is_skill_matched }"
          >
            <div class="product-cover-wrap">
              <el-image
                v-if="item.product_cover_image"
                :src="item.product_cover_image"
                fit="cover"
                class="product-cover"
                :preview-src-list="[item.product_cover_image]"
                preview-teleported
              />
              <div v-else class="product-cover-placeholder">无图</div>
            </div>

            <div class="product-main">
              <p class="product-name">{{ item.product_name }}</p>
              <p class="product-meta">数量：{{ item.qty }}</p>
              <p class="product-meta">
                阶段要求：拣{{ item.req_skill_picking }} / 备{{ item.req_skill_staging }} / 发{{ item.req_skill_shipping }}
              </p>
              <div class="product-tags">
                <el-tag size="small" effect="light" type="info">当前阶段需 Lv{{ item.current_stage_required_skill }}</el-tag>
                <el-tag size="small" effect="light" :type="item.is_skill_matched ? 'success' : 'danger'">
                  {{ item.is_skill_matched ? '技能匹配' : '技能不匹配' }}
                </el-tag>
              </div>
            </div>
          </article>
        </div>
      </div>

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

const orderItems = computed(() => {
  return detail.value?.order_items || []
})

const skillMismatchCount = computed(() => {
  return orderItems.value.filter((item) => !item.is_skill_matched).length
})

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

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.panel-tip {
  margin: 0;
  color: #3a5166;
  font-size: 13px;
}

.product-list {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.product-card {
  display: flex;
  align-items: stretch;
  gap: 10px;
  border: 1px solid #d5e2ef;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
}

.product-card-mismatch {
  border-color: #f1bab3;
  background: #fff7f5;
}

.product-cover-wrap {
  flex: 0 0 72px;
  width: 72px;
  height: 72px;
}

.product-cover {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  display: block;
}

.product-cover-placeholder {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  border: 1px dashed #c4d2e2;
  color: #7d8ea3;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f8fc;
}

.product-main {
  min-width: 0;
  flex: 1;
}

.product-name {
  margin: 0;
  font-weight: 700;
  color: #1f2c3c;
}

.product-meta {
  margin: 4px 0 0;
  font-size: 13px;
  color: #43586d;
}

.product-tags {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.panel p {
  margin: 6px 0 0;
  color: #334155;
}

@media (max-width: 920px) {
  .product-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .panel-title-row {
    align-items: flex-start;
    flex-direction: column;
  }
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