<template>
  <section class="panel">
    <div class="panel-head">
      <h4>
        <el-icon><BellFilled /></el-icon>
        订单运营预警
      </h4>
    </div>
    <div v-if="items.length" class="alerts-scroll" @scroll="handleScroll">
      <ul class="alerts">
      <li
        v-for="(item, index) in visibleItems"
        :key="`${item.alert_type}-${index}`"
        role="button"
        tabindex="0"
        @click="emit('alert-click', item)"
        @keyup.enter="emit('alert-click', item)"
      >
        {{ item.message }}
      </li>
      </ul>
    </div>
    <div v-if="items.length" class="actions">
      <el-button text type="primary" :disabled="visibleCount >= items.length" @click="loadMore">
        {{ visibleCount >= items.length ? '已加载全部' : '加载更多' }}
      </el-button>
    </div>
    <el-empty v-else description="当前无运营预警" :image-size="70" />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BellFilled } from '@element-plus/icons-vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['alert-click'])

const visibleCount = ref(6)
const timerRef = ref(null)

const visibleItems = computed(() => props.items.slice(0, visibleCount.value))

function loadMore(step = 3) {
  visibleCount.value = Math.min(props.items.length, visibleCount.value + step)
}

function handleScroll(event) {
  const target = event?.target
  if (!target) return
  if (target.scrollTop + target.clientHeight >= target.scrollHeight - 12) {
    loadMore(2)
  }
}

function startAutoLoading() {
  stopAutoLoading()
  timerRef.value = setInterval(() => {
    if (visibleCount.value < props.items.length) {
      loadMore(1)
    }
  }, 5000)
}

function stopAutoLoading() {
  if (timerRef.value) {
    clearInterval(timerRef.value)
    timerRef.value = null
  }
}

watch(
  () => props.items,
  () => {
    visibleCount.value = Math.min(6, props.items.length || 0)
    startAutoLoading()
  },
  { immediate: true },
)

onMounted(startAutoLoading)
onBeforeUnmount(stopAutoLoading)
</script>

<style scoped>
.panel {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #d8e1eb;
  background: #ffffff;
}

.panel-head h4 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 16px;
}

.alerts-scroll {
  height: 220px;
  overflow-y: auto;
  padding-right: 4px;
}

.alerts {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.alerts li {
  color: #334155;
  font-size: 14px;
  cursor: pointer;
}

.alerts li:hover {
  color: #0f766e;
  text-decoration: underline;
}

.actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
</style>
