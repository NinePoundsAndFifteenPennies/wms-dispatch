<template>
  <section class="flow-card" v-loading="loading">
    <header class="flow-card-head">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ subtitle }}</p>
      </div>
      <el-button type="primary" plain size="small" @click="expanded = true">放大查看</el-button>
    </header>

    <v-chart class="flow-chart" :option="chartOption" autoresize @click="onChartClick" />

    <el-dialog v-model="expanded" width="min(1080px, 92vw)" destroy-on-close>
      <template #header>
        <span>{{ title }} · 流水趋势详情</span>
      </template>
      <v-chart class="flow-chart flow-chart-large" :option="chartOption" autoresize @click="onChartClick" />
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, AxisPointerComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, AxisPointerComponent])

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  points: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['point-click'])
const expanded = ref(false)

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter(params) {
      const point = params?.[0]?.data?.payload
      if (!point) return ''
      return [
        `<strong>${point.date}</strong>`,
        `流水笔数: ${point.movement_count}`,
        `变动总量: ${point.total_abs_delta}`,
      ].join('<br/>')
    },
  },
  grid: { left: 42, right: 20, top: 22, bottom: 28, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.points.map((item) => item.date.slice(5)),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: '#d7d8df' } },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#ececf3' } },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 9,
      data: props.points.map((item) => ({
        value: item.movement_count,
        payload: item,
      })),
      lineStyle: { color: '#198f7b', width: 3 },
      itemStyle: { color: '#198f7b', borderColor: '#ffffff', borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(25, 143, 123, 0.35)' },
            { offset: 1, color: 'rgba(25, 143, 123, 0.04)' },
          ],
        },
      },
      emphasis: {
        focus: 'series',
      },
    },
  ],
}))

function onChartClick(params) {
  const payload = params?.data?.payload
  if (!payload || !payload.date) return
  emit('point-click', payload)
}
</script>

<style scoped>
.flow-card {
  border: 1px solid #d8dde6;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
}

.flow-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.flow-card-head h3 {
  margin: 0;
  font-size: 16px;
  color: #1f2430;
}

.flow-card-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #697082;
}

.flow-chart {
  height: 280px;
}

.flow-chart-large {
  height: 64vh;
  min-height: 420px;
}
</style>
