<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  scatterData: { type: Array, default: () => [] },
  title: { type: String, default: '异常检测散点图' },
})

const chartRef = ref(null)
let chart = null

const renderChart = () => {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  // 正常点和异常点分开
  const normal = props.scatterData.filter(d => !d.is_anomaly)
  const anomaly = props.scatterData.filter(d => d.is_anomaly)

  chart.setOption({
    title: {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        return `${p.data[3]}<br/>
          换手率: ${p.data[0]}%<br/>
          涨跌幅: ${p.data[1]}%<br/>
          异常分: ${p.data[2]?.toFixed(2) || '-'}`
      },
    },
    legend: {
      data: ['正常', '异常'],
      top: 30,
    },
    grid: { left: '10%', right: '10%', top: 60, bottom: 40 },
    xAxis: {
      name: '换手率(%)',
      nameLocation: 'middle',
      nameGap: 25,
    },
    yAxis: {
      name: '涨跌幅(%)',
      nameLocation: 'middle',
      nameGap: 40,
    },
    series: [
      {
        name: '正常',
        type: 'scatter',
        data: normal.map(d => [d.turnover, d.pct_change, d.anomaly_score, d.stock_code]),
        symbolSize: 6,
        itemStyle: { color: '#ccc', opacity: 0.5 },
      },
      {
        name: '异常',
        type: 'scatter',
        data: anomaly.map(d => [d.turnover, d.pct_change, d.anomaly_score, d.stock_code]),
        symbolSize: 12,
        itemStyle: { color: '#ff4757' },
      },
    ],
  }, true)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => props.scatterData, renderChart, { deep: true })
</script>
