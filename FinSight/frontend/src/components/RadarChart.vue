<template>
  <div ref="chartRef" style="width: 100%; height: 350px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  factors: { type: Object, default: () => ({}) },
  stockName: { type: String, default: '' },
  compositeScore: { type: Number, default: 0 },
})

const chartRef = ref(null)
let chart = null

const renderChart = () => {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const indicator = Object.keys(props.factors).map(name => ({
    name,
    max: 3,  // Z-Score通常在-3到3之间
  }))

  const values = Object.values(props.factors)

  chart.setOption({
    title: {
      text: props.stockName ? `${props.stockName} 因子雷达` : '因子雷达图',
      subtext: props.compositeScore ? `综合评分: ${props.compositeScore.toFixed(2)}` : '',
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: {},
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#333', fontSize: 13 },
      splitArea: { areaStyle: { color: ['rgba(22, 199, 154, 0.05)', 'rgba(22, 199, 154, 0.1)'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: props.stockName || '当前股票',
        areaStyle: { color: 'rgba(22, 199, 154, 0.3)' },
        lineStyle: { color: '#16c79a', width: 2 },
        itemStyle: { color: '#16c79a' },
      }],
    }],
  }, true)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => props.factors, renderChart, { deep: true })
</script>
