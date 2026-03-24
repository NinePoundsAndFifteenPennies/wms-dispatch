<template>
  <el-dialog
    :model-value="modelValue"
    width="min(1120px, 94vw)"
    destroy-on-close
    @update:model-value="(val) => emit('update:modelValue', val)"
  >
    <template #header>
      <div class="dialog-header">
        <strong>{{ title }}</strong>
        <small>{{ warehouseName }} · {{ date }}</small>
      </div>
    </template>

    <section class="summary-grid">
      <article>
        <p>当日流水笔数</p>
        <h4>{{ movementCount }}</h4>
      </article>
      <article>
        <p>当日变化总量</p>
        <h4>{{ totalAbsDelta }}</h4>
        <div class="delta-pair">
          <span class="up">▲ +{{ positiveDeltaOnHand }}</span>
          <span class="down">▼ -{{ negativeDeltaOnHandAbs }}</span>
        </div>
      </article>
      <article>
        <p>当前页原子节点</p>
        <h4>{{ orderedRows.length }}</h4>
      </article>
    </section>

    <section class="curve-wrap" v-loading="loading">
      <v-chart
        class="atomic-chart"
        :option="chartOption"
        autoresize
        @click="handleChartClick"
      />
    </section>

    <section class="node-detail-card" v-if="selectedNode">
      <header>
        <strong>选中原子节点</strong>
        <small>{{ formatCnDateTime(selectedNode.created_at) }}</small>
      </header>
      <div class="detail-grid">
        <div><label>变化类型</label><p>{{ selectedNode.change_type || '-' }}</p></div>
        <div><label>商品</label><p>{{ selectedNode.product_name }}（{{ selectedNode.product_sku }}）</p></div>
        <div><label>现存变化</label><p :class="Number(selectedNode.delta_on_hand) >= 0 ? 'up' : 'down'">{{ formatSigned(selectedNode.delta_on_hand) }}</p></div>
        <div><label>操作人</label><p>{{ selectedNode.operated_by_name || '-' }}</p></div>
        <div><label>关联对象</label><p>{{ selectedNode.related_type || '-' }} {{ selectedNode.related_id || '' }}</p></div>
        <div class="full"><label>业务说明</label><p>{{ selectedNode.related_description || '-' }}</p></div>
      </div>
    </section>

    <div class="pager-wrap">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="(value) => emit('current-change', value)"
        @size-change="(value) => emit('size-change', value)"
      />
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, AxisPointerComponent } from 'echarts/components'
import { formatCnDateTime, toCnTimestamp } from '../../utils/cnTime'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, AxisPointerComponent])

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '流水节点详情',
  },
  warehouseName: {
    type: String,
    default: '',
  },
  date: {
    type: String,
    default: '',
  },
  movementCount: {
    type: Number,
    default: 0,
  },
  totalAbsDelta: {
    type: Number,
    default: 0,
  },
  positiveDeltaOnHand: {
    type: Number,
    default: 0,
  },
  negativeDeltaOnHandAbs: {
    type: Number,
    default: 0,
  },
  rows: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  total: {
    type: Number,
    default: 0,
  },
  page: {
    type: Number,
    default: 1,
  },
  pageSize: {
    type: Number,
    default: 20,
  },
})

const emit = defineEmits(['update:modelValue', 'current-change', 'size-change'])
const selectedNode = ref(null)

const orderedRows = computed(() => {
  return [...props.rows].sort((a, b) => toCnTimestamp(a.created_at) - toCnTimestamp(b.created_at))
})

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter(params) {
      const payload = params?.[0]?.data?.payload
      if (!payload) return ''
      return [
        `<strong>${formatCnDateTime(payload.created_at)}</strong>`,
        `现存变化: ${formatSigned(payload.delta_on_hand)}`,
        `类型: ${payload.change_type || '-'}`,
        `商品: ${payload.product_name || '-'} (${payload.product_sku || '-'})`,
        `说明: ${payload.related_description || '-'}`,
      ].join('<br/>')
    },
  },
  grid: { left: 42, right: 20, top: 22, bottom: 32, containLabel: true },
  xAxis: {
    type: 'category',
    axisTick: { show: false },
    data: orderedRows.value.map((row, index) => {
      const text = formatCnDateTime(row.created_at)
      return `${index + 1}.${text.slice(11)}`
    }),
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#e7ebf3' } },
  },
  series: [
    {
      type: 'line',
      smooth: false,
      symbol: 'circle',
      symbolSize: 9,
      data: orderedRows.value.map((row) => ({
        value: Number(row.delta_on_hand || 0),
        payload: row,
        itemStyle: {
          color: Number(row.delta_on_hand || 0) >= 0 ? '#1f9b55' : '#d14343',
        },
      })),
      lineStyle: { color: '#2f4f8f', width: 2 },
      itemStyle: { borderColor: '#ffffff', borderWidth: 2 },
    },
  ],
}))

watch(
  orderedRows,
  (list) => {
    selectedNode.value = list[0] || null
  },
  { immediate: true }
)

function formatSigned(value) {
  const num = Number(value || 0)
  if (num > 0) return `+${num}`
  return String(num)
}

function handleChartClick(params) {
  const payload = params?.data?.payload
  if (!payload) return
  selectedNode.value = payload
}
</script>

<style scoped>
.dialog-header {
  display: grid;
  gap: 2px;
}

.dialog-header small {
  color: #72798a;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.summary-grid article {
  border: 1px solid #e2e6ee;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fafbff;
}

.summary-grid p {
  margin: 0;
  font-size: 12px;
  color: #6f7788;
}

.summary-grid h4 {
  margin: 6px 0 0;
  font-size: 20px;
  color: #1f2430;
}

.delta-pair {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  font-size: 12px;
  font-weight: 700;
}

.curve-wrap {
  border: 1px solid #e1e6f0;
  border-radius: 12px;
  padding: 8px;
  background: #ffffff;
}

.atomic-chart {
  height: 360px;
}

.node-detail-card {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e0e5ee;
  border-radius: 12px;
  background: #fafbff;
}

.node-detail-card header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.node-detail-card header small {
  color: #6f7788;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.detail-grid .full {
  grid-column: 1 / -1;
}

.detail-grid label {
  display: block;
  font-size: 12px;
  color: #6f7788;
}

.detail-grid p {
  margin: 3px 0 0;
  color: #1f2430;
}

.up {
  color: #1f9b55;
}

.down {
  color: #d14343;
}

.pager-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 920px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
