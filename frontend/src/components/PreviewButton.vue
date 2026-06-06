<template>
  <el-button 
    type="info" 
    plain
    @click="$emit('click')" 
  >
    预览效果（上线时注释此组件）
  </el-button>
</template>

<script setup lang="ts">
defineEmits<{
  click: []
}>()
</script>