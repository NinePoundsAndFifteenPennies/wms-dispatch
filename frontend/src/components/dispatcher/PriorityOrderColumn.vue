<template>
  <section class="priority-column">
    <header class="column-head">
      <h4>{{ title }}</h4>
      <el-select :model-value="sortOrder" size="small" style="width: 120px" @change="$emit('sort-change', $event)">
        <el-option label="时间降序" value="desc" />
        <el-option label="时间升序" value="asc" />
      </el-select>
    </header>

    <div ref="scrollRef" class="column-scroll" @scroll="handleScroll">
      <div :style="{ height: `${topSpacer}px` }" />

      <div v-for="item in visibleItems" :key="item.id" class="card-wrap">
        <slot :item="item" />
      </div>

      <div :style="{ height: `${bottomSpacer}px` }" />
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  items: {
    type: Array,
    default: () => [],
  },
  sortOrder: {
    type: String,
    default: 'desc',
  },
  itemHeight: {
    type: Number,
    default: 120,
  },
  overscan: {
    type: Number,
    default: 4,
  },
})

defineEmits(['sort-change'])

const scrollRef = ref(null)
const scrollTop = ref(0)
const viewportHeight = ref(0)

const visibleCount = computed(() => Math.ceil((viewportHeight.value || 1) / props.itemHeight))
const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.overscan))
const endIndex = computed(() =>
  Math.min(props.items.length, startIndex.value + visibleCount.value + props.overscan * 2)
)
const visibleItems = computed(() => props.items.slice(startIndex.value, endIndex.value))
const topSpacer = computed(() => startIndex.value * props.itemHeight)
const bottomSpacer = computed(() => Math.max(0, (props.items.length - endIndex.value) * props.itemHeight))

function handleScroll(event) {
  const target = event.target
  scrollTop.value = target.scrollTop
  viewportHeight.value = target.clientHeight
}
</script>

<style scoped>
.priority-column {
  min-width: 0;
  border: 1px solid var(--dispatcher-border);
  border-radius: 14px;
  background: rgba(255, 253, 249, 0.9);
  display: flex;
  flex-direction: column;
}

.column-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid var(--dispatcher-border);
}

.column-head h4 {
  margin: 0;
  font-size: 14px;
}

.column-scroll {
  height: calc(100vh - 280px);
  min-height: 260px;
  overflow: auto;
  padding: 8px;
}

.card-wrap {
  height: 112px;
  margin-bottom: 8px;
}
</style>
