<template>
  <div class="search-box">
    <el-input
      :model-value="modelValue"
      :placeholder="placeholder"
      clearable
      @update:model-value="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '搜索客户名称或订单号',
  },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.search-box {
  width: 320px;
  max-width: 100%;
}
</style>
