<template>
  <section class="panel">
    <div class="panel-head">
      <h4>低库存 Top</h4>
      <span>点击条目进入仓库库存详情</span>
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

const emit = defineEmits(['item-click'])

const option = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 10, right: 54, top: 16, bottom: 20, containLabel: true },
  xAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#e6eef4' } },
  },
  yAxis: {
    type: 'category',
    inverse: true,
    data: props.items.map((item) => `${item.product_name} (${item.sku})`),
    axisTick: { show: false },
  },
  series: [
    {
      type: 'bar',
      barMaxWidth: 26,
      data: props.items.map((item) => ({
        value: Math.max(0, item.qty_threshold - item.qty_available),
        warehouse_id: item.warehouse_id,
      })),
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: '#f2994a',
      },
      label: {
        show: true,
        position: 'right',
        distance: 4,
        formatter: ({ value }) => `${value}`,
      },
    },
  ],
}))

function handleClick(params) {
  if (!params?.data?.warehouse_id) return
  emit('item-click', params.data.warehouse_id)
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
