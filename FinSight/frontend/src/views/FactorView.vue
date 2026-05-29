<template>
  <div class="factor-view">
    <el-row :gutter="20">
      <!-- 左侧：因子雷达图 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <span>因子雷达图</span>
          </template>
          <el-select
            v-model="searchCode"
            filterable
            placeholder="搜索股票名称或代码"
            style="margin-bottom: 12px; width: 100%;"
            @change="loadRadar"
          >
            <el-option
              v-for="s in stockList"
              :key="s.ts_code"
              :label="`${s.name}（${s.ts_code}）`"
              :value="s.ts_code"
            />
          </el-select>
          <RadarChart
            v-if="radarData.factors"
            :factors="radarData.factors"
            :stockName="radarData.name || radarData.ts_code"
            :compositeScore="radarData.composite_score || 0"
          />
          <el-empty v-else description="选择股票查看因子雷达" />
        </el-card>
      </el-col>

      <!-- 右侧：因子排名表 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>因子排名</span>
              <div style="display: flex; gap: 8px;">
                <el-select v-model="industryFilter" placeholder="行业筛选" clearable size="small" style="width: 140px;">
                  <el-option v-for="s in sectors" :key="s.industry" :label="s.industry" :value="s.industry" />
                </el-select>
                <el-button type="primary" size="small" @click="loadRanking" :loading="rankingLoading">
                  刷新排名
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="ranking" stripe style="width: 100%;" max-height="500" @row-click="handleRowClick">
            <el-table-column prop="stock_code" label="代码" width="90" />
            <el-table-column prop="stock_name" label="名称" width="80" />
            <el-table-column prop="industry" label="行业" width="80" />
            <el-table-column prop="composite_score" label="综合评分" width="100" sortable>
              <template #default="{ row }">
                <span :style="{ color: row.composite_score > 0 ? '#ef5350' : '#26a69a', fontWeight: 600 }">
                  {{ row.composite_score?.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="value_score" label="价值" width="70" />
            <el-table-column prop="growth_score" label="成长" width="70" />
            <el-table-column prop="quality_score" label="质量" width="70" />
            <el-table-column prop="momentum_score" label="动量" width="70" />
            <el-table-column prop="volatility_score" label="波动" width="70" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 算法说明 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <template #header><span>数据挖掘方法说明</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="去极值方法">MAD法（中位数绝对偏差），缩放因子1.4826</el-descriptions-item>
        <el-descriptions-item label="标准化方法">Z-Score标准化</el-descriptions-item>
        <el-descriptions-item label="因子合成">等权加总（5个因子Z-Score取均值）</el-descriptions-item>
        <el-descriptions-item label="动量因子">过去5日/20日收益率</el-descriptions-item>
        <el-descriptions-item label="波动因子">过去20日收益率标准差（越低越好）</el-descriptions-item>
        <el-descriptions-item label="评分含义">正分=优于平均，负分=劣于平均</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getFactorRanking, getFactorRadar, getSectors, getStockList } from '../api'
import RadarChart from '../components/RadarChart.vue'

const searchCode = ref('')
const stockList = ref([])
const industryFilter = ref('')
const ranking = ref([])
const radarData = ref({})
const sectors = ref([])
const rankingLoading = ref(false)
const radarLoading = ref(false)

const loadRanking = async () => {
  rankingLoading.value = true
  try {
    const res = await getFactorRanking(industryFilter.value || undefined, 30)
    // 后端字段名映射到前端
    ranking.value = (res.data.ranking || []).map(r => ({
      stock_code: r.ts_code,
      stock_name: r.name,
      industry: r.industry,
      composite_score: r.composite_score,
      value_score: r.factor_pe,
      growth_score: r.factor_pb,
      quality_score: r.factor_roe,
      momentum_score: r.factor_momentum,
      volatility_score: r.factor_vol,
      rank_num: r.rank_num,
    }))
  } catch (e) {
    console.error(e)
  } finally {
    rankingLoading.value = false
  }
}

const loadRadar = async () => {
  if (!searchCode.value) return
  radarLoading.value = true
  try {
    const res = await getFactorRadar(searchCode.value)
    radarData.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    radarLoading.value = false
  }
}

const loadSectors = async () => {
  try {
    const res = await getSectors()
    sectors.value = res.data.sectors || []
  } catch (e) {
    console.error(e)
  }
}

const handleRowClick = (row) => {
  searchCode.value = row.stock_code
  loadRadar()
}

const loadStockList = async () => {
  try {
    const res = await getStockList()
    stockList.value = res.data.stocks || []
  } catch (e) {
    console.error(e)
  }
}

watch(industryFilter, loadRanking)

onMounted(() => {
  loadRanking()
  loadSectors()
  loadStockList()
})
</script>
