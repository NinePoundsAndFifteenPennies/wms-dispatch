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
  border: 1px solid var(--dispatcher-border);
  border-radius: 12px;
  padding: 10px;
  background: #fffdf9;
  cursor: pointer;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.customer,
.meta,
.time {
  margin: 6px 0 0;
  font-size: 12px;
}

.meta {
  display: flex;
  justify-content: space-between;
}

.status {
  color: var(--dispatcher-muted);
}

.time {
  color: var(--dispatcher-soft);
}
</style>
