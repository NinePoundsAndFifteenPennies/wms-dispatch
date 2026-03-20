<template>
  <div class="dashboard-grid">
    <section class="hero">
      <p class="kicker">Today Focus</p>
      <h3>
        <el-icon><Monitor /></el-icon>
        仓储调度运行平稳，建议优先处理高优订单
      </h3>
      <p>当前跨仓补货需求主要集中在华南区，已生成 2 条待审批调拨申请。</p>
    </section>

    <section class="metrics">
      <article class="metric-card">
        <p>
          <el-icon><Document /></el-icon>
          待接单订单
        </p>
        <h4>18</h4>
      </article>
      <article class="metric-card">
        <p>
          <el-icon><Operation /></el-icon>
          进行中工单
        </p>
        <h4>42</h4>
      </article>
      <article class="metric-card">
        <p>
          <el-icon><WarningFilled /></el-icon>
          低库存告警
        </p>
        <h4>7</h4>
      </article>
      <article class="metric-card">
        <p>
          <el-icon><CircleCheckFilled /></el-icon>
          今日完成率
        </p>
        <h4>84%</h4>
      </article>
    </section>

    <section class="panel panel-wide">
      <div class="panel-head">
        <h4>
          <el-icon><OfficeBuilding /></el-icon>
          仓库负载概览
        </h4>
        <span>实时刷新</span>
      </div>
      <div class="bars">
        <div>
          <label>华东一仓</label>
          <el-progress :percentage="78" color="#1c9c89" />
        </div>
        <div>
          <label>华南中心仓</label>
          <el-progress :percentage="61" color="#f2994a" />
        </div>
        <div>
          <label>华北中转仓</label>
          <el-progress :percentage="49" color="#3b82f6" />
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h4>
          <el-icon><BellFilled /></el-icon>
          调度提醒
        </h4>
      </div>
      <ul>
        <li>订单 OD-240319-08 超过 3 小时未接单</li>
        <li>工单 WO-00981 预计 30 分钟内超时</li>
        <li>SKU A-11 在华南仓低于阈值</li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import {
  BellFilled,
  CircleCheckFilled,
  Document,
  Monitor,
  OfficeBuilding,
  Operation,
  WarningFilled,
} from '@element-plus/icons-vue'
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: 2fr 1fr;
}

.hero {
  grid-column: 1 / -1;
  padding: 18px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(120deg, #1c9c89 0%, #117264 55%, #0a4f47 100%);
}

.kicker {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 12px;
  opacity: 0.84;
}

.hero h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 24px;
}

.hero p {
  margin: 10px 0 0;
  font-size: 14px;
  opacity: 0.9;
}

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
  margin: 8px 0 0;
  font-size: 28px;
  color: #16202a;
}

.panel {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.panel-wide {
  grid-column: 1;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-head h4 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 16px;
}

.panel-head span {
  font-size: 12px;
  color: #64748b;
}

.bars {
  display: grid;
  gap: 12px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

ul {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

li {
  color: #334155;
  font-size: 14px;
}

@media (max-width: 960px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metrics {
    grid-template-columns: 1fr;
  }

  .hero h3 {
    font-size: 20px;
  }

  .hero p {
    font-size: 13px;
  }
}
</style>
