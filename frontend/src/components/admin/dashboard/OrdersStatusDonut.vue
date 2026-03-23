<template>
  <section class="panel">
    <div class="panel-head">
      <h4>订单状态分布</h4>
    </div>
    <v-chart class="chart" :option="option" autoresize @click="handleClick" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, LegendComponent, TooltipComponent])

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['slice-click'])

const option = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, icon: 'circle' },
  color: ['#1c9c89', '#3b82f6', '#22c55e', '#f97316'],
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '44%'],
      padAngle: 2,
      itemStyle: { borderRadius: 6 },
      label: { formatter: '{b}\n{c}' },
      data: props.items.map((item) => ({
        name: item.label,
        value: item.value,
        key: item.key,
      })),
    },
  ],
}))

function handleClick(params) {
  if (!params?.data?.key) return
  emit('slice-click', params.data.key)
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
  align-items: center;
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
