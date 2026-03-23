<template>
  <section class="panel">
    <div class="panel-head">
      <h4>仓库负载对比</h4>
      <span>点击柱子进入仓库库存详情</span>
    </div>
    <v-chart class="chart" :option="option" autoresize @click="handleClick" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['bar-click'])

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 20, right: 20, top: 16, bottom: 36, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.warehouse_name),
    axisLabel: { interval: 0, rotate: 12 },
  },
  yAxis: {
    type: 'value',
    max: 100,
    axisLabel: { formatter: '{value}%' },
  },
  series: [
    {
      type: 'bar',
      barMaxWidth: 34,
      data: props.items.map((item) => ({
        value: item.load_percent,
        warehouse_id: item.warehouse_id,
      })),
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: '#1c9c89' },
            { offset: 1, color: '#117264' },
          ],
        },
      },
    },
  ],
}))

function handleClick(params) {
  if (!params?.data?.warehouse_id) return
  emit('bar-click', params.data.warehouse_id)
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
  height: 320px;
}
</style>
