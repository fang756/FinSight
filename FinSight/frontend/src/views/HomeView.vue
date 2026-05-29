<template>
  <div class="home">
    <h2 style="margin: 0 0 20px; color: #1a1a2e;">FinSight - A股智能投研分析平台</h2>

    <!-- 数据状态 -->
    <el-card shadow="hover" style="margin-bottom: 20px;">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>数据状态</span>
          <el-button type="primary" size="small" @click="handleInitData" :loading="initLoading">
            初始化数据
          </el-button>
        </div>
      </template>
      <el-row :gutter="20" v-if="dataStatus">
        <el-col :span="6">
          <el-statistic title="股票数量" :value="dataStatus.stock_count" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="行情记录" :value="dataStatus.daily_count" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="数据起始" :value="dataStatus.date_range?.start || '-'" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="数据截止" :value="dataStatus.date_range?.end || '-'" />
        </el-col>
      </el-row>
      <el-empty v-else description="请先点击「初始化数据」采集A股数据" />
    </el-card>

    <!-- 市场概况 -->
    <el-row :gutter="20" v-if="marketStats" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-card shadow="hover" class="market-card">
          <el-statistic title="上涨数量" :value="marketStats.up_count">
            <template #suffix>
              <span style="color: #ef5350; font-size: 12px;">只</span>
            </template>
          </el-statistic>
          <div class="stock-list" v-if="marketStats.up_stocks?.length">
            <div
              v-for="s in marketStats.up_stocks"
              :key="s.ts_code"
              class="stock-item up"
              @click="goToFactor(s.ts_code)"
            >
              <span class="stock-name">{{ s.name }}</span>
              <span class="stock-code">{{ s.ts_code }}</span>
              <span class="stock-pct">+{{ s.pct_chg }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="market-card">
          <el-statistic title="下跌数量" :value="marketStats.down_count">
            <template #suffix>
              <span style="color: #26a69a; font-size: 12px;">只</span>
            </template>
          </el-statistic>
          <div class="stock-list" v-if="marketStats.down_stocks?.length">
            <div
              v-for="s in marketStats.down_stocks"
              :key="s.ts_code"
              class="stock-item down"
              @click="goToFactor(s.ts_code)"
            >
              <span class="stock-name">{{ s.name }}</span>
              <span class="stock-code">{{ s.ts_code }}</span>
              <span class="stock-pct">{{ s.pct_chg }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="market-card">
          <el-statistic title="平均涨跌幅" :value="marketStats.avg_change">
            <template #suffix>
              <span style="font-size: 12px;">%</span>
            </template>
          </el-statistic>
          <div class="stock-list" v-if="marketStats.up_stocks?.length || marketStats.down_stocks?.length">
            <div class="stock-list-header">涨幅榜 TOP5</div>
            <div
              v-for="s in marketStats.up_stocks?.slice(0, 5)"
              :key="s.ts_code"
              class="stock-item up"
              @click="goToFactor(s.ts_code)"
            >
              <span class="stock-name">{{ s.name }}</span>
              <span class="stock-code">{{ s.ts_code }}</span>
              <span class="stock-pct">+{{ s.pct_chg }}%</span>
            </div>
            <div class="stock-list-header" style="margin-top: 8px;">跌幅榜 TOP5</div>
            <div
              v-for="s in marketStats.down_stocks?.slice(0, 5)"
              :key="s.ts_code"
              class="stock-item down"
              @click="goToFactor(s.ts_code)"
            >
              <span class="stock-name">{{ s.name }}</span>
              <span class="stock-code">{{ s.ts_code }}</span>
              <span class="stock-pct">{{ s.pct_chg }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 功能模块入口 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="module-card" @click="$router.push('/factor')">
          <div class="module-icon" style="background: linear-gradient(135deg, #16c79a, #0f9b6e);">&#x1F4C8;</div>
          <h3>因子选股</h3>
          <p>多因子模型评分，雷达图可视化，智能筛选Top股票</p>
          <el-tag type="success" size="small">分类 + 特征工程</el-tag>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="module-card" @click="$router.push('/predict')">
          <div class="module-icon" style="background: linear-gradient(135deg, #ffa502, #e67e22);">&#x1F4CA;</div>
          <h3>趋势预测</h3>
          <p>LSTM深度学习模型，预测未来价格走势与置信度</p>
          <el-tag type="warning" size="small">回归 + 深度学习</el-tag>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="module-card" @click="$router.push('/anomaly')">
          <div class="module-icon" style="background: linear-gradient(135deg, #ff4757, #c0392b);">&#x26A0;</div>
          <h3>异常检测</h3>
          <p>Isolation Forest + K-Means双引擎，识别异常交易</p>
          <el-tag type="danger" size="small">异常检测 + 聚类</el-tag>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDataStatus, initData, getMarketIndices } from '../api'

const router = useRouter()
const dataStatus = ref(null)
const marketStats = ref(null)
const initLoading = ref(false)

const goToFactor = (tsCode) => {
  router.push({ path: '/factor', query: { code: tsCode } })
}

onMounted(async () => {
  try {
    const res = await getDataStatus()
    dataStatus.value = res.data
  } catch (e) {
    // 数据库可能还没初始化
  }

  try {
    const res = await getMarketIndices()
    marketStats.value = res.data.market_stats
  } catch (e) {
    // 忽略
  }
})

const handleInitData = async () => {
  initLoading.value = true
  try {
    const res = await initData()
    if (res.data.success) {
      ElMessage.success('数据初始化完成')
      const statusRes = await getDataStatus()
      dataStatus.value = statusRes.data
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('初始化失败: ' + e.message)
  } finally {
    initLoading.value = false
  }
}
</script>

<style scoped>
.module-card {
  cursor: pointer;
  text-align: center;
  transition: transform 0.2s;
}
.module-card:hover {
  transform: translateY(-4px);
}
.module-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin: 0 auto 12px;
  color: #fff;
}
.module-card h3 {
  margin: 8px 0;
  color: #1a1a2e;
}
.module-card p {
  color: #888;
  font-size: 13px;
  margin: 4px 0 12px;
}

.market-card :deep(.el-card__body) {
  padding: 16px;
}
.stock-list {
  margin-top: 12px;
  max-height: 280px;
  overflow-y: auto;
}
.stock-list-header {
  font-size: 11px;
  color: #999;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 4px;
}
.stock-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.stock-item:hover {
  background: #f5f7fa;
}
.stock-item .stock-name {
  flex: 1;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stock-item .stock-code {
  color: #999;
  font-size: 11px;
  margin: 0 8px;
  min-width: 60px;
  text-align: center;
}
.stock-item .stock-pct {
  font-weight: 600;
  font-size: 12px;
  min-width: 52px;
  text-align: right;
}
.stock-item.up .stock-pct {
  color: #ef5350;
}
.stock-item.down .stock-pct {
  color: #26a69a;
}
</style>
