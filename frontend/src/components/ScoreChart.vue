<template>
  <div class="chart-container">
    <div ref="chartRef" class="chart"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  scores: {
    task_completion?: number
    process_adherence?: number
    constraint_compliance?: number
    naturalness?: number
    strategy_adaptation?: number
  }
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const scoreLabels: Record<string, string> = {
  task_completion: '任务达成度',
  process_adherence: '流程完整性',
  constraint_compliance: '约束遵循度',
  naturalness: '沟通自然度',
  strategy_adaptation: '策略灵活性'
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  const keys = Object.keys(props.scores)
  const values = keys.map(key => props.scores[key as keyof typeof props.scores] || 0)
  const labels = keys.map(key => scoreLabels[key] || key)
  
  const option: echarts.EChartsOption = {
    title: {
      text: '各维度得分',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: unknown) => {
        const param = params as Array<{ axisValue: string; value: number }>
        if (param.length > 0) {
          return `${param[0].axisValue}: ${param[0].value.toFixed(1)}分`
        }
        return ''
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        interval: 0,
        rotate: 15,
        fontSize: 12,
        color: '#666'
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}分'
      },
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '得分',
        type: 'bar',
        data: values,
        barWidth: '50%',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#5a6fd6' },
              { offset: 1, color: '#6a4190' }
            ])
          }
        }
      }
    ]
  }
  
  chartInstance.setOption(option)
}

function updateChart() {
  if (!chartInstance) {
    if (Object.keys(props.scores).length > 0) {
      initChart()
    }
    return
  }

  const keys = Object.keys(props.scores)
  const values = keys.map(key => props.scores[key as keyof typeof props.scores] || 0)
  const labels = keys.map(key => scoreLabels[key] || key)

  chartInstance.setOption({
    xAxis: {
      data: labels
    },
    series: [
      {
        data: values
      }
    ]
  })
}

onMounted(() => {
  initChart()
  
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

watch(() => props.scores, () => {
  updateChart()
}, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 300px;
}

.chart {
  width: 100%;
  height: 100%;
}
</style>