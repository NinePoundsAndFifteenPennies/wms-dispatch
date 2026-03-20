<template>
  <article class="order-card" @click="$emit('click')">
    <header class="card-head">
      <strong>{{ order.order_no }}</strong>
      <span class="status">{{ statusText(order.status) }}</span>
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
defineProps({
  order: {
    type: Object,
    required: true,
  },
})

defineEmits(['click'])

function statusText(status) {
  return {
    pending_acceptance: '待接单',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }[status] || status
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
  color: #8f6d42;
  font-weight: 600;
  background: #f7ead6;
  padding: 2px 8px;
  border-radius: 999px;
}

.time {
  color: var(--dispatcher-soft);
}
</style>
