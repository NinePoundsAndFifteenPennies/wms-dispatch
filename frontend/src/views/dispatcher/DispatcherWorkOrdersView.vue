<template>
  <div class="dispatcher-page">
    <section class="page-hero">
      <p class="section-kicker">Work Order Center</p>
      <h2>工单中心保留调度看板结构，但全部使用本地静态数据</h2>
      <p>可浏览不同阶段与风险状态，方便先落地调度工作台的信息层。</p>
    </section>

    <section class="board-grid">
      <article v-for="column in columns" :key="column.key" class="board-column">
        <header>
          <p class="section-kicker">{{ column.label }}</p>
          <strong>{{ getItems(column.matcher).length }} 张</strong>
        </header>

        <div class="board-list">
          <div v-for="item in getItems(column.matcher)" :key="item.code" class="board-card" :class="statusClass(item.status)">
            <div class="card-head">
              <strong>{{ item.code }}</strong>
              <span>{{ item.priority }}</span>
            </div>
            <p>{{ item.orderNo }} / {{ item.worker }}</p>
            <small>{{ item.stage }} · 截止 {{ item.deadline }}</small>
            <small>{{ item.source }}</small>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { dispatcherWorkOrdersMock } from '../../modules/dispatcher/mock/dispatcher'

const columns = [
  { key: 'pending', label: '待处理', matcher: (item) => item.status === '待处理' },
  { key: 'active', label: '进行中', matcher: (item) => item.status === '进行中' },
  { key: 'risk', label: '超时告警', matcher: (item) => item.status === '超时告警' },
  { key: 'done', label: '已完成', matcher: (item) => item.status === '已完成' },
]

function getItems(matcher) {
  return dispatcherWorkOrdersMock.filter(matcher)
}

function statusClass(status) {
  return {
    待处理: 'status-pending',
    进行中: 'status-active',
    超时告警: 'status-alert',
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
.board-column {
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

.board-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.board-column {
  padding: 14px;
}

.board-column header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.board-list {
  display: grid;
  gap: 10px;
}

.board-card {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--dispatcher-border);
  background: var(--dispatcher-surface);
}

.card-head,
.board-card p,
.board-card small {
  margin: 0;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.board-card p {
  margin-top: 8px;
}

.board-card small {
  display: block;
  margin-top: 4px;
  color: var(--dispatcher-muted);
}

.status-pending {
  border-left: 4px solid #bb8137;
}

.status-active {
  border-left: 4px solid #35679c;
}

.status-alert {
  border-left: 4px solid #a54343;
}

.status-done {
  border-left: 4px solid #5f7c48;
}

@media (max-width: 1180px) {
  .board-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .board-grid {
    grid-template-columns: 1fr;
  }
}
</style>
