import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { dispatcherOrdersApi } from '../api/dispatcher/orders'

export const useDispatcherStore = defineStore('dispatcher', () => {
  const summary = ref({
    warehouse_id: null,
    warehouse_name: '',
    pending_count: 0,
    my_orders_count: 0,
    my_in_progress_count: 0,
    my_completed_count: 0,
    my_cancelled_count: 0,
  })

  const loading = ref(false)

  async function refreshSummary() {
    loading.value = true
    try {
      const res = await dispatcherOrdersApi.getDashboardSummary()
      summary.value = { ...summary.value, ...(res.data || {}) }
    } catch {
      summary.value = { ...summary.value }
    } finally {
      loading.value = false
    }
  }

  const statusBadges = computed(() => [
    { key: 'pending', label: '待接单', value: summary.value.pending_count, tone: 'pending' },
    { key: 'active', label: '进行中', value: summary.value.my_in_progress_count, tone: 'active' },
    { key: 'done', label: '已完成', value: summary.value.my_completed_count, tone: 'done' },
  ])

  return {
    summary,
    loading,
    statusBadges,
    refreshSummary,
  }
})
