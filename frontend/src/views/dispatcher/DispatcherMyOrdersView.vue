<template>
  <div class="dispatcher-orders-page">
    <section class="page-head">
      <h3>我的订单</h3>
      <OrderSearchBox v-model="search" />
    </section>

    <section class="columns-grid" v-loading="loading">
      <PriorityOrderColumn
        title="高优先级"
        :items="grouped.high"
        :sort-order="sortOrder.high"
        @sort-change="sortOrder.high = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>

      <PriorityOrderColumn
        title="中优先级"
        :items="grouped.medium"
        :sort-order="sortOrder.medium"
        @sort-change="sortOrder.medium = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>

      <PriorityOrderColumn
        title="低优先级"
        :items="grouped.low"
        :sort-order="sortOrder.low"
        @sort-change="sortOrder.low = $event"
      >
        <template #default="{ item }">
          <DispatcherOrderCard :order="item" @click="openDetail(item.id)" />
        </template>
      </PriorityOrderColumn>
    </section>

  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { dispatcherOrdersApi } from '../../api/dispatcher/orders'
import DispatcherOrderCard from '../../components/dispatcher/DispatcherOrderCard.vue'
import PriorityOrderColumn from '../../components/dispatcher/PriorityOrderColumn.vue'
import OrderSearchBox from '../../components/shared/OrderSearchBox.vue'

const loading = ref(false)
const orders = ref([])
const search = ref('')
const router = useRouter()
let searchTimer = null

const sortOrder = reactive({
  high: 'desc',
  medium: 'desc',
  low: 'desc',
})

const filtered = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return orders.value
  return orders.value.filter(
    (item) =>
      String(item.order_no).toLowerCase().includes(keyword) ||
      String(item.customer_name).toLowerCase().includes(keyword)
  )
})

const grouped = computed(() => {
  const groups = { high: [], medium: [], low: [] }
  for (const item of filtered.value) {
    if (groups[item.priority]) groups[item.priority].push(item)
  }
  for (const key of ['high', 'medium', 'low']) {
    groups[key].sort((a, b) => {
      const diff = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
      return sortOrder[key] === 'asc' ? diff : -diff
    })
  }
  return groups
})

async function fetchOrders() {
  loading.value = true
  try {
    const res = await dispatcherOrdersApi.getMyOrders({ search: search.value || undefined })
    orders.value = res.data.items || []
  } finally {
    loading.value = false
  }
}

function openDetail(orderId) {
  router.push({ name: 'dispatcher-my-order-detail', params: { orderId } })
}

onMounted(fetchOrders)
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchOrders()
  }, 250)
})
onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.dispatcher-orders-page {
  display: grid;
  gap: 12px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.page-head h3 {
  margin: 0;
}

.columns-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 980px) {
  .columns-grid {
    grid-template-columns: 1fr;
  }
}
</style>
