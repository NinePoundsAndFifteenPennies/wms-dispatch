<template>
  <div class="orders-page">
    <section class="toolbar">
      <div>
        <h3>订单中枢</h3>
        <p>聚合查看接单状态、优先级和责任调度员。</p>
      </div>
      <div class="actions">
        <el-button>
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="primary">
          <el-icon><Plus /></el-icon>
          新建订单
        </el-button>
      </div>
    </section>

    <section class="stats">
      <div class="stat-item">
        <span><el-icon><Tickets /></el-icon>待接单</span>
        <b>18</b>
      </div>
      <div class="stat-item">
        <span><el-icon><ShoppingCartFull /></el-icon>进行中</span>
        <b>27</b>
      </div>
      <div class="stat-item">
        <span><el-icon><Timer /></el-icon>接单超时风险</span>
        <b>4</b>
      </div>
    </section>

    <el-card class="table-card" shadow="never">
      <el-table :data="mockRows" stripe>
        <el-table-column prop="orderNo" label="订单号" width="180" />
        <el-table-column prop="warehouse" label="仓库" width="140" />
        <el-table-column prop="priority" label="优先级" width="110" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="dispatcher" label="责任调度员" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { Download, Plus, ShoppingCartFull, Tickets, Timer } from '@element-plus/icons-vue'

const mockRows = [
  {
    orderNo: 'OD-240319-08',
    warehouse: '华南中心仓',
    priority: '高',
    status: '待接单',
    dispatcher: '-',
  },
  {
    orderNo: 'OD-240319-06',
    warehouse: '华东一仓',
    priority: '中',
    status: '进行中',
    dispatcher: '周伟',
  },
  {
    orderNo: 'OD-240319-02',
    warehouse: '华北中转仓',
    priority: '低',
    status: '进行中',
    dispatcher: '王琳',
  },
]
</script>

<style scoped>
.orders-page {
  display: grid;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

h3 {
  margin: 0;
  font-size: 22px;
}

p {
  margin: 6px 0 0;
  color: #475569;
}

.actions {
  display: flex;
  gap: 8px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stat-item {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.stat-item span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
}

.stat-item b {
  display: block;
  margin-top: 6px;
  font-size: 26px;
  color: #16202a;
}

.table-card {
  border-radius: 12px;
}

@media (max-width: 860px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .stats {
    grid-template-columns: 1fr;
  }
}
</style>
