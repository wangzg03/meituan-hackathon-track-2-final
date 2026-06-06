<template>
  <div v-if="status" class="task-status-message">
    {{ status }}
  </div>
</template>

<script setup lang="ts">
defineProps<{
  status?: string
}>()
</script>

<style scoped>
.task-status-message {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  height: 32px;
  background-color: #f0f9eb;
  border: 1px solid #67c23a;
  border-radius: 4px;
  color: #67c23a;
  font-weight: 500;
  box-sizing: border-box;
}
</style>