<template>
  <div class="predict-view">
    <el-row :gutter="20">
      <!-- 左侧：控制面板 -->
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>LSTM预测控制</span></template>

          <el-form label-position="top">
            <el-form-item label="选择股票">
              <el-select
                v-model="stockCode"
                filterable
                placeholder="搜索股票名称或代码"
                style="width: 100%;"
                @change="loadKline"
              >
                <el-option
                  v-for="s in stockList"
                  :key="s.ts_code"
                  :label="`${s.name}（${s.ts_code}）`"
                  :value="s.ts_code"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="训练轮数(Epochs)">
              <el-slider v-model="epochs" :min="10" :max="200" :step="10" show-input />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleTrain" :loading="training" style="width: 100%;">
                训练模型
              </el-button>
            </el-form-item>
            <el-form-item label="预测天数">
              <el-select v-model="predictDays" style="width: 100%;">
                <el-option :value="3" label="3天" />
                <el-option :value="5" label="5天" />
                <el-option :value="10" label="10天" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button @click="handlePredict" :loading="predicting" style="width: 100%;">
                预测未来价格
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 已训练模型 -->
          <el-divider>已训练模型</el-divider>
          <el-tag v-for="m in trainedModels" :key="m.stock_code"
            style="margin: 4px; cursor: pointer;"
            @click="stockCode = m.stock_code"
          >
            {{ m.stock_code }}
          </el-tag>
        </el-card>

        <!-- 评估指标 -->
        <el-card v-if="metrics" shadow="hover" style="margin-top: 16px;">
          <template #header><span>模型评估</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="MAE">{{ metrics.mae }}</el-descriptions-item>
            <el-descriptions-item label="RMSE">{{ metrics.rmse }}</el-descriptions-item>
            <el-descriptions-item label="方向准确率">
              <el-tag :type="metrics.direction_accuracy > 0.5 ? 'success' : 'danger'">
                {{ (metrics.direction_accuracy * 100).toFixed(1) }}%
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最终Loss">{{ metrics.final_loss }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 右侧：K线图 + 预测线 -->
      <el-col :span="18">
        <el-card shadow="hover">
          <template #header>
            <span>{{ selectedStockName || stockCode }} K线 + LSTM预测</span>
          </template>
          <KlineChart
            :klineData="klineData"
            :predictions="predictionLineData"
            :title="(selectedStockName || stockCode) + ' 价格走势与预测'"
          />
        </el-card>

        <!-- 未来预测结果 -->
        <el-card v-if="futurePredictions.length > 0" shadow="hover" style="margin-top: 16px;">
          <template #header><span>未来价格预测</span></template>
          <el-table :data="futurePredictions" stripe>
            <el-table-column prop="day" label="第N天" width="100" />
            <el-table-column prop="predicted_price" label="预测价格" width="150">
              <template #default="{ row }">
                <span style="color: #ffa502; font-weight: 600;">{{ row.predicted_price }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 训练日志 -->
        <el-card v-if="trainMessage" shadow="hover" style="margin-top: 16px;">
          <template #header><span>训练日志</span></template>
          <el-alert :title="trainMessage" :type="trainSuccess ? 'success' : 'error'" show-icon />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getKline, trainPredict, getPredictResult, getTrainedModels, getStockList } from '../api'
import KlineChart from '../components/KlineChart.vue'

const stockCode = ref('')
const stockList = ref([])
const epochs = ref(50)
const predictDays = ref(5)
const training = ref(false)
const predicting = ref(false)
const klineData = ref([])
const backtestPredictions = ref([])  // 训练后的回测预测数据（不在训练后立即显示）
const predictionLineData = ref([])
const futurePredictions = ref([])
const metrics = ref(null)
const trainedModels = ref([])
const trainMessage = ref('')
const trainSuccess = ref(false)

const selectedStockName = computed(() => {
  const stock = stockList.value.find(s => s.ts_code === stockCode.value)
  return stock ? stock.name : ''
})

const loadKline = async () => {
  // 切换股票时清空所有预测数据
  predictionLineData.value = []
  backtestPredictions.value = []
  futurePredictions.value = []
  metrics.value = null
  trainMessage.value = ''
  try {
    const res = await getKline(stockCode.value, 120)
    klineData.value = res.data.kline || []
  } catch (e) {
    console.error(e)
  }
}

const handleTrain = async () => {
  if (!stockCode.value) return
  training.value = true
  trainMessage.value = ''
  metrics.value = null
  predictionLineData.value = []
  backtestPredictions.value = []
  futurePredictions.value = []
  try {
    const res = await trainPredict(stockCode.value, epochs.value)
    trainSuccess.value = res.data.success
    trainMessage.value = res.data.message
    if (res.data.success) {
      metrics.value = res.data.metrics
      // 保存回测预测数据，但不立即显示，等用户点击"预测未来价格"后再显示
      backtestPredictions.value = res.data.predictions || []
      loadModels()
    }
  } catch (e) {
    trainMessage.value = '训练失败: ' + e.message
    trainSuccess.value = false
  } finally {
    training.value = false
  }
}

const handlePredict = async () => {
  if (!stockCode.value) return
  predicting.value = true
  try {
    const res = await getPredictResult(stockCode.value, predictDays.value)
    if (res.data.success) {
      futurePredictions.value = res.data.predictions || []
      // 预测成功后，同时显示回测预测线
      predictionLineData.value = backtestPredictions.value
    } else {
      ElMessage.warning(res.data.message)
    }
  } catch (e) {
    ElMessage.error('预测失败: ' + e.message)
  } finally {
    predicting.value = false
  }
}

const loadModels = async () => {
  try {
    const res = await getTrainedModels()
    trainedModels.value = res.data.models || []
  } catch (e) {
    console.error(e)
  }
}

const loadStockList = async () => {
  try {
    const res = await getStockList()
    stockList.value = res.data.stocks || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadStockList()
  loadModels()
})
</script>
