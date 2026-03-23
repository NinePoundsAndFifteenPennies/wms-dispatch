<template>
  <section class="metrics">
    <article
      v-for="item in cards"
      :key="item.key"
      class="metric-card"
      role="button"
      tabindex="0"
      @click="emit('card-click', item.key)"
      @keyup.enter="emit('card-click', item.key)"
    >
      <p>
        <el-icon><component :is="item.icon" /></el-icon>
        {{ item.label }}
      </p>
      <h4>{{ item.value }}</h4>
      <span class="hint">点击查看明细</span>
    </article>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import {
  CircleCloseFilled,
  Document,
  Promotion,
  WarningFilled,
} from '@element-plus/icons-vue'

const props = defineProps({
  kpis: {
    type: Object,
    default: () => ({
      pending_acceptance_orders: 0,
      low_stock_alerts: 0,
      cancelled_orders_today: 0,
      accepted_no_dispatch_orders: 0,
    }),
  },
})

const emit = defineEmits(['card-click'])

const cards = computed(() => [
  {
    key: 'pending_acceptance_orders',
    label: '待接单订单',
    value: props.kpis.pending_acceptance_orders ?? 0,
    icon: Document,
  },
  {
    key: 'accepted_no_dispatch_orders',
    label: '接单未派工',
    value: props.kpis.accepted_no_dispatch_orders ?? 0,
    icon: Promotion,
  },
  {
    key: 'low_stock_alerts',
    label: '低库存告警',
    value: props.kpis.low_stock_alerts ?? 0,
    icon: WarningFilled,
  },
  {
    key: 'cancelled_orders_today',
    label: '今日取消订单',
    value: props.kpis.cancelled_orders_today ?? 0,
    icon: CircleCloseFilled,
  },
])
</script>

<style scoped>
.metrics {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(16, 34, 53, 0.08);
  border-color: #bdd0e0;
}

.metric-card p {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.metric-card h4 {
  margin: 8px 0 4px;
  font-size: 28px;
  color: #16202a;
}

.hint {
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 960px) {
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
