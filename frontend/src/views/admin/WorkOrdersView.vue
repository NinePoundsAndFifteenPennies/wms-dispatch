<template>
  <div class="work-order-page">
    <header>
      <h3>工单执行看板</h3>
      <p>按阶段和状态跟踪工单，及时处理堵点。</p>
    </header>

    <section class="columns">
      <article class="column">
        <h4>
          <el-icon><Clock /></el-icon>
          待开始
        </h4>
        <div class="ticket">
          <el-icon><Box /></el-icon>
          WO-00986 · 拣货 · 华南中心仓
        </div>
        <div class="ticket">
          <el-icon><Box /></el-icon>
          WO-00987 · 拣货 · 华东一仓
        </div>
      </article>

      <article class="column">
        <h4>
          <el-icon><Loading /></el-icon>
          进行中
        </h4>
        <div class="ticket is-hot">
          <el-icon><WarningFilled /></el-icon>
          WO-00981 · 备货 · 截止 30 分钟
        </div>
        <div class="ticket">
          <el-icon><Box /></el-icon>
          WO-00982 · 发货 · 截止 2 小时
        </div>
      </article>

      <article class="column">
        <h4>
          <el-icon><CircleCheckFilled /></el-icon>
          已完成
        </h4>
        <div class="ticket">
          <el-icon><Box /></el-icon>
          WO-00974 · 拣货
        </div>
        <div class="ticket">
          <el-icon><Box /></el-icon>
          WO-00975 · 备货
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { Box, CircleCheckFilled, Clock, Loading, WarningFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
header {
  margin-bottom: 12px;
}

h3 {
  margin: 0;
  font-size: 22px;
}

p {
  margin: 6px 0 0;
  color: #475569;
}

.columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.column {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.column h4 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 10px;
  font-size: 14px;
  color: #334155;
}

.ticket {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid #d9e2ec;
  font-size: 13px;
  background: #f8fbff;
}

.ticket.is-hot {
  border-color: #f4b47a;
  background: #fff5ec;
}

@media (max-width: 960px) {
  .columns {
    grid-template-columns: 1fr;
  }
}
</style>
