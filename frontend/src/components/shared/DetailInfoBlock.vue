<template>
  <el-card shadow="never" class="detail-info-block">
    <template #header>
      <strong>{{ title }}</strong>
    </template>
    <slot />
  </el-card>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.detail-info-block {
  margin-top: 12px;
}
</style>
