<template>
  <div class="chat-view">
    <el-row :gutter="20">
      <!-- 左侧：股票信息 + 控制 -->
      <el-col :xs="24" :sm="24" :md="7" :lg="6">
        <div class="side-panel">
          <div class="panel-header">
            <span class="panel-icon">📊</span>
            <span>舆情数据源</span>
          </div>
          <div class="panel-body">
            <div class="stock-select-row">
              <el-select
                v-model="stockCode"
                filterable
                placeholder="🔍 搜索股票..."
                style="width: 100%;"
                @change="onStockChange"
                size="large"
              >
                <el-option
                  v-for="s in stockList"
                  :key="s.ts_code"
                  :label="`${s.name}（${s.ts_code}）`"
                  :value="s.ts_code"
                />
              </el-select>
            </div>
            <el-button
              class="refresh-btn"
              type="warning"
              @click="handleRefreshNews"
              :loading="refreshing"
              plain
            >
              <span v-if="!refreshing">🔄 刷新舆情数据</span>
              <span v-else>采集中...</span>
            </el-button>

            <div v-if="sentimentSummary && sentimentSummary.total > 0" class="sentiment-card">
              <div class="sentiment-title">📈 情感统计</div>
              <div class="sentiment-row">
                <div class="s-item">
                  <span class="s-label">总数</span>
                  <span class="s-num">{{ sentimentSummary.total }}</span>
                </div>
                <div class="s-item positive">
                  <span class="s-label">正面</span>
                  <span class="s-num">{{ sentimentSummary.positive }}</span>
                </div>
                <div class="s-item negative">
                  <span class="s-label">负面</span>
                  <span class="s-num">{{ sentimentSummary.negative }}</span>
                </div>
                <div class="s-item neutral">
                  <span class="s-label">中性</span>
                  <span class="s-num">{{ sentimentSummary.neutral }}</span>
                </div>
                <div class="s-item score">
                  <span class="s-label">均分</span>
                  <span :class="['s-num', scoreLevel]">{{ sentimentSummary.avg_score }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-hint">
              <div class="empty-icon">💬</div>
              <p>选择股票后可查看舆情数据<br/>也可以直接提问，股小查会自动搜索 📡</p>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 右侧：聊天区域 -->
      <el-col :xs="24" :sm="24" :md="17" :lg="18">
        <div class="chat-panel">
          <!-- 聊天头部 -->
          <div class="chat-header">
            <div class="chat-header-left">
              <div class="ai-avatar-large">
                <span>🦊</span>
              </div>
              <div>
                <div class="ai-name">股小查</div>
                <div class="ai-status">
                  <span class="status-dot"></span>
                  在线 · 随时为你服务
                </div>
              </div>
            </div>
            <div class="chat-header-right">
              <span class="powered-by">Powered by DeepSeek</span>
            </div>
          </div>

          <!-- 消息列表 -->
          <div ref="messageContainer" class="message-container">
            <div v-if="messages.length === 0" class="welcome-screen">
              <div class="welcome-avatar">🦊</div>
              <div class="welcome-title">你好呀！我是股小查~ 😊</div>
              <div class="welcome-desc">你的A股智能投资小助手！<br/>直接告诉我你想了解哪只股票，我来帮你查！</div>
              <div class="welcome-tips">
                <div class="tip-item" @click="quickAsk('帮我查一下贵州茅台')">🏷️ 帮我查一下贵州茅台</div>
                <div class="tip-item" @click="quickAsk('平安银行最近行情怎么样？')">📊 平安银行最近行情怎么样？</div>
                <div class="tip-item" @click="quickAsk('查询系统中所有股票')">📋 查询系统中所有股票</div>
              </div>
            </div>

            <div v-for="(msg, i) in messages" :key="i"
              :class="['message-row', msg.role === 'user' ? 'user-row' : 'assistant-row']">
              <div v-if="msg.role === 'assistant'" class="msg-avatar">
                <span>🦊</span>
              </div>
              <div :class="['msg-bubble', msg.role]">
                <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
              </div>
              <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">
                <span>👤</span>
              </div>
            </div>

            <div v-if="loading" class="message-row assistant-row">
              <div class="msg-avatar">
                <span>🦊</span>
              </div>
              <div class="msg-bubble assistant">
                <div class="typing-indicator">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="typing-text">股小查正在查数据...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入框 -->
          <div class="input-area">
            <div class="input-wrapper">
              <el-input
                v-model="question"
                type="textarea"
                :rows="1"
                placeholder="直接提问，例如：帮我查一下贵州茅台"
                @keydown.enter.prevent="handleSend"
                :disabled="loading"
                class="chat-input"
              />
              <el-button
                class="send-btn"
                type="primary"
                @click="handleSend"
                :loading="loading"
                :disabled="!question.trim()"
              >
                <span v-if="!loading">发送</span>
              </el-button>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { chatAsk, refreshNews, getStockList } from '../api'
import { getSentimentSummary } from '../api'

const stockCode = ref('')
const stockList = ref([])
const messages = ref([])
const question = ref('')
const loading = ref(false)
const refreshing = ref(false)
const sentimentSummary = ref(null)
const messageContainer = ref(null)

const scrollToBottom = () => {
  setTimeout(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  }, 100)
}

const renderMarkdown = (text) => {
  if (!text) return ''
  // 1. 先转义 HTML 特殊字符（防止 XSS 和渲染错乱）
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 2. 表格处理：识别连续的 | 行转为 <table>
  const lines = html.split('\n')
  let out = []
  let i = 0
  while (i < lines.length) {
    const t = lines[i].trim()
    if (t.startsWith('|') && t.endsWith('|')) {
      const tbl = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tbl.push(lines[i].trim())
        i++
      }
      if (tbl.length >= 2) {
        const isSep = (line) => {
          const parts = line.split('|')
          return parts.length >= 3 && parts.slice(1, -1).every(p => /^[-:\s]+$/.test(p))
        }
        const sep = isSep(tbl[1])
        out.push('<table>')
        const hd = tbl[0].split('|').filter(c => c.trim())
        out.push('<thead><tr>' + hd.map(c => '<th>' + c.trim() + '</th>').join('') + '</tr></thead>')
        out.push('<tbody>')
        for (let j = sep ? 2 : 1; j < tbl.length; j++) {
          const cells = tbl[j].split('|').filter(c => c.trim())
          out.push('<tr>' + cells.map(c => '<td>' + c.trim() + '</td>').join('') + '</tr>')
        }
        out.push('</tbody></table>')
      }
    } else {
      out.push(lines[i])
      i++
    }
  }

  // 3. 加粗/斜体 + 换行
  html = out.join('\n')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
  return html
}

const scoreLevel = computed(() => {
  if (!sentimentSummary.value) return ''
  const s = sentimentSummary.value.avg_score
  if (s > 0.6) return 'high'
  if (s < 0.4) return 'low'
  return 'mid'
})

const onStockChange = async () => {
  if (stockCode.value) {
    try {
      const res = await getSentimentSummary(stockCode.value)
      sentimentSummary.value = res.data
    } catch (e) {
      sentimentSummary.value = null
    }
  }
}

const handleRefreshNews = async () => {
  if (!stockCode.value) {
    ElMessage.warning('请先选择股票')
    return
  }
  refreshing.value = true
  try {
    const res = await refreshNews(stockCode.value)
    if (res.data.success) {
      ElMessage.success(`✅ 采集完成，新增 ${res.data.new_count} 条新闻`)
      onStockChange()
    }
  } catch (e) {
    ElMessage.error('❌ 刷新失败: ' + e.message)
  } finally {
    refreshing.value = false
  }
}

const quickAsk = (text) => {
  question.value = text.replace(/^[^\s]+\s/, '')
  handleSend()
}

const handleSend = async () => {
  const text = question.value.trim()
  if (!text) return

  // 如果没有选股票，但用户问题中可能提到了某只股票，让AI自己去搜索

  messages.value.push({ role: 'user', content: text })
  question.value = ''
  loading.value = true
  scrollToBottom()

  let history = messages.value.slice(-10, -1).map(m => ({
    role: m.role,
    content: m.content,
  }))

  try {
    const res = await chatAsk(text, stockCode.value || undefined, history)
    if (res.data.success) {
      messages.value.push({ role: 'assistant', content: res.data.answer })
    } else {
      messages.value.push({
        role: 'assistant',
        content: `抱歉，${res.data.message} 😅`,
      })
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: `抱歉，连接失败: ${e.message} 😅 请检查后端是否正常运行~`,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  try {
    const res = await getStockList()
    stockList.value = res.data.stocks || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.chat-view {
  height: calc(100vh - 100px);
  min-height: 560px;
}

/* ========== 左侧面板 ========== */
.side-panel {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  overflow: hidden;
}
.panel-header {
  padding: 16px 20px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-header .panel-icon {
  font-size: 20px;
}
.panel-body {
  padding: 16px;
}
.stock-select-row {
  margin-bottom: 12px;
}
.refresh-btn {
  width: 100%;
  margin-bottom: 16px;
  font-size: 14px;
  border-radius: 10px;
  padding: 10px 0;
}

/* 情感统计卡片 */
.sentiment-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2f5 100%);
  border-radius: 12px;
  padding: 12px;
}
.sentiment-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}
.sentiment-row {
  display: flex;
  gap: 4px;
}
.s-item {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 6px 4px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.s-label {
  display: block;
  font-size: 10px;
  color: #999;
}
.s-num {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  margin-top: 1px;
}
.s-item.positive .s-num { color: #16c79a; }
.s-item.negative .s-num { color: #e74c3c; }
.s-item.neutral .s-num { color: #f39c12; }
.s-item.score .s-num.high { color: #16c79a; }
.s-item.score .s-num.mid { color: #f39c12; }
.s-item.score .s-num.low { color: #e74c3c; }

.empty-hint {
  text-align: center;
  padding: 30px 10px;
  color: #bbb;
}
.empty-icon {
  font-size: 40px;
  margin-bottom: 10px;
}
.empty-hint p {
  font-size: 13px;
  line-height: 1.8;
  margin: 0;
}

/* ========== 聊天面板 ========== */
.chat-panel {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  min-height: 560px;
  overflow: hidden;
}

/* 聊天头部 */
.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ai-avatar-large {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.ai-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
}
.ai-status {
  font-size: 12px;
  color: #999;
  display: flex;
  align-items: center;
  gap: 5px;
}
.status-dot {
  width: 6px;
  height: 6px;
  background: #16c79a;
  border-radius: 50%;
  display: inline-block;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.powered-by {
  font-size: 11px;
  color: #ccc;
}

/* 欢迎界面 */
.welcome-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}
.welcome-avatar {
  font-size: 64px;
  margin-bottom: 16px;
  animation: bounce 2s infinite;
}
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.welcome-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
}
.welcome-desc {
  font-size: 14px;
  color: #888;
  line-height: 1.8;
  margin-bottom: 24px;
}
.welcome-tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tip-item {
  background: #f5f6fa;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}
.tip-item:hover {
  background: #e8f5e9;
  color: #16c79a;
  transform: translateX(4px);
}

/* 消息容器 */
.message-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.message-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.user-row {
  justify-content: flex-end;
}
.assistant-row {
  justify-content: flex-start;
}

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
}
.user-avatar {
  background: linear-gradient(135deg, #16c79a, #0da688);
}

.msg-bubble {
  max-width: 70%;
  padding: 12px 18px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg-bubble.user {
  background: linear-gradient(135deg, #16c79a, #0da688);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
  background: #f5f6fa;
  color: #333;
  border-bottom-left-radius: 4px;
}
.msg-text {
  white-space: pre-wrap;
}
.msg-text :deep(strong) {
  color: inherit;
  font-weight: 700;
}
.msg-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.msg-text :deep(th) {
  background: #1a1a2e;
  color: #fff;
  padding: 6px 10px;
  text-align: center;
  font-weight: 600;
}
.msg-text :deep(td) {
  padding: 5px 10px;
  border-bottom: 1px solid #e8e8e8;
  text-align: center;
}
.msg-text :deep(tr:last-child td) {
  border-bottom: none;
}
.msg-text :deep(tr:hover td) {
  background: #f8f9ff;
}
.msg-bubble.user .msg-text :deep(table) {
  color: #333;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 0;
}
.typing-indicator .dot {
  width: 8px;
  height: 8px;
  background: #ccc;
  border-radius: 50%;
  animation: typing 1.4s infinite both;
}
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }
.typing-indicator .typing-text {
  font-size: 12px;
  color: #999;
  margin-left: 4px;
  width: auto;
  height: auto;
  background: none;
  border-radius: 0;
  animation: none;
}
@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 输入区域 */
.input-area {
  flex-shrink: 0;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}
.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: center;
}
.chat-input {
  flex: 1;
}
.chat-input :deep(.el-textarea__inner) {
  border-radius: 12px;
  border: 1px solid #e8e8e8;
  padding: 10px 16px;
  font-size: 14px;
  resize: none;
  min-height: 44px;
  transition: border-color 0.2s;
}
.chat-input :deep(.el-textarea__inner:focus) {
  border-color: #16c79a;
  box-shadow: 0 0 0 2px rgba(22,199,154,0.1);
}
.send-btn {
  height: 44px;
  width: 80px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border: none;
}
.send-btn:hover {
  background: linear-gradient(135deg, #16213e, #1a1a2e);
  transform: translateY(-1px);
}
.send-btn:disabled {
  background: #ccc;
}

/* 滚动条 */
.message-container::-webkit-scrollbar {
  width: 4px;
}
.message-container::-webkit-scrollbar-track {
  background: transparent;
}
.message-container::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 4px;
}
</style>
