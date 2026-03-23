<template>
  <section class="panel">
    <div class="panel-head">
      <h4>{{ title }}</h4>
    </div>
    <v-chart class="chart" :option="option" autoresize />
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
  warehouseName: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
})

const title = computed(() => `${props.warehouseName || '仓库'} 调度员订单绩效`)

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 4 },
  grid: { left: 20, right: 24, top: 40, bottom: 46, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.dispatcher_name),
    axisLabel: { interval: 0, rotate: 16 },
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
      data: props.items.map((item) => item.total_orders),
      itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '已完成订单数',
      type: 'bar',
      barMaxWidth: 24,
      data: props.items.map((item) => item.completed_orders),
      itemStyle: { color: '#1c9c89', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '完成率',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      symbolSize: 8,
      data: props.items.map((item) => item.completion_rate),
      lineStyle: { color: '#f2994a', width: 2 },
      itemStyle: { color: '#f2994a' },
    },
  ],
}))
</script>

<style scoped>
.panel {
  padding: 8px;
}

.panel-head h4 {
  margin: 0 0 8px;
  font-size: 16px;
}

.chart {
  height: 380px;
}
</style>
