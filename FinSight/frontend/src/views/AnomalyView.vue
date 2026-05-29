<template>
  <div class="anomaly-view">
    <el-row :gutter="20">
      <!-- 左侧：控制 + 散点图 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>异常交易检测</span>
              <div style="display: flex; gap: 8px; align-items: center;">
                <el-date-picker v-model="dateRange" type="daterange" range-separator="-"
                  start-placeholder="开始日期" end-placeholder="结束日期" size="small"
                  value-format="YYYY-MM-DD" style="width: 240px;" />
                <el-button type="danger" size="small" @click="handleDetect" :loading="detecting">
                  执行检测
                </el-button>
              </div>
            </div>
          </template>
          <ScatterChart :scatterData="scatterData" />
        </el-card>

        <!-- 异常股票K线 -->
        <el-card v-if="anomalyKline.length > 0" shadow="hover" style="margin-top: 16px;">
          <template #header>
            <span>{{ selectedStock }} 异常标注K线</span>
          </template>
          <KlineChart :klineData="anomalyKline" :title="selectedStock + ' 异常交易日标注'" />
        </el-card>
      </el-col>

      <!-- 右侧：预警列表 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>异常预警列表</span>
              <el-tag type="danger" size="small">{{ anomalyList.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="anomalyList" stripe max-height="400" @row-click="handleAlertClick">
            <el-table-column prop="stock_code" label="代码" width="80" />
            <el-table-column prop="stock_name" label="名称" width="60" />
            <el-table-column prop="trade_date" label="日期" width="100" />
            <el-table-column prop="anomaly_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="row.anomaly_type === '疑似操纵' ? 'danger' : 'warning'" size="small">
                  {{ row.anomaly_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="anomaly_score" label="异常分" width="70" />
            <el-table-column prop="pct_change" label="涨跌幅" width="70">
              <template #default="{ row }">
                <span :style="{ color: row.pct_change > 0 ? '#ef5350' : '#26a69a' }">
                  {{ row.pct_change }}%
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 检测方法说明 -->
        <el-card shadow="hover" style="margin-top: 16px;">
          <template #header><span>检测方法</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="方法1">Isolation Forest（孤立森林）</el-descriptions-item>
            <el-descriptions-item label="原理">随机分割特征空间，异常点更容易被孤立</el-descriptions-item>
            <el-descriptions-item label="方法2">K-Means聚类</el-descriptions-item>
            <el-descriptions-item label="原理">远离聚类中心的点标记为异常模式</el-descriptions-item>
            <el-descriptions-item label="综合判定">两种方法都标记为异常 = 高置信异常</el-descriptions-item>
            <el-descriptions-item label="异常比例">{{ contamination }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 统计信息 -->
        <el-card v-if="detectResult" shadow="hover" style="margin-top: 16px;">
          <template #header><span>检测结果统计</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="检测样本数">{{ detectResult.total }}</el-descriptions-item>
            <el-descriptions-item label="异常数量">{{ detectResult.anomaly_count }}</el-descriptions-item>
            <el-descriptions-item label="异常占比">
              {{ ((detectResult.anomaly_count / detectResult.total) * 100).toFixed(1) }}%
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { detectAnomalies, getAnomalyKline } from '../api'
import ScatterChart from '../components/ScatterChart.vue'
import KlineChart from '../components/KlineChart.vue'

const dateRange = ref(null)
const detecting = ref(false)
const scatterData = ref([])
const anomalyList = ref([])
const detectResult = ref(null)
const selectedStock = ref('')
const anomalyKline = ref([])
const contamination = ref('5%')

const handleDetect = async () => {
  detecting.value = true
  try {
    const startDate = dateRange.value ? dateRange.value[0] : undefined
    const endDate = dateRange.value ? dateRange.value[1] : undefined
    const res = await detectAnomalies(startDate, endDate)
    detectResult.value = res.data
    scatterData.value = res.data.scatter_data || []
    anomalyList.value = res.data.anomalies || []
    if (res.data.methods?.isolation_forest?.contamination) {
      contamination.value = (res.data.methods.isolation_forest.contamination * 100) + '%'
    }
  } catch (e) {
    console.error(e)
  } finally {
    detecting.value = false
  }
}

const handleAlertClick = async (row) => {
  selectedStock.value = row.stock_code
  try {
    const res = await getAnomalyKline(row.stock_code)
    anomalyKline.value = res.data.kline || []
  } catch (e) {
    console.error(e)
  }
}
</script>
