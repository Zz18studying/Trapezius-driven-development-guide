<template>
  <div class="dashboard">
    <!-- ===== 加载状态 ===== -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
      <div class="loading-text">正在加载数据...</div>
    </div>

    <!-- ===== 数据内容 ===== -->
    <template v-else>
      <!-- KPI 卡片（毛玻璃 + 渐变点缀） -->
      <el-row :gutter="20">
        <el-col :span="6" v-for="(item, index) in kpiList" :key="index">
          <el-card class="kpi-card" shadow="hover" :style="`border-top: 4px solid ${item.borderColor || '#2c6e8a'};`">
            <div class="kpi-icon" :style="`color: ${item.iconColor || '#2c6e8a'};`">{{ item.icon }}</div>
            <div class="kpi-title">{{ item.title }}</div>
            <div class="kpi-value">{{ item.value }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 图表行 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <span class="chart-title">📈 近7天服务人次趋势</span>
              <el-button size="small" class="refresh-btn" @click="refreshData">刷新</el-button>
            </template>
            <div ref="trendChart" style="height: 300px; width: 100%;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <span class="chart-title">☁️ 游客关注词云</span>
              <span style="font-size: 12px; color: #8aa8b8; margin-left: 8px;">
                {{ keywordDateRange }} · TOP25
              </span>
            </template>
            <div style="position: relative; height: 300px; width: 100%;">
              <div ref="wordCloudChart" style="height: 100%; width: 100%;"></div>
              <div v-if="hotKeywords.length === 0" class="empty-state">
                <div class="empty-icon">🕊️</div>
                <div class="empty-text">暂无词云数据</div>
                <div class="empty-desc">请等待更多游客对话</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 满意度趋势 -->
      <el-row style="margin-top: 20px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header>
              <span class="chart-title">📊 游客满意度趋势（近30天）</span>
            </template>
            <div ref="satisfactionChart" style="height: 300px; width: 100%;"></div>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import 'echarts-wordcloud'
import { ref, onMounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// ===================== KPI 卡片配色 =====================
const kpiColors = [
  { border: '#2c6e8a', icon: '#2c6e8a' },
  { border: '#10b981', icon: '#10b981' },
  { border: '#f59e0b', icon: '#f59e0b' },
  { border: '#8b5cf6', icon: '#8b5cf6' }
]

// ===================== 响应式数据 =====================
const loading = ref(true)
const kpiList = ref([
  { icon: '👥', title: '今日服务人次', value: 0, borderColor: '#2c6e8a', iconColor: '#2c6e8a' },
  { icon: '📅', title: '近7天服务人次', value: 0, borderColor: '#10b981', iconColor: '#10b981' },
  { icon: '⚡', title: '平均响应延迟', value: '0 s', borderColor: '#f59e0b', iconColor: '#f59e0b' },
  { icon: '💬', title: '累计会话总数', value: 0, borderColor: '#8b5cf6', iconColor: '#8b5cf6' }
])

const hotKeywords = ref([])
const keywordDateRange = computed(() => {
  const now = new Date()
  const d = new Date()
  d.setDate(d.getDate() - 6)
  return `${d.getMonth()+1}月${d.getDate()}日-${now.getMonth()+1}月${now.getDate()}日`
})

// 图表引用
const trendChart = ref(null)
const satisfactionChart = ref(null)
const wordCloudChart = ref(null)

// ===================== 加载数据 =====================
const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, keywordsRes, satisfactionRes] = await Promise.all([
      request.get('/api/admin/dashboard/stats', { params: { days: 7 } }),
      request.get('/api/admin/dashboard/keywords', { params: { days: 7, limit: 25 } }),
      request.get('/api/admin/dashboard/satisfaction-trend', { params: { days: 30 } })
    ])

    // ---- 处理统计 ----
    if (statsRes.code === 0) {
      const { stats = {} } = statsRes.data
      const todayCount = stats.today_count || 0
      const totalConversations = stats.total_conversations || 0
      const avgResponseTime = stats.avg_response_time || 0

      let weekCount = 0
      if (stats.daily_stats && stats.daily_stats.length > 0) {
        const days = stats.daily_stats.slice(-7)
        weekCount = days.reduce((sum, d) => sum + d.count, 0)
      }

      const colors = [
        { border: '#2c6e8a', icon: '#2c6e8a' },
        { border: '#10b981', icon: '#10b981' },
        { border: '#f59e0b', icon: '#f59e0b' },
        { border: '#8b5cf6', icon: '#8b5cf6' }
      ]

      kpiList.value = [
        { icon: '👥', title: '今日服务人次', value: todayCount, borderColor: colors[0].border, iconColor: colors[0].icon },
        { icon: '📅', title: '近7天服务人次', value: weekCount, borderColor: colors[1].border, iconColor: colors[1].icon },
        { icon: '⚡', title: '平均响应延迟', value: avgResponseTime.toFixed(1) + ' s', borderColor: colors[2].border, iconColor: colors[2].icon },
        { icon: '💬', title: '累计会话总数', value: totalConversations, borderColor: colors[3].border, iconColor: colors[3].icon }
      ]
    }

    // ---- 处理词云 ----
    let keywordData = []
    if (keywordsRes.code === 0) {
      keywordData = keywordsRes.data || []
      hotKeywords.value = keywordData
    }

    // ---- 处理满意度趋势 ----
    let satisfactionData = []
    if (satisfactionRes.code === 0) {
      satisfactionData = satisfactionRes.data || []
    }

    await nextTick()
    setTimeout(() => {
      if (statsRes.code === 0 && statsRes.data.stats && statsRes.data.stats.daily_stats) {
        renderTrendChart(statsRes.data.stats.daily_stats)
      }
      renderSatisfactionChart(satisfactionData)
      renderWordCloud()
    }, 200)

  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('数据加载失败，请刷新重试')
  } finally {
    loading.value = false
  }
}

// ===================== 渲染趋势图 =====================
const renderTrendChart = (dailyStats) => {
  const container = trendChart.value
  if (!container) return

  try {
    const chart = echarts.getInstanceByDom(container) || echarts.init(container)
    const dateList = Array.from({ length: 7 }, (_, i) => {
      const d = new Date()
      d.setDate(d.getDate() - (6 - i))
      return `${d.getMonth() + 1}月${d.getDate()}日`
    })
    const counts = dateList.map(dateStr => {
      const match = dailyStats.find(d => {
        const dDate = new Date(d.date)
        return `${dDate.getMonth() + 1}月${dDate.getDate()}日` === dateStr
      })
      return match ? match.count : 0
    })
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 20, bottom: 30, left: 50, right: 60 },
      xAxis: { type: 'category', data: dateList, axisLabel: { rotate: 0, fontSize: 12 } },
      yAxis: { type: 'value', name: '人次', nameTextStyle: { color: '#8aa8b8' } },
      series: [{
        type: 'line',
        data: counts,
        smooth: true,
        lineStyle: { color: '#2c6e8a', width: 3 },
        areaStyle: { opacity: 0.2, color: '#2c6e8a' },
        symbol: 'circle',
        symbolSize: 8
      }]
    })
    chart.resize()
  } catch (e) {
    console.warn('趋势图渲染失败:', e)
  }
}

// ===================== 渲染满意度趋势图 =====================
const renderSatisfactionChart = (data) => {
  const container = satisfactionChart.value
  if (!container) {
    setTimeout(() => renderSatisfactionChart(data), 200)
    return
  }

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(() => renderSatisfactionChart(data), 200)
    return
  }

  try {
    let chart = echarts.getInstanceByDom(container)
    if (!chart) {
      chart = echarts.init(container)
    }

    const validData = data.filter(d => d.satisfaction !== null)

    if (validData.length === 0) {
      chart.clear()
      chart.setOption({
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#999', fontSize: 16, fontWeight: 'normal' }
        }
      })
      return
    }

    const dateList = validData.map(d => d.date_display)
    const satisfactionValues = validData.map(d => d.satisfaction)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: function(params) {
          const idx = params[0].dataIndex
          const item = validData[idx]
          return `<strong>${item.date_display}</strong><br/>
                  满意度：<strong>${item.satisfaction}%</strong><br/>
                  正面：${item.positive} 条 | 中性：${item.neutral} 条 | 负面：${item.negative} 条`
        }
      },
      grid: { top: 30, bottom: 40, left: 60, right: 60 },
      xAxis: {
        type: 'category',
        data: dateList,
        axisLabel: {
          rotate: 30,
          fontSize: 11,
          interval: 2
        }
      },
      yAxis: {
        type: 'value',
        name: '满意度 (%)',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' },
        nameTextStyle: { color: '#8aa8b8' }
      },
      series: [{
        type: 'line',
        data: satisfactionValues,
        smooth: true,
        lineStyle: { color: '#3b82f6', width: 3 },
        areaStyle: { opacity: 0.2, color: '#3b82f6' },
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: function(params) {
            const val = params.value
            if (val >= 70) return '#10b981'
            if (val >= 50) return '#f59e0b'
            return '#ef4444'
          }
        },
        markLine: {
          data: [
            { yAxis: 70, label: { formatter: '良好线 70%', color: '#10b981' } },
            { yAxis: 50, label: { formatter: '及格线 50%', color: '#f59e0b' } }
          ],
          lineStyle: { type: 'dashed', color: '#ccc' },
          label: { fontSize: 10, color: '#999' }
        }
      }]
    })

    setTimeout(() => {
      chart.resize()
    }, 50)

    console.log('✅ 满意度趋势图渲染成功')
  } catch (e) {
    console.warn('满意度趋势图渲染失败:', e)
  }
}

// ===================== 渲染词云图 =====================
const renderWordCloud = () => {
  const container = wordCloudChart.value
  if (!container) {
    setTimeout(renderWordCloud, 200)
    return
  }

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(renderWordCloud, 200)
    return
  }

  try {
    let chart = echarts.getInstanceByDom(container)
    if (!chart) {
      chart = echarts.init(container, null, {
        width: rect.width,
        height: rect.height
      })
    }

    const data = hotKeywords.value.map(item => ({
      name: item.keyword,
      value: item.count
    }))

    if (data.length === 0) {
      chart.clear()
      return
    }

    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: function(params) {
          return `<strong>${params.name}</strong><br/>提及次数：<strong>${params.value}</strong> 次`
        },
        backgroundColor: 'rgba(255,255,255,0.9)',
        borderColor: '#2c6e8a',
        borderWidth: 2,
        padding: [10, 15],
        textStyle: { color: '#333', fontSize: 14 }
      },
      series: [{
        type: 'wordCloud',
        gridSize: 12,
        sizeRange: [18, 58],
        rotationRange: [0, 0],
        shape: 'circle',
        width: '100%',
        height: '100%',
        textStyle: {
          color: function() {
            const hue = Math.round(Math.random() * 360)
            return `hsl(${hue}, 70%, 50%)`
          },
          fontWeight: 'bold',
          fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif'
        },
        data: data,
        emphasis: {
          focus: 'self',
          textStyle: {
            shadowBlur: 10,
            shadowColor: '#333'
          }
        }
      }]
    })

    setTimeout(() => {
      chart.resize()
    }, 50)

    console.log('✅ 词云图渲染成功，关键词数:', data.length)
  } catch (e) {
    console.warn('词云图渲染失败:', e)
  }
}

// ===================== 刷新数据 =====================
const refreshData = () => {
  ElMessage.info('正在刷新数据...')
  loadData()
}

// ===================== 生命周期 =====================
onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* ===== KPI 卡片 ===== */
.kpi-card {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
  cursor: default;
}
.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(44, 110, 138, 0.12);
}
.kpi-card :deep(.el-card__body) {
  padding: 20px 24px;
}

.kpi-icon {
  position: absolute;
  right: 60px;
  top: 20px;
  font-size: 36px;
  opacity: 0.15;
}
.kpi-title {
  font-size: 14px;
  color: #6a8a9a;
  font-weight: 500;
  letter-spacing: 0.3px;
}
.kpi-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a3a4a;
  margin-top: 6px;
  letter-spacing: -0.5px;
}

/* ===== 图表卡片 ===== */
.chart-card {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}
.chart-card:hover {
  box-shadow: 0 4px 24px rgba(44, 110, 138, 0.06);
}
.chart-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(44, 110, 138, 0.06);
  background: rgba(255, 255, 255, 0.3);
}
.chart-card :deep(.el-card__body) {
  padding: 16px 20px 20px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a3a4a;
}

.refresh-btn {
  float: right;
  font-size: 12px;
  color: #2c6e8a;
  border-color: rgba(44, 110, 138, 0.2);
  background: rgba(44, 110, 138, 0.04);
}
.refresh-btn:hover {
  background: rgba(44, 110, 138, 0.1);
  border-color: #2c6e8a;
}

/* ===== 加载 ===== */
.loading-container {
  padding: 40px;
  text-align: center;
}
.loading-text {
  margin-top: 20px;
  color: #909399;
  font-size: 14px;
}

/* ===== 空状态 ===== */
.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  text-align: center;
  pointer-events: none;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}
.empty-text {
  font-size: 16px;
  color: #8aa8b8;
  margin-bottom: 4px;
}
.empty-desc {
  font-size: 13px;
  color: #b0c8d8;
}
</style>