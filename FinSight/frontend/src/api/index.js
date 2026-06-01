import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // LSTM训练可能较慢
})

// ============ 行情 ============
export const getMarketIndices = () => api.get('/market/indices')
export const getKline = (code, limit = 120) => api.get(`/market/kline/${code}`, { params: { limit } })
export const getSectors = () => api.get('/market/sectors')
export const getStockList = () => api.get('/market/stocks')

// ============ 因子选股 ============
export const getFactorRanking = (industry, topN = 20) => api.get('/factor/ranking', { params: { industry, top_n: topN } })
export const getFactorRadar = (code) => api.get(`/factor/radar/${code}`)
export const refreshFactors = () => api.post('/factor/refresh')

// ============ 趋势预测 ============
export const trainPredict = (code, epochs = 50) => api.post(`/predict/train/${code}`, null, { params: { epochs } })
export const getPredictResult = (code, days = 5) => api.get(`/predict/result/${code}`, { params: { days } })
export const getTrainedModels = () => api.get('/predict/models')

// ============ 异常检测 ============
export const detectAnomalies = (startDate, endDate) => api.get('/anomaly/detect', { params: { start_date: startDate, end_date: endDate } })
export const getAnomalyAlerts = () => api.get('/anomaly/alerts')
export const getAnomalyKline = (code) => api.get(`/anomaly/kline/${code}`)

// ============ 数据管理 ============
export const initData = () => api.post('/data/init')
export const getInitStatus = () => api.get('/data/init-status')
export const getDataStatus = () => api.get('/data/status')

// ============ AI 助手 ============
export const chatAsk = (question, tsCode, history) => api.post('/chat/ask', { question, ts_code: tsCode, history })
export const refreshNews = (code) => api.post(`/chat/refresh-news/${code}`)
export const getSentimentSummary = (code) => api.get(`/chat/sentiment/${code}`)

export default api
