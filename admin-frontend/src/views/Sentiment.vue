<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>近7天情感倾向分布</template>
          <div ref="emotionPie" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>游客关注点 TOP6</template>
          <el-table :data="topConcerns" stripe>
            <el-table-column prop="keyword" label="关注点" />
            <el-table-column prop="count" label="提及次数" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>服务建议（基于情感分析）</template>
          <div class="suggestion-box">
            {{ serviceSuggestion }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-button type="primary" @click="exportReport">导出报告（模拟）</el-button>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const emotionPie = ref(null)
const topConcerns = ref([
  { keyword: '门票价格', count: 245 },
  { keyword: '路线指引', count: 189 },
  { keyword: '历史故事', count: 156 },
  { keyword: '排队时间', count: 98 },
  { keyword: '餐饮服务', count: 77 },
  { keyword: '卫生间位置', count: 66 }
])

const serviceSuggestion = ref('根据近期游客反馈，排队时间提及率上升12%，建议在高峰时段增加疏导广播；游客对历史故事需求强烈，可考虑增设语音讲解二维码。')

onMounted(() => {
  if (emotionPie.value) {
    const chart = echarts.init(emotionPie.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { top: 'bottom' },
      series: [{
        type: 'pie',
        radius: '55%',
        data: [
          { name: '正面情感', value: 68, itemStyle: { color: '#10b981' } },
          { name: '中性情感', value: 22, itemStyle: { color: '#f59e0b' } },
          { name: '负面情感', value: 10, itemStyle: { color: '#ef4444' } }
        ],
        emphasis: { scale: true },
        label: { show: true, formatter: '{b}: {d}%' }
      }]
    })
  }
})

const exportReport = () => {
  ElMessage.success('报告导出功能模拟：实际项目中将生成PDF/Excel文件')
}
</script>

<style scoped>
.suggestion-box {
  padding: 16px;
  background-color: #ecfdf5;
  border-radius: 12px;
  border-left: 4px solid var(--primary-color);
  line-height: 1.6;
}
</style>