<template>
  <el-button 
    type="primary" 
    @click="$emit('click')" 
    :disabled="disabled"
    :loading="loading"
  >
    {{ loading && loadingText ? loadingText : '开始测评' }}
  </el-button>
</template>

<script setup lang="ts">
defineProps<{
  disabled?: boolean
  loading?: boolean
  loadingText?: string
}>()

defineEmits<{
  click: []
}>()
</script>