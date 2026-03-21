<template>
  <article class="order-card" @click="$emit('click')">
    <header class="card-head">
      <strong>{{ order.order_no }}</strong>
      <span class="status" :class="statusMeta(order.status).className">{{ statusMeta(order.status).text }}</span>
    </header>
    <p class="customer">{{ order.customer_name }}</p>
    <p class="meta">
      <span>{{ priorityText(order.priority) }}</span>
      <span>{{ order.total_items }} 件</span>
    </p>
    <p class="time">更新：{{ formatDate(order.updated_at) }}</p>
  </article>
</template>

<script setup>
const props = defineProps({
  order: {
    type: Object,
    required: true,
  },
  mode: {
    type: String,
    default: 'default',
  },
})

defineEmits(['click'])

function statusMeta(status) {
  const shared = {
    completed: { text: '已完成', className: 'status-completed' },
    cancelled: { text: '已取消', className: 'status-cancelled' },
    in_progress: { text: '进行中', className: 'status-in-progress' },
    pending_acceptance: { text: '待接单', className: 'status-pending' },
  }

  if (props.mode === 'mine') {
    return {
      completed: { text: '已完成 · 归档', className: 'status-completed' },
      cancelled: { text: '已取消 · 已终止', className: 'status-cancelled' },
      in_progress: { text: '执行中 · 待收尾', className: 'status-in-progress' },
      pending_acceptance: { text: '待接单', className: 'status-pending' },
    }[status] || { text: status, className: 'status-default' }
  }

  return shared[status] || { text: status, className: 'status-default' }
}

function priorityText(priority) {
  return {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级',
  }[priority] || priority
}

function formatDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}
</script>

<style scoped>
.order-card {
  border: 1px solid #d9cfbe;
  border-radius: 14px;
  padding: 12px;
  background: linear-gradient(155deg, #fffdf9 0%, #f8f3ea 100%);
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(91, 75, 51, 0.08);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.order-card:hover {
  transform: translateY(-2px);
  border-color: #bfa781;
  box-shadow: 0 10px 22px rgba(91, 75, 51, 0.16);
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.customer,
.meta,
.time {
  margin: 8px 0 0;
  font-size: 12px;
}

.customer {
  font-size: 13px;
  color: #2b2721;
}

.meta {
  display: flex;
  justify-content: space-between;
  color: #6f675a;
}

.status {
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.status-pending {
  color: #8f6d42;
  background: #f7ead6;
}

.status-in-progress {
  color: #1f5c9a;
  background: #e5f0fc;
}

.status-completed {
  color: #22663f;
  background: #dcf3e4;
}

.status-cancelled {
  color: #9d4e3b;
  background: #f9e6df;
}

.status-default {
  color: #5f5a52;
  background: #ece9e2;
}

.time {
  color: var(--dispatcher-soft);
}
</style>
