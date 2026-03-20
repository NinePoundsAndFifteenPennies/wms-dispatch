<template>
  <div class="dispatcher-page">
    <section class="page-hero">
      <p class="section-kicker">Order Center</p>
      <h2>订单中心使用静态 mock 展示调度视角</h2>
      <p>这里保留了调度筛选、状态密度和操作位，但不会对接真实管理员订单接口。</p>
    </section>

    <section class="toolbar">
      <div class="filter-group">
        <button
          v-for="option in statusOptions"
          :key="option"
          type="button"
          class="filter-chip"
          :class="{ active: activeStatus === option }"
          @click="activeStatus = option"
        >
          {{ option }}
        </button>
      </div>
      <div class="filter-group">
        <button
          v-for="option in priorityOptions"
          :key="option"
          type="button"
          class="filter-chip"
          :class="{ active: activePriority === option }"
          @click="activePriority = option"
        >
          {{ option }}
        </button>
      </div>
    </section>

    <section class="table-shell">
      <header class="table-head">
        <span>订单号</span>
        <span>客户 / 仓库</span>
        <span>优先级</span>
        <span>状态</span>
        <span>接单时间</span>
        <span>备注</span>
      </header>

      <article v-for="order in filteredOrders" :key="order.orderNo" class="table-row">
        <div>
          <strong>{{ order.orderNo }}</strong>
          <small>{{ order.stage }}</small>
        </div>
        <div>
          <strong>{{ order.customer }}</strong>
          <small>{{ order.warehouse }}</small>
        </div>
        <div>
          <span class="priority-chip" :class="priorityClass(order.priority)">{{ order.priority }}</span>
        </div>
        <div>
          <span class="status-chip" :class="statusClass(order.status)">{{ order.status }}</span>
        </div>
        <div>
          <strong>{{ order.acceptedAt }}</strong>
          <small>责任调度：{{ order.dispatcher }}</small>
        </div>
        <div>
          <strong>{{ order.totalItems }} 件</strong>
          <small>{{ order.note }}</small>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { dispatcherOrdersMock } from '../../modules/dispatcher/mock/dispatcher'

const statusOptions = ['全部', '待接单', '进行中', '告警处理中', '已完成']
const priorityOptions = ['全部', '高', '中', '低']
const activeStatus = ref('全部')
const activePriority = ref('全部')

const filteredOrders = computed(() =>
  dispatcherOrdersMock.filter((item) => {
    const passStatus = activeStatus.value === '全部' || item.status === activeStatus.value
    const passPriority = activePriority.value === '全部' || item.priority === activePriority.value
    return passStatus && passPriority
  })
)

function priorityClass(priority) {
  return {
    高: 'priority-high',
    中: 'priority-medium',
    低: 'priority-low',
  }[priority]
}

function statusClass(status) {
  return {
    待接单: 'status-pending',
    进行中: 'status-active',
    告警处理中: 'status-alert',
    已完成: 'status-done',
  }[status]
}
</script>

<style scoped>
.dispatcher-page {
  display: grid;
  gap: 14px;
}

.page-hero,
.toolbar,
.table-shell {
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.88);
}

.page-hero {
  padding: 18px 20px;
}

.page-hero h2,
.page-hero p,
.section-kicker {
  margin: 0;
}

.section-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.page-hero h2 {
  margin-top: 6px;
  font-size: 24px;
}

.page-hero p:last-child {
  margin-top: 8px;
  color: var(--dispatcher-muted);
  line-height: 1.6;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
}

.filter-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-chip {
  border: 1px solid var(--dispatcher-border);
  border-radius: 999px;
  padding: 7px 12px;
  background: #f3eee5;
  color: var(--dispatcher-muted);
  cursor: pointer;
}

.filter-chip.active {
  background: #2c2923;
  border-color: #2c2923;
  color: #faf7f0;
}

.table-shell {
  overflow: hidden;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 1.2fr 1.3fr 0.7fr 0.9fr 1fr 1fr;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
}

.table-head {
  border-bottom: 1px solid var(--dispatcher-border);
  background: #f4eee4;
  font-size: 12px;
  color: var(--dispatcher-soft);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.table-row + .table-row {
  border-top: 1px solid rgba(214, 208, 196, 0.72);
}

.table-row strong,
.table-row small {
  display: block;
}

.table-row small {
  margin-top: 4px;
  color: var(--dispatcher-muted);
}

.priority-chip,
.status-chip {
  display: inline-flex;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.priority-high,
.status-alert {
  background: var(--dispatcher-alert-bg);
  color: var(--dispatcher-alert-text);
}

.priority-medium,
.status-pending {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.priority-low,
.status-done {
  background: #e8efdd;
  color: #436c25;
}

.status-active {
  background: var(--dispatcher-active-bg);
  color: var(--dispatcher-active-text);
}

@media (max-width: 980px) {
  .toolbar {
    flex-direction: column;
  }

  .table-head {
    display: none;
  }

  .table-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .table-row {
    grid-template-columns: 1fr;
  }
}
</style>
