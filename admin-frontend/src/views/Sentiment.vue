<template>
  <div class="sentiment-page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-header">
      <div>
        <h2 class="page-title">📊 游客感受度报告</h2>
        <p class="page-desc">基于 LLM 情感分析，洞察游客情绪变化与服务优化方向</p>
      </div>
      <div class="page-actions">
        <el-tag type="info" size="large" style="font-size: 14px; padding: 8px 16px;">
          近7天 · {{ overview.total_conversations || 0 }} 条对话
        </el-tag>
      </div>
    </div>

    <!-- ===== 第一行：情感分布 + 热门话题 ===== -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <span class="card-title">🎯 情感倾向分布</span>
            <span class="card-subtitle">近7天 · {{ overview.total_conversations || 0 }} 条</span>
          </template>
          <div v-if="loading.overview" class="loading-text">加载中...</div>
          <div v-else ref="emotionPie" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="table-card" shadow="hover">
          <template #header>
            <span class="card-title">🔥 游客关注点 TOP6</span>
            <span class="card-subtitle">近30天累计</span>
          </template>
          <el-table :data="hotTopics" stripe v-loading="loading.hotTopics" style="width: 100%">
            <el-table-column prop="topic" label="关注点" min-width="120" />
            <el-table-column prop="count" label="提及次数" width="100" align="center" />
            <el-table-column label="占比" width="100" align="center">
              <template #default="{ row }">
                <span v-if="totalMentions > 0" class="percentage">
                  {{ ((row.count / totalMentions) * 100).toFixed(1) }}%
                </span>
                <span v-else>0%</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="hotTopics.length > 0 && totalMentions > 0" class="table-note">
            * 占比 = 该话题提及次数 / 所有话题提及次数之和 × 100%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 第二行：服务建议 ===== -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card class="suggestion-card" shadow="hover">
          <template #header>
            <div class="suggestion-header-wrapper">
              <span class="card-title">💡 服务建议</span>
              <span class="card-subtitle">基于情感分析自动生成</span>
              <el-button
                type="primary"
                size="small"
                class="generate-btn"
                @click="generateAdvancedReport"
                :loading="isGenerating"
              >
                {{ isGenerating ? '生成中...' : '📊 生成详细报告' }}
              </el-button>
            </div>
          </template>
          <div v-if="loading.suggestions" class="loading-text">正在生成建议...</div>
          <div v-else-if="suggestions.length === 0" class="empty-state-text">暂无建议，请等待更多数据</div>
          <div v-else>
            <div v-for="(item, index) in suggestions" :key="index" class="suggestion-item">
              <div class="suggestion-header">
                <el-tag :type="item.level === 'high' ? 'danger' : item.level === 'medium' ? 'warning' : 'info'" size="small">
                  {{ item.title }}
                </el-tag>
              </div>
              <p class="suggestion-desc">{{ item.description }}</p>
              <div class="suggestion-action">
                <el-icon><Monitor /></el-icon>
                <span>{{ item.action }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 第三行：高风险会话 ===== -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card class="table-card" shadow="hover">
          <template #header>
            <div class="table-header-wrapper">
              <span class="card-title">⚠️ 高风险会话</span>
              <span class="card-subtitle">情绪持续下降 · 需关注</span>
              <el-tag v-if="highRiskSessions.length > 0" type="danger" size="small" class="count-tag">
                共 {{ highRiskSessions.length }} 个
              </el-tag>
              <el-tag v-else type="success" size="small" class="count-tag">
                ✅ 暂无高风险会话
              </el-tag>
            </div>
          </template>
          <div v-if="loading.highRisk" class="loading-text">加载中...</div>
          <el-table v-else :data="highRiskSessions" stripe style="width: 100%">
            <el-table-column prop="session_id" label="会话ID" min-width="180" show-overflow-tooltip />
            <el-table-column prop="total_turns" label="对话轮数" width="100" align="center" />
            <el-table-column label="风险等级" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'info'" size="small">
                  {{ row.risk_level === 'high' ? '🔴 高' : row.risk_level === 'medium' ? '🟡 中' : '🟢 低' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="风险评分" width="100" align="center">
              <template #default="{ row }">
                <span :style="{
                  color: row.risk_score >= 45 ? '#f56c6c' : row.risk_score >= 20 ? '#e6a23c' : '#67c23a',
                  fontWeight: 'bold'
                }">
                  {{ row.risk_score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="末段负面密度" width="130" align="center">
              <template #default="{ row }">
                <span>{{ row.negative_density || 0 }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="起始情绪" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.start_sentiment)" size="small">
                  {{ getSentimentLabel(row.start_sentiment) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="结束情绪" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.end_sentiment)" size="small">
                  {{ getSentimentLabel(row.end_sentiment) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" plain @click="viewSessionHistory(row.session_id)">
                  查看对话
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="highRiskSessions.length > 0" class="table-note">
            💡 风险评分 ≥ 45 为高风险，20-44 为中风险，&lt; 20 为低风险
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 第四行：高级报告（折叠/展开） ===== -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card class="report-card" shadow="hover">
          <template #header>
            <div class="report-header-wrapper">
              <span class="card-title">📄 高级分析报告</span>
              <span class="card-subtitle">AI 自动生成 · 决策建议</span>
              <div class="report-actions">
                <el-button
                  v-if="advancedReport"
                  size="small"
                  :type="reportVisible ? 'warning' : 'primary'"
                  @click="toggleReport"
                >
                  {{ reportVisible ? '收起' : '展开' }}
                </el-button>
                <el-button
                  v-if="reportVisible"
                  size="small"
                  type="success"
                  @click="exportReport"
                >
                  <el-icon><Download /></el-icon>
                  导出报告
                </el-button>
              </div>
            </div>
          </template>
          <div v-show="reportVisible" class="report-box">
            <div v-if="advancedReport" v-html="formatReport(advancedReport)"></div>
            <div v-else class="empty-state-text">
              暂无报告，请点击“生成详细报告”按钮生成
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 对话历史对话框 ===== -->
    <el-dialog
      v-model="dialogVisible"
      :title="'会话详情：' + currentSessionId"
      width="1000px"
      top="5vh"
      class="history-dialog"
    >
      <div v-if="loading.history" class="loading-text">加载对话历史...</div>
      <template v-else>
        <!-- 情绪轨迹折线图 -->
        <div v-if="trajectoryData.length > 0" class="trajectory-section">
          <h4 class="trajectory-title">📈 情绪演变轨迹</h4>
          <div ref="trajectoryChart" class="trajectory-chart"></div>
          <div class="trajectory-legend">
            <span><span class="dot positive"></span> 正面</span>
            <span><span class="dot neutral"></span> 中性</span>
            <span><span class="dot negative"></span> 负面</span>
          </div>
        </div>

        <!-- 对话时间线 -->
        <el-timeline>
          <el-timeline-item
            v-for="item in sessionHistory"
            :key="item.turn"
            :timestamp="item.created_at"
            :type="getTimelineType(item.sentiment)"
            placement="top"
          >
            <el-card shadow="hover" class="history-message-card">
              <div class="history-message-header">
                <el-tag :type="getSentimentType(item.sentiment)" size="small">
                  {{ getSentimentLabel(item.sentiment) }}
                </el-tag>
                <span class="turn-label">第 {{ item.turn }} 轮</span>
              </div>
              <div class="history-message-body">
                <div class="user-question">
                  <strong>问：</strong>{{ item.question }}
                </div>
                <div class="ai-answer">
                  <strong>答：</strong>{{ item.answer }}
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" plain @click="exportSessionHistory">
          <el-icon><Download /></el-icon>
          导出对话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Monitor, TrendCharts, Download } from '@element-plus/icons-vue'
import axios from 'axios'

// ============================================================
// 状态变量
// ============================================================
const emotionPie = ref(null)
const trajectoryChart = ref(null)
let chartInstance = null
let trajectoryChartInstance = null

const loading = ref({
  overview: false,
  hotTopics: false,
  suggestions: false,
  highRisk: false,
  history: false
})

const isGenerating = ref(false)

const overview = ref({
  total_conversations: 0,
  today_conversations: 0,
  sentiment_distribution: { positive: 0, neutral: 0, negative: 0 },
  positive_rate: 0,
  negative_rate: 0,
  neutral_rate: 0,
  avg_response_time: 0
})

const hotTopics = ref([])
const suggestions = ref([])
const highRiskSessions = ref([])

const advancedReport = ref(null)
const reportVisible = ref(false)

const dialogVisible = ref(false)
const currentSessionId = ref('')
const sessionHistory = ref([])
const trajectoryData = ref([])

// ============================================================
// 计算属性
// ============================================================
const totalMentions = computed(() => {
  return hotTopics.value.reduce((sum, t) => sum + t.count, 0)
})

// ============================================================
// 工具函数
// ============================================================
const getSentimentType = (sentiment) => {
  const map = { positive: 'success', neutral: 'warning', negative: 'danger' }
  return map[sentiment] || 'info'
}

const getSentimentLabel = (sentiment) => {
  const map = { positive: '正面', neutral: '中性', negative: '负面' }
  return map[sentiment] || sentiment
}

const getTimelineType = (sentiment) => {
  const map = { positive: 'success', neutral: 'warning', negative: 'danger' }
  return map[sentiment] || 'primary'
}

const formatReport = (text) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

// ============================================================
// API 调用
// ============================================================
const API_BASE = '/api/admin'

const fetchOverview = async () => {
  loading.value.overview = true
  try {
    const res = await axios.get(`${API_BASE}/sentiment/overview?days=7`)
    if (res.data.code === 0) {
      overview.value = res.data.data
    }
  } catch (err) {
    console.error('获取总览失败:', err)
  } finally {
    loading.value.overview = false
    await nextTick()
    setTimeout(() => renderPieChart(), 200)
  }
}

const fetchHotTopics = async () => {
  loading.value.hotTopics = true
  try {
    const res = await axios.get(`${API_BASE}/sentiment/hot-topics?limit=6`)
    if (res.data.code === 0) {
      hotTopics.value = res.data.data
    }
  } catch (err) {
    console.error('获取热门话题失败:', err)
  } finally {
    loading.value.hotTopics = false
  }
}

const fetchSuggestions = async () => {
  loading.value.suggestions = true
  try {
    const res = await axios.get(`${API_BASE}/sentiment/suggestions?days=7`)
    if (res.data.code === 0) {
      suggestions.value = res.data.data
    }
  } catch (err) {
    console.error('获取建议失败:', err)
  } finally {
    loading.value.suggestions = false
  }
}

const fetchHighRiskSessions = async () => {
  loading.value.highRisk = true
  try {
    const res = await axios.get(`${API_BASE}/sentiment/high-risk?days=7&threshold=high`)
    if (res.data.code === 0) {
      highRiskSessions.value = res.data.data
    }
  } catch (err) {
    console.error('获取高风险会话失败:', err)
  } finally {
    loading.value.highRisk = false
  }
}

// ============================================================
// 饼图渲染
// ============================================================
const renderPieChart = () => {
  const container = emotionPie.value
  if (!container) {
    setTimeout(renderPieChart, 300)
    return
  }

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(renderPieChart, 200)
    return
  }

  try {
    chartInstance = echarts.getInstanceByDom(container)
    if (!chartInstance) {
      chartInstance = echarts.init(container)
    }

    const dist = overview.value.sentiment_distribution || { positive: 0, neutral: 0, negative: 0 }
    const total = overview.value.total_conversations || 1

    chartInstance.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}条 ({d}%)'
      },
      legend: {
        top: 'bottom',
        formatter: (name) => {
          const map = { '正面': 'positive', '中性': 'neutral', '负面': 'negative' }
          const key = map[name] || name
          const count = dist[key] || 0
          const pct = ((count / total) * 100).toFixed(1)
          return `${name}  ${count}条 (${pct}%)`
        }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        data: [
          { name: '正面', value: dist.positive || 0, itemStyle: { color: '#10b981' } },
          { name: '中性', value: dist.neutral || 0, itemStyle: { color: '#f59e0b' } },
          { name: '负面', value: dist.negative || 0, itemStyle: { color: '#ef4444' } }
        ],
        emphasis: { scale: true },
        label: { show: true, formatter: '{d}%' },
        labelLine: { show: true }
      }]
    })

    setTimeout(() => chartInstance?.resize(), 50)
    console.log('✅ 饼图渲染成功')
  } catch (err) {
    console.error('饼图渲染失败:', err)
  }
}

// ============================================================
// 情绪轨迹折线图渲染
// ============================================================
const renderTrajectoryChart = () => {
  const container = trajectoryChart.value
  if (!container) {
    setTimeout(renderTrajectoryChart, 200)
    return
  }

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(renderTrajectoryChart, 200)
    return
  }

  try {
    if (trajectoryChartInstance) {
      trajectoryChartInstance.dispose()
    }
    trajectoryChartInstance = echarts.init(container)

    const scoreMap = { positive: 1, neutral: 0, negative: -1 }
    const scores = trajectoryData.value.map(t => scoreMap[t] ?? 0)
    const labels = trajectoryData.value.map((_, i) => `第${i+1}轮`)

    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: function(params) {
          const idx = params[0].dataIndex
          const sentiment = trajectoryData.value[idx] || 'neutral'
          const sentimentLabel = getSentimentLabel(sentiment)
          return `<strong>第${idx+1}轮</strong><br/>情绪：${sentimentLabel}`
        }
      },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { fontSize: 11, interval: Math.floor(labels.length / 10) },
        axisLine: { lineStyle: { color: '#ddd' } }
      },
      yAxis: {
        type: 'value',
        min: -1.3,
        max: 1.3,
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
        axisLabel: { show: false },
        axisLine: { show: false }
      },
      grid: { top: 20, bottom: 30, left: 10, right: 20 },
      series: [{
        type: 'line',
        data: scores,
        smooth: true,
        lineStyle: { color: '#3b82f6', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
          ])
        },
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: function(params) {
            const val = params.value
            if (val >= 0.5) return '#10b981'
            if (val >= -0.5) return '#f59e0b'
            return '#ef4444'
          }
        },
        markLine: {
          silent: true,
          data: [{ yAxis: 0 }],
          lineStyle: { color: '#ccc', type: 'dashed' },
          label: { show: false }
        }
      }]
    }

    trajectoryChartInstance.setOption(option)
    setTimeout(() => trajectoryChartInstance?.resize(), 100)
    console.log('✅ 情绪轨迹图渲染成功')
  } catch (err) {
    console.error('情绪轨迹图渲染失败:', err)
  }
}

// ============================================================
// 查看会话历史
// ============================================================
const viewSessionHistory = async (sessionId) => {
  currentSessionId.value = sessionId
  dialogVisible.value = true
  loading.value.history = true
  sessionHistory.value = []
  trajectoryData.value = []

  try {
    const [historyRes, trajectoryRes] = await Promise.all([
      axios.get(`${API_BASE}/sentiment/session/${sessionId}/history`),
      axios.get(`${API_BASE}/sentiment/session/${sessionId}/trajectory`)
    ])

    if (historyRes.data.code === 0) {
      sessionHistory.value = historyRes.data.data
    }

    if (trajectoryRes.data.code === 0) {
      trajectoryData.value = trajectoryRes.data.data.trajectory || []
      await nextTick()
      setTimeout(() => renderTrajectoryChart(), 300)
    }
  } catch (err) {
    console.error('获取会话数据失败:', err)
    ElMessage.error('获取会话数据失败')
  } finally {
    loading.value.history = false
  }
}

// ============================================================
// 高级报告操作
// ============================================================
const generateAdvancedReport = async () => {
  if (isGenerating.value) {
    ElMessage.warning('报告生成中，请等待...')
    return
  }

  isGenerating.value = true
  try {
    const res = await axios.get(`${API_BASE}/sentiment/advanced-report?days=7`)
    if (res.data.code === 0) {
      advancedReport.value = res.data.data.report_text
      reportVisible.value = true
      localStorage.setItem('sentiment_report', res.data.data.report_text)
      ElMessage.success('报告生成成功！')
    }
  } catch (err) {
    console.error('生成报告失败:', err)
    ElMessage.error('生成报告失败')
  } finally {
    isGenerating.value = false
  }
}

const toggleReport = () => {
  if (!advancedReport.value) {
    generateAdvancedReport()
  } else {
    reportVisible.value = !reportVisible.value
  }
}

const exportReport = () => {
  if (!advancedReport.value) {
    ElMessage.warning('没有可导出的报告')
    return
  }
  const blob = new Blob([advancedReport.value], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `游客感受度报告_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('报告导出成功！')
}

const exportSessionHistory = () => {
  if (sessionHistory.value.length === 0) {
    ElMessage.warning('没有可导出的对话')
    return
  }
  let text = `会话ID：${currentSessionId.value}\n`
  text += `导出时间：${new Date().toLocaleString()}\n`
  text += '='.repeat(60) + '\n\n'

  if (trajectoryData.value.length > 0) {
    text += '情绪轨迹：' + trajectoryData.value.map(t => getSentimentLabel(t)).join(' → ') + '\n\n'
  }

  sessionHistory.value.forEach(item => {
    text += `[第${item.turn}轮] ${item.created_at}\n`
    text += `情绪：${getSentimentLabel(item.sentiment)}\n`
    text += `问：${item.question}\n`
    text += `答：${item.answer}\n`
    text += '-'.repeat(40) + '\n'
  })

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `会话记录_${currentSessionId.value}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('对话导出成功！')
}

// ============================================================
// 生命周期
// ============================================================
onMounted(async () => {
  const cached = localStorage.getItem('sentiment_report')
  if (cached) {
    advancedReport.value = cached
    reportVisible.value = true
  }

  await Promise.all([
    fetchOverview(),
    fetchHotTopics(),
    fetchSuggestions(),
    fetchHighRiskSessions()
  ])

  setTimeout(() => {
    if (!chartInstance) {
      renderPieChart()
    }
  }, 2000)
})

window.addEventListener('resize', () => {
  if (chartInstance) setTimeout(() => chartInstance?.resize(), 100)
  if (trajectoryChartInstance) setTimeout(() => trajectoryChartInstance?.resize(), 100)
})

watch(advancedReport, (newVal) => {
  if (newVal) {
    localStorage.setItem('sentiment_report', newVal)
  } else {
    localStorage.removeItem('sentiment_report')
  }
})

watch(dialogVisible, (newVal) => {
  if (!newVal) {
    setTimeout(() => {
      if (trajectoryChartInstance) {
        trajectoryChartInstance.dispose()
        trajectoryChartInstance = null
      }
    }, 300)
  }
})
</script>

<style scoped>
/* ===== 页面布局 ===== */
.sentiment-page {
  padding: 0;
}

/* ===== 页面头部 ===== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-dark);
  margin: 0;
}
.page-desc {
  font-size: 14px;
  color: var(--text-gray);
  margin: 4px 0 0;
}
.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== 卡片标题 ===== */
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-dark);
}
.card-subtitle {
  font-size: 13px;
  color: var(--text-light);
  margin-left: 12px;
}

/* ===== 图表卡片 ===== */
.chart-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
}
.chart-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.chart-card :deep(.el-card__body) {
  padding: 16px 20px 20px;
}
.chart-container {
  height: 300px;
  width: 100%;
}

/* ===== 表格卡片 ===== */
.table-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
}
.table-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.table-card :deep(.el-card__body) {
  padding: 0;
}
.table-card :deep(.el-table) {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.table-card :deep(.el-table th.el-table__cell) {
  background: rgba(44, 110, 138, 0.04) !important;
  color: var(--text-mid);
  font-weight: 600;
}
.table-card :deep(.el-table .el-table__row:hover td.el-table__cell) {
  background: rgba(44, 110, 138, 0.02) !important;
}

.table-header-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.count-tag {
  margin-left: 4px;
}

.table-note {
  padding: 10px 16px 12px;
  font-size: 12px;
  color: var(--text-light);
  border-top: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.percentage {
  font-weight: 600;
  color: var(--text-mid);
}

/* ===== 建议卡片 ===== */
.suggestion-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
}
.suggestion-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.suggestion-card :deep(.el-card__body) {
  padding: 20px 24px;
}

.suggestion-header-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.generate-btn {
  margin-left: auto;
}

.suggestion-item {
  padding: 14px 18px;
  background: rgba(44, 110, 138, 0.03);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  border-left: 4px solid var(--primary-color);
}
.suggestion-item:last-child {
  margin-bottom: 0;
}
.suggestion-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.suggestion-desc {
  margin: 6px 0 8px 0;
  color: var(--text-mid);
  font-size: 14px;
  line-height: 1.6;
}
.suggestion-action {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--primary-color);
  font-size: 13px;
  background: rgba(44, 110, 138, 0.06);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  margin-top: 4px;
}

/* ===== 报告卡片 ===== */
.report-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
}
.report-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.report-card :deep(.el-card__body) {
  padding: 16px 24px 20px;
}

.report-header-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.report-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.report-box {
  background: rgba(44, 110, 138, 0.03);
  padding: 16px 20px;
  border-radius: var(--radius-sm);
  line-height: 1.8;
  font-size: 14px;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--border-light);
}

/* ===== 对话框样式 ===== */
.history-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
}
.history-dialog :deep(.el-dialog__header) {
  padding: 20px 24px 12px;
  border-bottom: 1px solid var(--border-light);
}
.history-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
  max-height: 70vh;
  overflow-y: auto;
}
.history-dialog :deep(.el-dialog__footer) {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--border-light);
}

.trajectory-section {
  margin-bottom: 24px;
}
.trajectory-title {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-dark);
}
.trajectory-chart {
  height: 200px;
  width: 100%;
}
.trajectory-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-gray);
}
.trajectory-legend .dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  vertical-align: middle;
  margin-right: 4px;
}
.trajectory-legend .dot.positive {
  background: #10b981;
}
.trajectory-legend .dot.neutral {
  background: #f59e0b;
}
.trajectory-legend .dot.negative {
  background: #ef4444;
}

.history-message-card {
  border-radius: var(--radius-sm) !important;
}
.history-message-card :deep(.el-card__body) {
  padding: 12px 16px !important;
}
.history-message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.turn-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-mid);
}
.history-message-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.user-question {
  color: var(--text-dark);
  font-size: 14px;
  padding: 4px 8px;
  background: rgba(44, 110, 138, 0.04);
  border-radius: var(--radius-sm);
}
.ai-answer {
  color: #10b981;
  font-size: 14px;
  padding: 4px 8px;
  background: rgba(16, 185, 129, 0.04);
  border-radius: var(--radius-sm);
}

/* ===== 通用 ===== */
.loading-text {
  text-align: center;
  color: var(--text-gray);
  padding: 40px 0;
}
.empty-state-text {
  text-align: center;
  color: var(--text-gray);
  padding: 20px 0;
  font-size: 14px;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .page-title {
    font-size: 18px;
  }
  .chart-card :deep(.el-card__header),
  .table-card :deep(.el-card__header),
  .suggestion-card :deep(.el-card__header),
  .report-card :deep(.el-card__header) {
    padding: 12px 16px;
  }
  .chart-card :deep(.el-card__body) {
    padding: 12px 14px 16px;
  }
  .chart-container {
    height: 220px;
  }
  .suggestion-card :deep(.el-card__body) {
    padding: 14px 16px;
  }
  .report-card :deep(.el-card__body) {
    padding: 12px 16px 16px;
  }
  .suggestion-header-wrapper {
    flex-wrap: wrap;
  }
  .generate-btn {
    margin-left: 0;
  }
  .report-header-wrapper {
    flex-wrap: wrap;
  }
  .report-actions {
    margin-left: 0;
  }
  .history-dialog :deep(.el-dialog) {
    width: 95% !important;
  }
  .trajectory-chart {
    height: 150px;
  }
}
</style>