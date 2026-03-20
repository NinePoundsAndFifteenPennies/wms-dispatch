<template>
  <div class="dispatcher-workbench">
    <section class="focus-banner">
      <p class="section-kicker">Today Focus</p>
      <h2>{{ workbench.focus.title }}</h2>
      <p>{{ workbench.focus.description }}</p>
    </section>

    <section class="workspace-grid">
      <aside class="queue-panel">
        <div class="panel-heading">
          <div>
            <p class="section-kicker">订单队列</p>
            <h3>进行中 / 待接单</h3>
          </div>
        </div>

        <div class="queue-list">
          <button
            v-for="order in workbench.orderQueue"
            :key="order.id"
            type="button"
            class="queue-card"
            :class="{
              selected: selectedOrderId === order.id,
              alert: order.alertText,
            }"
            @click="selectOrder(order.id)"
          >
            <div class="queue-card-head">
              <strong>{{ order.orderNo }}</strong>
              <span class="priority-chip" :class="`priority-${order.priority}`">{{ order.priorityText }}</span>
            </div>
            <p>{{ order.customer }}</p>
            <small>{{ order.stageSummary }}</small>
            <small v-if="order.alertText" class="alert-copy">{{ order.alertText }}</small>
          </button>
        </div>

        <section class="reminder-panel">
          <p class="section-kicker">调度提醒</p>
          <ul>
            <li v-for="item in workbench.reminders" :key="item">{{ item }}</li>
          </ul>
        </section>
      </aside>

      <section class="detail-panel">
        <div class="detail-head">
          <div>
            <h3>{{ selectedOrder.orderNo }} / {{ selectedOrder.customer }}</h3>
            <p>
              仓库：{{ selectedOrder.warehouse }} · 接单时间：{{ selectedOrder.acceptedAt }} ·
              状态：{{ selectedOrder.statusText }}
            </p>
          </div>
          <button type="button" class="ghost-button">取消订单</button>
        </div>

        <div class="stage-tabs">
          <button
            v-for="stage in selectedOrder.stages"
            :key="stage.key"
            type="button"
            class="stage-tab"
            :class="[stage.status, { active: activeStageKey === stage.key }]"
            :disabled="stage.status === 'locked'"
            @click="activeStageKey = stage.key"
          >
            {{ stage.label }}
            <span v-if="stage.status === 'done'">已完成</span>
          </button>
        </div>

        <div class="detail-body">
          <div class="action-row">
            <span>当前阶段工单 {{ activeWorkOrders.length }} 张</span>
            <button type="button" class="primary-button">+ 派发工单</button>
          </div>

          <div v-if="activeWorkOrders.length > 0" class="work-order-list">
            <article
              v-for="item in activeWorkOrders"
              :key="item.id"
              class="work-order-card"
              :class="item.status"
            >
              <div class="worker-avatar">{{ item.worker.slice(0, 1) }}</div>
              <div class="work-order-meta">
                <strong>{{ item.worker }}</strong>
                <p>{{ item.skill }} · {{ item.timeText }}</p>
              </div>
              <span class="status-chip" :class="item.status">{{ item.statusText }}</span>
            </article>
          </div>
          <div v-else class="empty-state">
            当前阶段还没有派发工单，这里只展示 mock 布局，不会调用真实接口。
          </div>

          <div class="advance-panel">
            <span>阶段推进：等待所有工单完成后自动推进，或由调度员手动标记完成。</span>
            <button type="button" class="ghost-button">手动完成阶段</button>
          </div>
        </div>
      </section>

      <aside class="insight-panel">
        <section class="side-card">
          <p class="section-kicker">本仓工人状态</p>
          <div v-for="worker in workbench.warehouseWorkers" :key="worker.id" class="worker-row">
            <span class="worker-dot" :class="{ busy: worker.busy }"></span>
            <strong>{{ worker.name }}</strong>
            <small>{{ worker.skill }} · {{ worker.statusText }}</small>
          </div>
        </section>

        <section class="side-card">
          <p class="section-kicker">当前订单概览</p>
          <div class="stat-row">
            <span>商品种类</span>
            <strong>{{ selectedOrder.totalSkus }}</strong>
          </div>
          <div class="stat-row">
            <span>总件数</span>
            <strong>{{ selectedOrder.totalItems }}</strong>
          </div>
          <div class="stat-row">
            <span>客户联系</span>
            <strong>{{ selectedOrder.contact }}</strong>
          </div>
          <div class="order-note">{{ selectedOrder.description }}</div>
        </section>

        <section class="side-card">
          <p class="section-kicker">动态流</p>
          <article
            v-for="item in selectedOrder.activities"
            :key="`${item.time}-${item.text}`"
            class="activity-item"
            :class="{ alert: item.tone === 'alert' }"
          >
            <strong>{{ item.text }}</strong>
            <small>{{ item.time }}</small>
          </article>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { dispatcherWorkbenchMock } from '../../modules/dispatcher/mock/dispatcher'

const workbench = dispatcherWorkbenchMock
const selectedOrderId = ref(workbench.orderQueue[0].id)
const activeStageKey = ref(workbench.orderQueue[0].stages.find((item) => item.status !== 'locked')?.key || 'picking')

const selectedOrder = computed(
  () => workbench.orderQueue.find((item) => item.id === selectedOrderId.value) || workbench.orderQueue[0]
)

const activeWorkOrders = computed(() => selectedOrder.value.workOrders[activeStageKey.value] || [])

function selectOrder(orderId) {
  selectedOrderId.value = orderId
  const order = workbench.orderQueue.find((item) => item.id === orderId)
  activeStageKey.value = order?.stages.find((item) => item.status === 'active')?.key || 'picking'
}
</script>

<style scoped>
.dispatcher-workbench {
  display: grid;
  gap: 16px;
}

.focus-banner {
  padding: 18px 20px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: linear-gradient(135deg, #faf7f1 0%, #f1ece3 100%);
}

.focus-banner h2,
.focus-banner p,
.section-kicker,
.panel-heading h3 {
  margin: 0;
}

.focus-banner h2 {
  margin-top: 6px;
  font-size: 28px;
}

.focus-banner p:last-child {
  margin-top: 8px;
  color: var(--dispatcher-muted);
  line-height: 1.7;
}

.section-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dispatcher-soft);
}

.workspace-grid {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 16px;
}

.queue-panel,
.detail-panel,
.insight-panel {
  min-width: 0;
}

.queue-panel,
.detail-panel,
.side-card {
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.86);
}

.queue-panel {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-heading h3 {
  margin-top: 4px;
  font-size: 18px;
}

.queue-list {
  display: grid;
  gap: 10px;
}

.queue-card {
  width: 100%;
  text-align: left;
  padding: 12px;
  border: 1px solid var(--dispatcher-border);
  border-radius: 12px;
  background: var(--dispatcher-surface);
  color: inherit;
  cursor: pointer;
}

.queue-card.selected {
  border-color: var(--dispatcher-border-strong);
  box-shadow: 0 10px 22px rgba(63, 54, 42, 0.08);
}

.queue-card.alert {
  border-color: #d5a7a7;
}

.queue-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.queue-card p,
.queue-card small {
  display: block;
}

.queue-card p {
  margin: 6px 0 2px;
}

.queue-card small {
  color: var(--dispatcher-muted);
}

.alert-copy {
  margin-top: 6px;
  color: var(--dispatcher-alert-text);
}

.priority-chip {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.priority-high {
  background: var(--dispatcher-alert-bg);
  color: var(--dispatcher-alert-text);
}

.priority-medium {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.priority-low {
  background: #e8efdd;
  color: #436c25;
}

.reminder-panel {
  padding: 14px;
  border-radius: 14px;
  background: #f2ece3;
}

.reminder-panel ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--dispatcher-muted);
}

.reminder-panel li + li {
  margin-top: 6px;
}

.detail-panel {
  display: flex;
  flex-direction: column;
}

.detail-head,
.detail-body {
  padding: 16px 18px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--dispatcher-border);
}

.detail-head h3,
.detail-head p {
  margin: 0;
}

.detail-head p {
  margin-top: 6px;
  color: var(--dispatcher-muted);
}

.stage-tabs {
  display: flex;
  gap: 8px;
  padding: 0 18px 16px;
  border-bottom: 1px solid var(--dispatcher-border);
}

.stage-tab {
  padding: 10px 14px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--dispatcher-muted);
  cursor: pointer;
}

.stage-tab.active {
  color: var(--dispatcher-text);
  border-bottom-color: var(--dispatcher-text);
  font-weight: 700;
}

.stage-tab.done {
  color: #55733f;
}

.stage-tab.locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-row,
.advance-panel,
.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.action-row {
  margin-bottom: 14px;
  color: var(--dispatcher-muted);
}

.primary-button,
.ghost-button {
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 12px;
  cursor: pointer;
}

.primary-button {
  border: 1px solid #2c2923;
  background: #2c2923;
  color: #faf7f0;
}

.ghost-button {
  border: 1px solid var(--dispatcher-border-strong);
  background: var(--dispatcher-surface);
  color: var(--dispatcher-text);
}

.work-order-list {
  display: grid;
  gap: 10px;
}

.work-order-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--dispatcher-border);
  border-left: 4px solid var(--dispatcher-border-strong);
  border-radius: 14px;
  background: var(--dispatcher-surface);
}

.work-order-card.pending {
  border-left-color: #bb8137;
}

.work-order-card.in_progress {
  border-left-color: #35679c;
}

.work-order-card.completed {
  border-left-color: #5f7c48;
}

.work-order-card.risk {
  border-left-color: #a54343;
}

.worker-avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #ddd4c5;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.work-order-meta {
  flex: 1;
}

.work-order-meta strong,
.work-order-meta p {
  margin: 0;
}

.work-order-meta p {
  margin-top: 4px;
  color: var(--dispatcher-muted);
}

.status-chip {
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.status-chip.pending {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.status-chip.in_progress {
  background: var(--dispatcher-active-bg);
  color: var(--dispatcher-active-text);
}

.status-chip.completed {
  background: #e8efdd;
  color: #436c25;
}

.status-chip.risk {
  background: var(--dispatcher-alert-bg);
  color: var(--dispatcher-alert-text);
}

.empty-state {
  padding: 20px;
  border: 1px dashed var(--dispatcher-border);
  border-radius: 14px;
  color: var(--dispatcher-muted);
  text-align: center;
}

.advance-panel {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f2ece3;
  color: var(--dispatcher-muted);
}

.insight-panel {
  display: grid;
  gap: 14px;
}

.side-card {
  padding: 14px 16px;
}

.worker-row,
.activity-item {
  display: grid;
  gap: 4px;
  padding: 8px 0;
}

.worker-row + .worker-row,
.activity-item + .activity-item {
  border-top: 1px solid rgba(214, 208, 196, 0.72);
}

.worker-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #5f7c48;
  display: inline-block;
}

.worker-dot.busy {
  background: #b85b4a;
}

.worker-row strong,
.worker-row small,
.activity-item strong,
.activity-item small,
.stat-row span,
.stat-row strong {
  margin: 0;
}

.worker-row small,
.activity-item small {
  color: var(--dispatcher-muted);
}

.activity-item.alert strong {
  color: var(--dispatcher-alert-text);
}

.stat-row + .stat-row {
  margin-top: 10px;
}

.order-note {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f2ece3;
  color: var(--dispatcher-muted);
  line-height: 1.6;
}

@media (max-width: 1220px) {
  .workspace-grid {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .insight-panel {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .insight-panel {
    grid-template-columns: 1fr;
  }

  .detail-head,
  .action-row,
  .advance-panel {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
