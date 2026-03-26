<template>
  <div class="detail-page" v-loading="loading">
    <section class="page-head">
      <el-button @click="goBack">返回我的订单</el-button>
      <el-button
        v-if="detail?.status === 'in_progress'"
        type="danger"
        plain
        :disabled="cancelSubmitting"
        @click="openCancelDialog"
      >
        取消订单
      </el-button>
    </section>

    <el-descriptions v-if="detail" :column="3" border>
      <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
      <el-descriptions-item label="客户">{{ detail.customer_name }}</el-descriptions-item>
      <el-descriptions-item label="客户联系方式">{{ detail.customer_contact || '-' }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
      <el-descriptions-item label="优先级">{{ priorityText(detail.priority) }}</el-descriptions-item>
      <el-descriptions-item label="总件数">{{ detail.total_items }}</el-descriptions-item>
      <el-descriptions-item label="总金额(元)">{{ detail.total_amount }}</el-descriptions-item>
      <el-descriptions-item label="订单备注" :span="3">{{ detail.description || '-' }}</el-descriptions-item>
    </el-descriptions>

    <DetailInfoBlock title="订单明细" v-if="detail">
      <el-table :data="detail.items || []" stripe>
        <el-table-column prop="product_sku" label="SKU" width="130" />
        <el-table-column prop="product_name" label="产品名称" min-width="200" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column label="技能要求" min-width="260">
          <template #default="{ row }">
            拣{{ row.req_skill_picking }} / 备{{ row.req_skill_staging }} / 发{{ row.req_skill_shipping }}
          </template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价(元)" width="110" />
      </el-table>
    </DetailInfoBlock>

    <DetailInfoBlock title="阶段进度" v-if="detail">
      <el-table :data="detail.stages || []" stripe>
        <el-table-column label="阶段" min-width="120">
          <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">{{ stageStatusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="工单概况" min-width="240">
          <template #default="{ row }">
            总{{ row.work_orders.total }} / 待{{ row.work_orders.pending }} / 进{{ row.work_orders.in_progress }} / 完{{
              row.work_orders.completed
            }}
          </template>
        </el-table-column>
        <el-table-column label="完成方式" min-width="100">
          <template #default="{ row }">{{ completionTypeText(row.completion_type) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              plain
              :disabled="row.status === 'completed' || stageCompleteSubmitting"
              @click="openManualComplete(row)"
            >
              手动标记完成
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </DetailInfoBlock>

    <DetailInfoBlock title="Agent 派单助手" v-if="detail?.status === 'in_progress'">
      <div class="agent-assistant">
        <div class="agent-head">
          <span class="agent-robot">🤖</span>
          <div>
            <p class="agent-title">智能派单建议</p>
            <p class="agent-subtitle">仅支持“进行中且尚未创建任何工单”的订单。</p>
          </div>
        </div>

        <el-alert
          v-if="!canUseAgentAssistant"
          type="warning"
          :closable="false"
          :title="agentDisabledReason"
          show-icon
        />

        <template v-else>
          <el-form label-width="100px" class="agent-form">
            <el-form-item label="调度意图">
              <el-input
                v-model="agentIntent"
                type="textarea"
                :rows="2"
                maxlength="500"
                show-word-limit
                placeholder="例如：优先时效，先安排熟悉发货复核的工人"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="agentSuggesting" @click="handleAgentSuggest">生成建议</el-button>
            </el-form-item>
          </el-form>

          <div v-if="agentSuggestion" class="agent-result">
            <p class="summary-text">
              本次建议共 {{ agentSuggestionStages.length }} 个阶段，可分配 {{ agentAssignableStages.length }} 个阶段。
            </p>

            <div class="agent-stage-list" v-if="agentSuggestionStages.length">
              <div class="agent-stage-card" v-for="stage in agentSuggestionStages" :key="stage.stage_id">
                <div class="agent-stage-head">
                  <p class="agent-stage-title">{{ stageText(stage.stage_type) }}阶段</p>
                  <el-tag :type="stage.assignable ? 'success' : 'warning'" size="small">
                    {{ stage.assignable ? '可分配' : '不可分配' }}
                  </el-tag>
                </div>

                <template v-if="stage.assignable">
                  <p class="summary-text">
                    工人 {{ stage.worker?.worker_name || '-' }}（ID: {{ stage.worker?.worker_id || '-' }}），技能 {{ stage.worker?.worker_skill || '-' }}，
                    阶段要求 {{ stage.required_skill_min }} - {{ stage.required_skill_max }}，建议优先级 {{ priorityText(stage.priority) }}。
                  </p>

                  <ul class="risk-list" v-if="stage.risks?.length">
                    <li v-for="risk in stage.risks" :key="`${stage.stage_id}-${risk.code}`">{{ formatRiskMessage(risk) }}</li>
                  </ul>

                  <el-form label-width="100px" class="agent-form">
                    <el-form-item label="建议描述">
                      <el-input
                        :model-value="stage.suggested_description || '无建议描述'"
                        type="textarea"
                        :rows="4"
                        readonly
                      />
                    </el-form-item>
                    <el-form-item label="阶段截止">
                      <el-date-picker
                        v-model="agentStageDeadlines[stage.stage_id]"
                        type="datetime"
                        value-format="YYYY-MM-DDTHH:mm:ss"
                        placeholder="可选，建议设置阶段截止时间"
                        style="width: 100%"
                      />
                    </el-form-item>
                    <el-form-item label="覆盖备注" v-if="stage.has_risk">
                      <el-input
                        v-model="agentStageOverrides[stage.stage_id]"
                        type="textarea"
                        :rows="2"
                        maxlength="500"
                        show-word-limit
                          placeholder="可选：补充你的管理备注（Agent 将自动处理风险覆盖）"
                      />
                    </el-form-item>
                  </el-form>
                </template>

                <template v-else>
                  <p class="summary-text">原因：{{ stage.reason || '无可用工人' }}</p>
                </template>
              </div>
            </div>

            <el-form label-width="100px" class="agent-form">
              <el-form-item>
                <el-button type="success" :loading="agentConfirming" @click="handleAgentConfirm">确认并创建工单</el-button>
                <el-button plain :disabled="!agentWorkflowTrace.length" @click="agentWorkflowVisible = true">
                  查看模型工作流
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </template>
      </div>
    </DetailInfoBlock>

    <DetailInfoBlock title="创建工单" v-if="detail">
      <el-form :model="createForm" label-width="100px" class="create-form">
        <el-form-item label="阶段">
          <el-select v-model="createForm.stage_id" placeholder="选择阶段" class="w-full" @change="handleAssignmentSelectionChange">
            <el-option
              v-for="stage in detail.stages || []"
              :key="stage.id"
              :label="`${stageText(stage.stage_type)}（${stageStatusText(stage.status)}）`"
              :value="stage.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工人">
          <el-select
            v-model="createForm.worker_id"
            filterable
            placeholder="选择工人"
            class="w-full"
            @change="handleAssignmentSelectionChange"
            :no-data-text="workerSelectNoDataText"
          >
            <el-option
              v-for="worker in filteredWorkers"
              :key="worker.id"
              :label="`${worker.username}（拣${worker.skill_picking}/备${worker.skill_staging}/发${worker.skill_shipping}｜在途${worker.active_work_order_count}/${worker.active_work_order_limit || 5}）`"
              :value="worker.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="派单风险" v-if="selectedStageDetail || selectedWorker">
          <div class="risk-hint-box">
            <p>
              当前阶段：{{ selectedStageDetail ? stageText(selectedStageDetail.stage_type) : '-' }}，阶段技能范围：
              {{ selectedStageRequiredSkillRange }}
            </p>
            <p>
              当前工人阶段技能：{{ selectedWorkerSkill }}，在途工单：{{ selectedWorkerLoad }}/{{ selectedWorkerLoadLimit }}
            </p>
          </div>
        </el-form-item>
        <el-form-item v-if="assignmentPrecheck?.has_risk">
          <p class="risk-inline-tip">检测到派单风险，点击“创建工单”将直接进入风险确认弹窗。</p>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" class="w-full">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker
            v-model="createForm.deadline"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="可选，留空表示不限时"
            class="w-full"
          />
        </el-form-item>
        <el-form-item label="任务备注" v-if="!assignmentPrecheck?.has_risk">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="选填，说明执行要求" />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="creatingWorkOrder"
            :disabled="filteredWorkers.length === 0"
            @click="submitCreateWorkOrder"
          >
            创建工单
          </el-button>
          <el-button @click="resetCreateForm">重置</el-button>
        </el-form-item>
      </el-form>
    </DetailInfoBlock>

    <DetailInfoBlock title="工单列表" v-if="detail">
      <el-table :data="workOrders" stripe>
        <el-table-column prop="id" label="工单ID" width="90" />
        <el-table-column label="阶段" min-width="100">
          <template #default="{ row }">{{ stageText(row.stage_type) }}</template>
        </el-table-column>
        <el-table-column prop="worker_name" label="工人" min-width="120" />
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">{{ workOrderStatusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="优先级" min-width="100">
          <template #default="{ row }">{{ priorityText(row.priority) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!['pending', 'in_progress'].includes(row.status) || terminateSubmitting"
              @click="openTerminate(row)"
            >
              终止
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </DetailInfoBlock>

    <el-dialog v-model="terminateDialogVisible" title="终止工单" width="500px">
      <el-input v-model="terminateReason" type="textarea" :rows="3" placeholder="请输入终止原因" />
      <template #footer>
        <el-button @click="terminateDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="terminateSubmitting" @click="submitTerminate">确认终止</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manualCompleteVisible" title="手动标记阶段完成" width="520px">
      <p class="summary-text" v-if="selectedStage">
        阶段：{{ stageText(selectedStage.stage_type) }}，当前状态：{{ stageStatusText(selectedStage.status) }}
      </p>
      <el-input v-model="manualCompleteRemark" type="textarea" :rows="3" placeholder="请输入手动完成原因" />
      <template #footer>
        <el-button @click="manualCompleteVisible = false">取消</el-button>
        <el-button type="primary" :loading="stageCompleteSubmitting" @click="submitManualComplete">确认完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消订单" width="520px">
      <p class="summary-text">取消前请确保所有未完成工单已终止。</p>
      <el-input
        v-model="cancelReason"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="请输入取消原因（必填）"
      />
      <template #footer>
        <el-button @click="cancelDialogVisible = false">返回</el-button>
        <el-button type="danger" :loading="cancelSubmitting" @click="submitCancelOrder">确认取消</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignmentRiskDialogVisible" title="派单风险确认" width="560px">
      <p class="summary-text" v-if="assignmentPrecheck">
        阶段：{{ stageText(assignmentPrecheck.stage_type) }}，工人阶段技能：{{ assignmentPrecheck.worker_skill }}，阶段技能范围：
        {{ assignmentPrecheck.required_skill_min }} - {{ assignmentPrecheck.required_skill_max }}
      </p>
      <ul class="risk-list" v-if="assignmentPrecheck?.risks?.length">
        <li v-for="risk in assignmentPrecheck.risks" :key="risk.code">{{ formatRiskMessage(risk) }}</li>
      </ul>
      <div v-if="assignmentPrecheck?.skill_products?.length && hasSkillGapRisk" class="skill-products-box">
        <p class="summary-text">技能匹配明细（便于备注说明）</p>
        <el-table :data="assignmentPrecheck.skill_products" size="small" border>
          <el-table-column prop="product_sku" label="SKU" min-width="120" />
          <el-table-column prop="product_name" label="产品" min-width="160" />
          <el-table-column prop="required_skill" label="需求技能" width="90" />
          <el-table-column prop="worker_skill" label="工人技能" width="90" />
          <el-table-column label="结果" width="90">
            <template #default="{ row }">
              <span :class="row.is_qualified ? 'skill-ok' : 'skill-bad'">{{ row.is_qualified ? '够' : '不够' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-input
        v-model="overrideReason"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="存在风险时必须填写强制派单原因"
      />
      <template #footer>
        <el-button @click="assignmentRiskDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="creatingWorkOrder" @click="submitCreateWorkOrderWithOverride">确认强制派单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="agentWorkflowVisible" title="模型调用工作流" width="760px">
      <el-table :data="agentWorkflowTrace" size="small" border max-height="420">
        <el-table-column prop="timestamp" label="时间" min-width="200" />
        <el-table-column label="阶段" width="120">
          <template #default="{ row }">{{ row.stage_type ? stageText(row.stage_type) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="model" label="模型" min-width="180" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="workflowStatusTagType(row.status)">{{ workflowStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="说明" min-width="220" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="agentWorkflowVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import DetailInfoBlock from '../../components/shared/DetailInfoBlock.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detail = ref(null)
const workOrders = ref([])
const workers = ref([])
const creatingWorkOrder = ref(false)
const terminateDialogVisible = ref(false)
const terminateSubmitting = ref(false)
const stageCompleteSubmitting = ref(false)
const manualCompleteVisible = ref(false)
const cancelDialogVisible = ref(false)
const cancelSubmitting = ref(false)
const assignmentRiskDialogVisible = ref(false)
const selectedStage = ref(null)
const selectedWorkOrderId = ref(null)
const terminateReason = ref('')
const manualCompleteRemark = ref('')
const cancelReason = ref('')
const assignmentPrecheck = ref(null)
const overrideReason = ref('')
const agentSuggesting = ref(false)
const agentConfirming = ref(false)
const agentIntent = ref('')
const agentSuggestion = ref(null)
const agentStageOverrides = ref({})
const agentStageDeadlines = ref({})
const agentWorkflowVisible = ref(false)

const createForm = ref({
  stage_id: null,
  worker_id: null,
  priority: 'medium',
  deadline: null,
  description: '',
})

const selectedStageDetail = computed(() => {
  return (detail.value?.stages || []).find((item) => item.id === createForm.value.stage_id) || null
})

const selectedStageSkillBounds = computed(() => {
  if (!selectedStageDetail.value || !Array.isArray(detail.value?.items)) {
    return { min: 0, max: 0 }
  }
  const keyMap = {
    picking: 'req_skill_picking',
    staging: 'req_skill_staging',
    shipping: 'req_skill_shipping',
  }
  const key = keyMap[selectedStageDetail.value.stage_type]
  const levels = (detail.value.items || []).map((item) => Number(item[key] || 0))
  if (!levels.length) {
    return { min: 0, max: 0 }
  }
  return { min: Math.min(...levels), max: Math.max(...levels) }
})

const filteredWorkers = computed(() => {
  if (!selectedStageDetail.value) {
    return workers.value || []
  }
  const keyMap = {
    picking: 'skill_picking',
    staging: 'skill_staging',
    shipping: 'skill_shipping',
  }
  const skillKey = keyMap[selectedStageDetail.value.stage_type]
  const minRequired = selectedStageSkillBounds.value.min
  return (workers.value || []).filter((worker) => Number(worker[skillKey] || 0) >= minRequired)
})

const selectedWorker = computed(() => {
  return (workers.value || []).find((item) => item.id === createForm.value.worker_id) || null
})

const selectedStageRequiredSkillRange = computed(() => {
  const min = selectedStageSkillBounds.value.min
  const max = selectedStageSkillBounds.value.max
  return min === max ? `${min}` : `${min} - ${max}`
})

const selectedWorkerSkill = computed(() => {
  if (!selectedStageDetail.value || !selectedWorker.value) return '-'
  const keyMap = {
    picking: 'skill_picking',
    staging: 'skill_staging',
    shipping: 'skill_shipping',
  }
  return selectedWorker.value[keyMap[selectedStageDetail.value.stage_type]]
})

const selectedWorkerLoad = computed(() => selectedWorker.value?.active_work_order_count ?? '-')
const selectedWorkerLoadLimit = computed(() => {
  if (assignmentPrecheck.value?.active_work_order_limit) return assignmentPrecheck.value.active_work_order_limit
  return selectedWorker.value?.active_work_order_limit ?? 5
})

const hasSkillGapRisk = computed(() => {
  return (assignmentPrecheck.value?.risks || []).some((item) => item.code === 'skill_gap')
})

const canUseAgentAssistant = computed(() => {
  if (!detail.value || detail.value.status !== 'in_progress') return false
  return workOrders.value.length === 0
})

const agentSuggestionStages = computed(() => {
  return Array.isArray(agentSuggestion.value?.stages) ? agentSuggestion.value.stages : []
})

const agentAssignableStages = computed(() => {
  return agentSuggestionStages.value.filter((stage) => stage.assignable)
})

const agentWorkflowTrace = computed(() => {
  return Array.isArray(agentSuggestion.value?.llm_workflow_trace) ? agentSuggestion.value.llm_workflow_trace : []
})

const agentDisabledReason = computed(() => {
  if (!detail.value || detail.value.status !== 'in_progress') {
    return '仅进行中订单可使用 Agent 派单助手'
  }
  if (workOrders.value.length > 0) {
    return '该订单已存在工单，Agent 助手已禁用，请继续在下方手动管理工单'
  }
  return ''
})

const workerSelectNoDataText = computed(() => {
  if (!selectedStageDetail.value) {
    return '请先选择阶段'
  }
  return '当前阶段暂无满足最低技能要求的可派工人'
})

function formatRiskMessage(risk) {
  const fallback = risk?.message || '存在派单风险'
  if (!risk?.code) return fallback

  const map = {
    skill_gap: '技能不足：当前工人技能未达到该阶段需求，建议更换工人或填写强制派单原因。',
    worker_overload: '负载超限：当前工人在途工单已达上限，建议分配给其他工人或填写强制派单原因。',
  }
  return map[risk.code] || fallback
}

function workflowStatusText(status) {
  return {
    attempt: '尝试',
    success: '成功',
    failed: '失败',
    provider_unavailable: '未配置',
    no_model_candidates: '无模型',
  }[status] || status
}

function workflowStatusTagType(status) {
  return {
    attempt: 'info',
    success: 'success',
    failed: 'danger',
    provider_unavailable: 'warning',
    no_model_candidates: 'warning',
  }[status] || 'info'
}

function ensureValidWorkerSelection() {
  if (!createForm.value.stage_id) {
    createForm.value.worker_id = null
    return
  }
  const allowedIds = new Set(filteredWorkers.value.map((item) => item.id))
  if (!allowedIds.has(createForm.value.worker_id)) {
    createForm.value.worker_id = filteredWorkers.value[0]?.id || null
  }
}

async function fetchDetail() {
  loading.value = true
  try {
    const [detailRes, workersRes, workOrdersRes] = await Promise.all([
      dispatcherOrdersApi.getMyOrderDetail(route.params.orderId),
      dispatcherOrdersApi.getWorkers(),
      dispatcherOrdersApi.getOrderWorkOrders(route.params.orderId),
    ])

    detail.value = detailRes.data
    workers.value = workersRes.data || []
    workOrders.value = workOrdersRes.data?.items || []

    const firstStage = (detail.value?.stages || []).find((item) => item.status !== 'completed')
    if (!createForm.value.stage_id && firstStage) {
      createForm.value.stage_id = firstStage.id
    }
    ensureValidWorkerSelection()
    await handleAssignmentSelectionChange()
    if (!canUseAgentAssistant.value) {
      agentSuggestion.value = null
      agentStageOverrides.value = {}
      agentStageDeadlines.value = {}
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '获取订单详情失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function resolveApiErrorMessage(error, fallbackText) {
  const detailPayload = error?.response?.data?.detail
  if (typeof detailPayload === 'string') return detailPayload
  if (detailPayload?.message) return detailPayload.message
  return error?.response?.data?.message || fallbackText
}

async function handleAgentSuggest() {
  if (!canUseAgentAssistant.value) {
    ElMessage.warning(agentDisabledReason.value || '当前订单不可使用 Agent')
    return
  }
  agentSuggesting.value = true
  try {
    const payload = {}
    if (agentIntent.value.trim()) payload.intent = agentIntent.value.trim()
    const res = await dispatcherOrdersApi.suggestWorkOrderByAgent(route.params.orderId, payload)
    agentSuggestion.value = res.data
    agentWorkflowVisible.value = false
    const overrides = {}
    const deadlines = {}
    for (const stage of Array.isArray(res.data?.stages) ? res.data.stages : []) {
      if (stage.assignable && stage.has_risk) {
        overrides[stage.stage_id] = ''
      }
      if (stage.assignable) {
        deadlines[stage.stage_id] = null
      }
    }
    agentStageOverrides.value = overrides
    agentStageDeadlines.value = deadlines
    ElMessage.success('Agent 建议已生成')
  } catch (error) {
    ElMessage.error(resolveApiErrorMessage(error, '生成 Agent 建议失败'))
  } finally {
    agentSuggesting.value = false
  }
}

async function handleAgentConfirm() {
  if (!agentSuggestion.value || !agentSuggestionStages.value.length) {
    ElMessage.warning('请先生成 Agent 建议')
    return
  }
  if (!agentAssignableStages.value.length) {
    ElMessage.warning('当前建议中没有可创建工单的阶段')
    return
  }

  agentConfirming.value = true
  try {
    const stage_overrides = agentAssignableStages.value
      .map((stage) => {
        const overrideReason = (agentStageOverrides.value?.[stage.stage_id] || '').trim()
        const deadline = agentStageDeadlines.value?.[stage.stage_id] || null
        const suggestedDescription = (stage.suggested_description || '').trim()
        if (!overrideReason && !deadline && !suggestedDescription) return null
        return {
          stage_id: stage.stage_id,
          override_reason: overrideReason || null,
          deadline,
          suggested_description: suggestedDescription || null,
        }
      })
      .filter(Boolean)

    const payload = {
      stage_overrides,
    }
    if (agentIntent.value.trim()) {
      payload.intent = agentIntent.value.trim()
    }

    const res = await dispatcherOrdersApi.confirmWorkOrderByAgent(route.params.orderId, payload)
    const createdCount = res.data?.created_work_orders?.length || 0
    const unassignableCount = (res.data?.stages || []).filter((stage) => stage.status === 'unassignable').length
    ElMessage.success(`Agent 已创建 ${createdCount} 张工单${unassignableCount ? `，${unassignableCount} 个阶段不可分配` : ''}`)
    agentSuggestion.value = null
    agentStageOverrides.value = {}
    agentStageDeadlines.value = {}
    await fetchDetail()
  } catch (error) {
    ElMessage.error(resolveApiErrorMessage(error, 'Agent 确认派单失败'))
  } finally {
    agentConfirming.value = false
  }
}

function goBack() {
  router.push({ name: 'dispatcher-my-orders' })
}

function statusText(status) {
  return {
    pending_acceptance: '待接单',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }[status] || status
}

function priorityText(priority) {
  return {
    high: '高',
    medium: '中',
    low: '低',
  }[priority] || priority
}

function stageText(stage) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[stage] || stage
}

function stageStatusText(status) {
  return {
    not_started: '未开始',
    in_progress: '进行中',
    completed: '已完成',
  }[status] || status
}

function completionTypeText(type) {
  return {
    auto: '自动',
    manual: '手动',
  }[type] || '-'
}

function workOrderStatusText(status) {
  return {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[status] || status
}

function resetCreateForm() {
  createForm.value = {
    stage_id: detail.value?.stages?.find((item) => item.status !== 'completed')?.id || null,
    worker_id: null,
    priority: 'medium',
    deadline: null,
    description: '',
  }
  ensureValidWorkerSelection()
  assignmentPrecheck.value = null
  overrideReason.value = ''
  handleAssignmentSelectionChange()
}

async function submitCreateWorkOrder() {
  if (!createForm.value.stage_id || !createForm.value.worker_id) {
    ElMessage.warning('请选择阶段和工人')
    return
  }

  try {
    const precheckRes = await dispatcherOrdersApi.precheckWorkOrder(route.params.orderId, {
      stage_id: createForm.value.stage_id,
      worker_id: createForm.value.worker_id,
    })
    assignmentPrecheck.value = precheckRes.data
    if (assignmentPrecheck.value?.has_risk) {
      overrideReason.value = ''
      assignmentRiskDialogVisible.value = true
      return
    }
  } catch (error) {
    const detailMessage = error?.response?.data?.detail
    const message =
      error?.response?.data?.message ||
      (typeof detailMessage === 'string' ? detailMessage : detailMessage?.message) ||
      '派单预校验失败'
    ElMessage.error(message)
    return
  }

  await performCreateWorkOrder()
}

async function handleAssignmentSelectionChange() {
  ensureValidWorkerSelection()
  if (!createForm.value.stage_id || !createForm.value.worker_id) {
    assignmentPrecheck.value = null
    return
  }

  try {
    const precheckRes = await dispatcherOrdersApi.precheckWorkOrder(route.params.orderId, {
      stage_id: createForm.value.stage_id,
      worker_id: createForm.value.worker_id,
    })
    assignmentPrecheck.value = precheckRes.data
    if (assignmentPrecheck.value?.has_risk) {
      createForm.value.description = ''
    }
  } catch {
    assignmentPrecheck.value = null
  }
}

async function submitCreateWorkOrderWithOverride() {
  if (!overrideReason.value.trim()) {
    ElMessage.warning('存在风险时必须填写强制派单原因')
    return
  }
  await performCreateWorkOrder(overrideReason.value.trim())
}

async function performCreateWorkOrder(forceReason = null) {
  creatingWorkOrder.value = true
  try {
    await dispatcherOrdersApi.createWorkOrder(route.params.orderId, {
      stage_id: createForm.value.stage_id,
      worker_id: createForm.value.worker_id,
      priority: createForm.value.priority,
      deadline: createForm.value.deadline || null,
      description: createForm.value.description || null,
      override_reason: forceReason,
    })
    assignmentRiskDialogVisible.value = false
    ElMessage.success('工单创建成功')
    resetCreateForm()
    await fetchDetail()
  } catch (error) {
    const detailMessage = error?.response?.data?.detail
    const message =
      error?.response?.data?.message ||
      (typeof detailMessage === 'string' ? detailMessage : detailMessage?.message) ||
      '工单创建失败'
    ElMessage.error(message)
  } finally {
    creatingWorkOrder.value = false
  }
}

function openTerminate(row) {
  selectedWorkOrderId.value = row.id
  terminateReason.value = ''
  terminateDialogVisible.value = true
}

async function submitTerminate() {
  if (!selectedWorkOrderId.value) return
  if (!terminateReason.value.trim()) {
    ElMessage.warning('请输入终止原因')
    return
  }

  terminateSubmitting.value = true
  try {
    await dispatcherOrdersApi.terminateWorkOrder(selectedWorkOrderId.value, {
      reason: terminateReason.value.trim(),
    })
    terminateDialogVisible.value = false
    ElMessage.success('工单已终止')
    await fetchDetail()
  } finally {
    terminateSubmitting.value = false
  }
}

function openManualComplete(stage) {
  selectedStage.value = stage
  manualCompleteRemark.value = ''
  manualCompleteVisible.value = true
}

async function submitManualComplete() {
  if (!selectedStage.value) return
  if (!manualCompleteRemark.value.trim()) {
    ElMessage.warning('请输入手动完成原因')
    return
  }

  stageCompleteSubmitting.value = true
  try {
    await dispatcherOrdersApi.manualCompleteStage(route.params.orderId, selectedStage.value.id, {
      remark: manualCompleteRemark.value.trim(),
    })
    manualCompleteVisible.value = false
    ElMessage.success('阶段已手动标记为完成')
    await fetchDetail()
  } finally {
    stageCompleteSubmitting.value = false
  }
}

function hasOpenWorkOrders() {
  return workOrders.value.some((item) => ['pending', 'in_progress'].includes(item.status))
}

function openCancelDialog() {
  if (!detail.value || detail.value.status !== 'in_progress') {
    ElMessage.warning('仅进行中的订单可取消')
    return
  }
  if (hasOpenWorkOrders()) {
    ElMessage.warning('请先终止所有未完成工单，再取消订单')
    return
  }
  cancelReason.value = ''
  cancelDialogVisible.value = true
}

async function submitCancelOrder() {
  if (!detail.value) return

  const reason = cancelReason.value.trim()
  if (!reason) {
    ElMessage.warning('请输入取消原因')
    return
  }
  if (hasOpenWorkOrders()) {
    ElMessage.warning('请先终止所有未完成工单，再取消订单')
    return
  }

  cancelSubmitting.value = true
  try {
    await dispatcherOrdersApi.cancelMyOrder(route.params.orderId, {
      cancellation_reason: reason,
    })
    cancelDialogVisible.value = false
    ElMessage.success('订单已取消')
    await fetchDetail()
  } catch (error) {
    const detailMessage = error?.response?.data?.detail
    const message =
      error?.response?.data?.message ||
      (typeof detailMessage === 'string' ? detailMessage : detailMessage?.message) ||
      '订单取消失败'
    ElMessage.error(message)
  } finally {
    cancelSubmitting.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail-page {
  display: grid;
  gap: 12px;
  background: transparent;
}

.page-head {
  display: flex;
  gap: 8px;
}

.summary-text {
  margin: 0;
}

.risk-list {
  margin: 10px 0;
  padding-left: 18px;
  color: #6a5338;
}

.risk-hint-box {
  width: 100%;
  display: grid;
  gap: 4px;
  color: #6a5338;
  font-size: 13px;
}

.risk-hint-box p {
  margin: 0;
}

.risk-inline-tip {
  margin: 0;
  color: #b54708;
  font-size: 13px;
}

.skill-products-box {
  margin-bottom: 10px;
  display: grid;
  gap: 8px;
}

.skill-ok {
  color: #15803d;
  font-weight: 600;
}

.skill-bad {
  color: #b91c1c;
  font-weight: 600;
}

.create-form {
  max-width: 720px;
}

.agent-assistant {
  display: grid;
  gap: 10px;
}

.agent-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-robot {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e8f3ff;
}

.agent-title,
.agent-subtitle {
  margin: 0;
}

.agent-title {
  font-weight: 700;
  color: #2b2721;
}

.agent-subtitle {
  font-size: 12px;
  color: #6a5338;
}

.agent-form {
  max-width: 720px;
}

.agent-result {
  border: 1px solid #eadfce;
  border-radius: 10px;
  padding: 12px;
}

.agent-stage-list {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}

.agent-stage-card {
  border: 1px solid #f1e8da;
  border-radius: 8px;
  padding: 10px;
  background: #fffdfa;
  display: grid;
  gap: 8px;
}

.agent-stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.agent-stage-title {
  margin: 0;
  font-weight: 600;
  color: #4b3d2d;
}

.w-full {
  width: 100%;
}

:deep(.el-descriptions__label) {
  color: #5b4d3d;
  font-weight: 600;
}

:deep(.el-descriptions__content) {
  color: #2b2721;
}

:deep(.el-table th.el-table__cell) {
  background: #f5ece0;
  color: #6a5338;
}
</style>
