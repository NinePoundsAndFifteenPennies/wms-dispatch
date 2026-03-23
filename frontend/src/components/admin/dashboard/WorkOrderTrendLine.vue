<template>
  <section class="panel">
    <div class="panel-head">
      <h4>近7天工单完成趋势</h4>
    </div>
    <v-chart class="chart" :option="option" autoresize />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, AxisPointerComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, AxisPointerComponent])

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 36, right: 18, top: 16, bottom: 24, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.date.slice(5)),
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#e6eef4' } },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: props.items.map((item) => item.completed_count),
      lineStyle: { color: '#1c9c89', width: 3 },
      itemStyle: { color: '#1c9c89' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(28, 156, 137, 0.35)' },
            { offset: 1, color: 'rgba(28, 156, 137, 0.02)' },
          ],
        },
      },
    },
  ],
}))
</script>

<style scoped>
.panel {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.panel-head {
  margin-bottom: 8px;
}

.panel-head h4 {
  margin: 0;
  font-size: 16px;
}

.chart {
  height: 320px;
}
</style>
