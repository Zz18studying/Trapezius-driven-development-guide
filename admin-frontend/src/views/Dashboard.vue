<template>
  <div class="dashboard">
    <!-- ===== 加载状态 ===== -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
      <div class="loading-text">正在加载数据...</div>
    </div>

    <!-- ===== 数据内容 ===== -->
    <template v-else>
      <!-- KPI 卡片 -->
      <el-row :gutter="20">
        <el-col :span="6" v-for="(item, index) in kpiList" :key="index">
          <el-card class="kpi-card" shadow="hover">
            <div class="kpi-icon">{{ item.icon }}</div>
            <div class="kpi-title">{{ item.title }}</div>
            <div class="kpi-value">{{ item.value }}</div>
            <div class="kpi-trend" :class="item.trendClass">{{ item.trend }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 图表行 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>近7天服务人次趋势</span>
              <el-button size="small" style="float: right" @click="refreshData">刷新</el-button>
            </template>
            <div ref="trendChart" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
  <el-card>
    <template #header>热门话题词云</template>
    <div ref="wordCloudChart" style="height: 300px"></div>
    <!-- 无数据时显示空状态 -->
    <div v-if="hotTopics.length === 0" class="empty-state" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
      <div class="empty-icon">🕊️</div>
      <div class="empty-text">暂无热门话题数据</div>
      <div class="empty-desc">请等待更多游客对话</div>
    </div>
  </el-card>
</el-col>
      </el-row>

      <!-- 满意度趋势 -->
      <el-row style="margin-top: 20px">
        <el-col :span="24">
          <el-card>
            <template #header>游客满意度趋势（近30天）</template>
            <div ref="satisfactionChart" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import 'echarts-wordcloud'
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

// ===================== 响应式数据 =====================
const loading = ref(true)
const kpiList = ref([
  { icon: '👥', title: '今日服务人次', value: 0, trend: '', trendClass: '' },
  { icon: '📅', title: '本周服务人次', value: 0, trend: '', trendClass: '' },
  { icon: '⚡', title: '平均响应延迟', value: '0 s', trend: '', trendClass: '' },
  { icon: '💬', title: '累计会话总数', value: 0, trend: '', trendClass: '' }
])

const hotTopics = ref([])

// 图表引用
const trendChart = ref(null)
const satisfactionChart = ref(null)
const wordCloudChart = ref(null)

// ===================== 假数据（模拟后端返回） =====================
const mockData = {
  stats: {
    today_count: 324,
    total_conversations: 8732,
    avg_response_time: 2.3,
    daily_stats: [
      { date: '2026-06-12', count: 220 },
      { date: '2026-06-13', count: 245 },
      { date: '2026-06-14', count: 278 },
      { date: '2026-06-15', count: 301 },
      { date: '2026-06-16', count: 289 },
      { date: '2026-06-17', count: 324 },
      { date: '2026-06-18', count: 356 }
    ]
  },
  hot_topics: [
    { topic: '开放时间', count: 15 },
    { topic: '门票价格', count: 12 },
    { topic: '交通路线', count: 8 },
    { topic: '祈福体验', count: 6 },
    { topic: '景点介绍', count: 5 }
  ]
}

// ===================== 加载数据 =====================
const loadData = async () => {
  loading.value = true
  try {
    // 模拟 API 请求延迟
    await new Promise(resolve => setTimeout(resolve, 800))

    // 使用假数据（后续替换为真实 API 调用）
    const { stats, hot_topics } = mockData

    // 更新 KPI
    const todayCount = stats.today_count || 0
    const totalConversations = stats.total_conversations || 0
    const avgResponseTime = stats.avg_response_time || 0

    let weekCount = 0
    if (stats.daily_stats && stats.daily_stats.length > 0) {
      const days = stats.daily_stats.slice(-7)
      weekCount = days.reduce((sum, d) => sum + d.count, 0)
    }

    kpiList.value = [
      { icon: '👥', title: '今日服务人次', value: todayCount, trend: '', trendClass: '' },
      { icon: '📅', title: '本周服务人次', value: weekCount, trend: '', trendClass: '' },
      { icon: '⚡', title: '平均响应延迟', value: avgResponseTime.toFixed(1) + ' s', trend: '', trendClass: '' },
      { icon: '💬', title: '累计会话总数', value: totalConversations, trend: '', trendClass: '' }
    ]

    // 更新热门话题
    hotTopics.value = hot_topics || []

    // 等待 DOM 更新后渲染图表
    await nextTick()
    renderCharts(stats.daily_stats || [])

  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('数据加载失败，请刷新重试')
  } finally {
    loading.value = false
  }
}

// ===================== 渲染图表 =====================
const renderCharts = (dailyStats) => {
  console.log('echarts 模块:', echarts)
  console.log('趋势图容器:', trendChart.value)
  console.log('满意度容器:', satisfactionChart.value)
   if (!trendChart.value) {
    setTimeout(() => renderCharts(dailyStats), 300)
    return
  }
  // 1. 趋势图
  if (trendChart.value) {
    const chart = echarts.getInstanceByDom(trendChart.value) || echarts.init(trendChart.value)
    const dates = dailyStats.map(d => d.date.slice(5))
    const counts = dailyStats.map(d => d.count)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates.length ? dates : ['暂无数据'] },
      yAxis: { type: 'value', name: '人次' },
      series: [{
        type: 'line',
        data: counts.length ? counts : [0],
        smooth: true,
        lineStyle: { color: '#10b981', width: 3 },
        areaStyle: { opacity: 0.2, color: '#10b981' },
        symbol: 'circle',
        symbolSize: 8
      }]
    })
    window.addEventListener('resize', () => chart.resize())
  }

    // 2. 满意度趋势图
  if (satisfactionChart.value) {
    const chart = echarts.getInstanceByDom(satisfactionChart.value) || echarts.init(satisfactionChart.value)
    
    // 【修复】将数据生成逻辑移至 setOption 之前
    const satisfactionData = Array.from({ length: 30 }, (_, i) => 80 + Math.floor(Math.random() * 15))
    const dateList = Array.from({ length: 30 }, (_, i) => {
      const d = new Date()
      d.setDate(d.getDate() - (29 - i))
      return `${d.getMonth() + 1}月${d.getDate()}日`
    })

    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { 
        type: 'category', 
        data: dateList, // 【修复】直接引用上方定义的变量
        axisLabel: {
          rotate: 30,
          fontSize: 11
        }
      },
      yAxis: { type: 'value', name: '满意度 (%)', min: 70, max: 100 },
      series: [{
        type: 'line',
        data: satisfactionData, // 【修复】直接引用上方定义的变量
        smooth: true,
        lineStyle: { color: '#3b82f6', width: 3 },
        areaStyle: { opacity: 0.2, color: '#3b82f6' }
      }]
    })
    window.addEventListener('resize', () => chart.resize())
  }
  // 3. 词云图（显示 TOP 10）
  if (wordCloudChart.value && hotTopics.value.length > 0) {
  const chart = echarts.getInstanceByDom(wordCloudChart.value) || echarts.init(wordCloudChart.value)
  
  const data = hotTopics.value.slice(0, 10).map(item => ({
    name: item.topic,
    value: item.count
  }))

  chart.setOption({
    // 添加 tooltip
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        return `<strong>${params.name}</strong><br/>提及次数：<strong>${params.value}</strong> 次`
      },
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderColor: '#10b981',
      borderWidth: 2,
      padding: [10, 15],
      textStyle: {
        color: '#333',
        fontSize: 14
      }
    },
    series: [{
      type: 'wordCloud',
      gridSize: 12,
      sizeRange: [16, 48],
      rotationRange: [-0, 0],
      shape: 'circle',
      width: '100%',
      height: '100%',
      textStyle: {
        color: function () {
          return 'hsl(' + Math.round(Math.random() * 360) + ', 70%, 50%)'
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
  chart.resize()
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
.kpi-card {
  position: relative;
  overflow: hidden;
}
.kpi-icon {
  position: absolute;
  right: 20px;
  top: 20px;
  font-size: 36px;
  opacity: 0.2;
}
.kpi-title {
  font-size: 14px;
  color: var(--text-gray);
}
.kpi-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary-color);
  margin: 10px 0;
}
.trend-up {
  color: #10b981;
  font-size: 12px;
}

/* 加载状态 */
.loading-container {
  padding: 40px;
  text-align: center;
}
.loading-text {
  margin-top: 20px;
  color: #909399;
  font-size: 14px;
}

/* 空状态 */
.empty-state {
  padding: 30px 0;
  text-align: center;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 4px;
}
.empty-desc {
  font-size: 13px;
  color: #909399;
}
</style>