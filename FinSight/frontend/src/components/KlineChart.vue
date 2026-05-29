<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  klineData: { type: Array, default: () => [] },
  predictions: { type: Array, default: () => [] },
  anomalyDates: { type: Set, default: () => new Set() },
  title: { type: String, default: '' },
})

const chartRef = ref(null)
let chart = null

const renderChart = () => {
  if (!chartRef.value || !props.klineData.length) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const dates = props.klineData.map(d => d.date)
  // K线数据: [open, close, low, high]
  const ohlc = props.klineData.map(d => [d.open, d.close, d.low, d.high])
  const volumes = props.klineData.map(d => d.volume || 0)

  // 预测线数据
  let predictDates = []
  let predictLine = []
  if (props.predictions.length > 0) {
    predictDates = props.predictions.map(p => p.date)
    predictLine = props.predictions.map(p => p.predicted)
    // 在K线最后一个点衔接预测线
    if (props.klineData.length > 0) {
      predictDates.unshift(dates[dates.length - 1])
      predictLine.unshift(props.klineData[props.klineData.length - 1]?.close)
    }
  }

  // 异常标注
  const markPoints = []
  props.klineData.forEach((d, i) => {
    if (d.is_anomaly) {
      markPoints.push({
        name: '异常',
        coord: [d.date, d.high],
        value: '!',
        itemStyle: { color: '#ff4757' },
      })
    }
  })

  const series = [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      itemStyle: {
        color: '#ef5350',      // 阳线颜色（涨）
        color0: '#26a69a',     // 阴线颜色（跌）
        borderColor: '#ef5350',
        borderColor0: '#26a69a',
      },
      markPoint: markPoints.length > 0 ? {
        data: markPoints,
        symbol: 'pin',
        symbolSize: 30,
        label: { show: true, fontSize: 12, color: '#fff' },
      } : undefined,
    },
    {
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes,
      itemStyle: {
        color: (params) => {
          const idx = params.dataIndex
          return ohlc[idx] && ohlc[idx][1] >= ohlc[idx][0] ? '#ef5350' : '#26a69a'
        }
      },
    },
  ]

  // 添加预测线
  if (predictLine.length > 0) {
    series.push({
      name: 'LSTM预测',
      type: 'line',
      data: predictDates.map((d, i) => [d, predictLine[i]]),
      lineStyle: { type: 'dashed', color: '#ffa502', width: 2 },
      itemStyle: { color: '#ffa502' },
      symbol: 'circle',
      symbolSize: 6,
    })
  }

  chart.setOption({
    title: {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14 },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['K线', 'LSTM预测'].filter((_, i) => i === 0 || predictLine.length > 0),
      top: 30,
    },
    grid: [
      { left: '10%', right: '8%', top: 60, height: '55%' },
      { left: '10%', right: '8%', top: '75%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, boundaryGap: true, axisLabel: { fontSize: 10 } },
      { type: 'category', data: dates, gridIndex: 1, boundaryGap: true, axisLabel: { show: false } },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { type: 'dashed' } } },
      { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false } },
    ],
    series,
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, bottom: 5 },
    ],
  }, true)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => [props.klineData, props.predictions], renderChart, { deep: true })
</script>
