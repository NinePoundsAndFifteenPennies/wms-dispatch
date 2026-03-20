<template>
  <div class="dispatcher-page">
    <section class="page-hero">
      <p class="section-kicker">Transfer Requests</p>
      <h2>调拨请求展示调度员的 mock 审批流观察视角</h2>
      <p>本页不提交真实调拨单，只模拟查看待审批、运输中与已入库状态。</p>
    </section>

    <section class="transfer-list">
      <article v-for="item in dispatcherTransfersMock" :key="item.code" class="transfer-card">
        <div class="transfer-head">
          <div>
            <p class="section-kicker">{{ item.code }}</p>
            <h3>{{ item.product }} / {{ item.sku }}</h3>
          </div>
          <span class="status-chip" :class="statusClass(item.status)">{{ item.status }}</span>
        </div>

        <div class="transfer-meta">
          <div>
            <span>来源仓</span>
            <strong>{{ item.fromWarehouse }}</strong>
          </div>
          <div>
            <span>目标仓</span>
            <strong>{{ item.toWarehouse }}</strong>
          </div>
          <div>
            <span>数量</span>
            <strong>{{ item.qty }}</strong>
          </div>
          <div>
            <span>创建时间</span>
            <strong>{{ item.createdAt }}</strong>
          </div>
        </div>

        <p class="reason-copy">{{ item.reason }}</p>

        <div class="transfer-actions">
          <button type="button" class="ghost-button">查看详情</button>
          <button type="button" class="primary-button">跟进入库</button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { dispatcherTransfersMock } from '../../mock/dispatcher'

function statusClass(status) {
  return {
    待审批: 'status-pending',
    审批通过: 'status-active',
    运输中: 'status-active',
    已入库: 'status-done',
  }[status]
}
</script>

<style scoped>
.dispatcher-page {
  display: grid;
  gap: 14px;
}

.page-hero,
.transfer-card {
  border: 1px solid var(--dispatcher-border);
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.88);
}

.page-hero {
  padding: 18px 20px;
}

.page-hero h2,
.page-hero p,
.section-kicker,
.transfer-head h3 {
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

.transfer-list {
  display: grid;
  gap: 12px;
}

.transfer-card {
  padding: 16px 18px;
}

.transfer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.transfer-head h3 {
  margin-top: 6px;
  font-size: 20px;
}

.transfer-meta {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.transfer-meta span,
.transfer-meta strong {
  display: block;
}

.transfer-meta span {
  font-size: 12px;
  color: var(--dispatcher-soft);
}

.transfer-meta strong {
  margin-top: 6px;
}

.reason-copy {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f2ece3;
  color: var(--dispatcher-muted);
  line-height: 1.6;
}

.transfer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.status-chip {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-pending {
  background: var(--dispatcher-pending-bg);
  color: var(--dispatcher-pending-text);
}

.status-active {
  background: var(--dispatcher-active-bg);
  color: var(--dispatcher-active-text);
}

.status-done {
  background: #e8efdd;
  color: #436c25;
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

@media (max-width: 900px) {
  .transfer-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .transfer-actions,
  .transfer-head {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 560px) {
  .transfer-meta {
    grid-template-columns: 1fr;
  }
}
</style>
