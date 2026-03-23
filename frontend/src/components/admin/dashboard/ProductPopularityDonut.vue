<template>
  <section class="panel">
    <div class="panel-head">
      <h4>产品热度图（已完成订单）</h4>
      <span>按销量占比显示热度，点击扇区可查看产品详情</span>
    </div>
    <v-chart class="chart" :option="option" autoresize @click="handleChartClick" />
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

const emit = defineEmits(['product-click'])

const MAX_VISIBLE_PRODUCTS = 6

const totalQty = computed(() =>
  props.items.reduce((sum, item) => sum + Number(item.total_qty || 0), 0),
)

const chartItems = computed(() => {
  const normalized = props.items
    .map((item) => ({
      ...item,
      total_qty: Number(item.total_qty || 0),
      order_count: Number(item.order_count || 0),
    }))
    .filter((item) => item.total_qty > 0)
    .sort((a, b) => b.total_qty - a.total_qty)

  if (normalized.length <= MAX_VISIBLE_PRODUCTS) {
    return normalized
  }

  const head = normalized.slice(0, MAX_VISIBLE_PRODUCTS)
  const tail = normalized.slice(MAX_VISIBLE_PRODUCTS)
  const othersQty = tail.reduce((sum, item) => sum + item.total_qty, 0)
  const othersOrderCount = tail.reduce((sum, item) => sum + item.order_count, 0)

  head.push({
    product_id: null,
    sku: 'OTHERS',
    product_name: '其他产品',
    total_qty: othersQty,
    order_count: othersOrderCount,
    is_others: true,
  })
  return head
})

function getHeatColorByShare(share) {
  if (share >= 0.22) return '#b91c1c'
  if (share >= 0.16) return '#ea580c'
  if (share >= 0.1) return '#f59e0b'
  if (share >= 0.06) return '#3b82f6'
  return '#10b981'
}

function getHeatLevelByShare(share) {
  if (share >= 0.22) return '极热'
  if (share >= 0.16) return '高热'
  if (share >= 0.1) return '中热'
  if (share >= 0.06) return '温热'
  return '常规'
}

function handleChartClick(params) {
  const data = params?.data
  if (!data?.product_id || data?.is_others) return
  emit('product-click', {
    productId: data.product_id,
    sku: data.sku,
    productName: data.product_name,
  })
}

const option = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (params) => {
      const data = params?.data || {}
      const percent = Number(params?.percent || 0).toFixed(1)
      return `${data.name}<br/>热度等级: ${data.heat_level || '常规'}<br/>销量: ${data.value}<br/>订单数: ${data.order_count || 0}<br/>销量占比: ${percent}%`
    },
  },
  legend: {
    type: 'scroll',
    orient: 'vertical',
    right: 0,
    top: 16,
    bottom: 16,
  },
  series: [
    {
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['38%', '50%'],
      minAngle: 4,
      itemStyle: { borderRadius: 6 },
      label: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 10,
        label: {
          show: true,
          formatter: ({ data }) => `${data.product_name}\n销量 ${data.value} (${data.percent_text})`,
        },
      },
      data: chartItems.value.map((item) => {
        const total = totalQty.value
        const value = Number(item.total_qty || 0)
        const share = total > 0 ? value / total : 0
        return {
        name: `${item.product_name} (${item.sku})`,
        value,
        sku: item.sku,
        product_id: item.product_id,
        product_name: item.product_name,
        order_count: item.order_count,
        is_others: Boolean(item.is_others),
        heat_level: getHeatLevelByShare(share),
        percent_text: `${(share * 100).toFixed(1)}%`,
        itemStyle: { color: getHeatColorByShare(share) },
      }
      }),
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
  height: 360px;
}
</style>
