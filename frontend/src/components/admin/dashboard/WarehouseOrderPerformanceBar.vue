<template>
  <section class="panel">
    <div class="panel-head">
      <h4>各仓库订单完成绩效</h4>
      <span>点击柱子查看该仓调度员绩效</span>
    </div>
    <v-chart class="chart" :option="option" autoresize @click="handleClick" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['warehouse-click'])

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 4 },
  grid: { left: 20, right: 24, top: 40, bottom: 36, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.warehouse_name),
    axisLabel: { interval: 0, rotate: 12 },
  },
  yAxis: [
    {
      type: 'value',
      name: '订单量',
      minInterval: 1,
    },
    {
      type: 'value',
      name: '完成率',
      max: 100,
      axisLabel: { formatter: '{value}%' },
    },
  ],
  series: [
    {
      name: '总订单数',
      type: 'bar',
      barMaxWidth: 24,
      data: props.items.map((item) => ({ value: item.total_orders, warehouse_id: item.warehouse_id })),
      itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '已完成订单数',
      type: 'bar',
      barMaxWidth: 24,
      data: props.items.map((item) => ({ value: item.completed_orders, warehouse_id: item.warehouse_id })),
      itemStyle: { color: '#1c9c89', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '完成率',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      symbolSize: 8,
      data: props.items.map((item) => ({ value: item.completion_rate, warehouse_id: item.warehouse_id })),
      lineStyle: { color: '#f2994a', width: 2 },
      itemStyle: { color: '#f2994a' },
    },
  ],
}))

function handleClick(params) {
  const warehouseId = params?.data?.warehouse_id
  if (!warehouseId) return
  emit('warehouse-click', warehouseId)
}
</script>

<style scoped>
.panel {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.panel-head h4 {
  margin: 0;
  font-size: 16px;
}

.panel-head span {
  font-size: 12px;
  color: #64748b;
}

.chart {
  height: 340px;
}
</style>
