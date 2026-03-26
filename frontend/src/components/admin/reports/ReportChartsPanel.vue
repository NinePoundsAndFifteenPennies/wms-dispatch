<template>
  <div class="report-chart-grid">
    <section class="chart-card">
      <header class="chart-head">
        <h4>工单趋势（完成/超时）</h4>
      </header>
      <v-chart v-if="trendItems.length" class="chart" :option="trendOption" autoresize />
      <el-empty v-else description="暂无趋势数据" :image-size="88" />
    </section>

    <section class="chart-card">
      <header class="chart-head">
        <h4>阶段分布（总量/完成/超时）</h4>
      </header>
      <v-chart v-if="stageItems.length" class="chart" :option="stageOption" autoresize />
      <el-empty v-else description="暂无阶段数据" :image-size="88" />
    </section>
  </div>
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
  stats: {
    type: Object,
    default: () => ({}),
  },
})

const trendItems = computed(() => (Array.isArray(props.stats?.daily_trend) ? props.stats.daily_trend : []))
const stageItems = computed(() => (Array.isArray(props.stats?.by_stage) ? props.stats.by_stage : []))

function stageText(value) {
  return {
    picking: '拣货',
    staging: '备货',
    shipping: '发货',
  }[value] || value || '-'
}

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 4 },
  grid: { left: 28, right: 22, top: 44, bottom: 26, containLabel: true },
  xAxis: {
    type: 'category',
    data: trendItems.value.map((item) => String(item.day || '').slice(5)),
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#e8eef4' } },
  },
  series: [
    {
      name: '完成数',
      type: 'line',
      smooth: true,
      symbolSize: 7,
      data: trendItems.value.map((item) => Number(item.completed || 0)),
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
            { offset: 1, color: 'rgba(28, 156, 137, 0.04)' },
          ],
        },
      },
    },
    {
      name: '超时数',
      type: 'line',
      smooth: true,
      symbolSize: 7,
      data: trendItems.value.map((item) => Number(item.timeout || 0)),
      lineStyle: { color: '#ef4444', width: 2 },
      itemStyle: { color: '#ef4444' },
    },
  ],
}))

const stageOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 4 },
  grid: { left: 18, right: 18, top: 44, bottom: 56, containLabel: true },
  xAxis: {
    type: 'category',
    data: stageItems.value.map((item) => stageText(item.stage_type)),
    axisLabel: { interval: 0 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#e8eef4' } },
  },
  series: [
    {
      name: '总量',
      type: 'bar',
      barMaxWidth: 24,
      data: stageItems.value.map((item) => Number(item.total || 0)),
      itemStyle: { color: '#4f46e5', borderRadius: [6, 6, 0, 0] },
    },
    {
      name: '完成',
      type: 'bar',
      barMaxWidth: 24,
      data: stageItems.value.map((item) => Number(item.completed || 0)),
      itemStyle: { color: '#16a34a', borderRadius: [6, 6, 0, 0] },
    },
    {
      name: '超时',
      type: 'bar',
      barMaxWidth: 24,
      data: stageItems.value.map((item) => Number(item.timeout || 0)),
      itemStyle: { color: '#f97316', borderRadius: [6, 6, 0, 0] },
    },
  ],
}))
</script>

<style scoped>
.report-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.chart-card {
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 12px;
}

.chart-head h4 {
  margin: 0;
  font-size: 15px;
}

.chart {
  height: 280px;
}

@media (max-width: 960px) {
  .report-chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
