<template>
  <div>
    <!-- 筛选栏 -->
    <el-card>
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-date-picker
            v-model="searchDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            @change="handleSearch"
          />
        </el-col>
        <el-col :span="5">
          <el-select v-model="searchSentiment" placeholder="全部情绪" clearable style="width: 100%" @change="handleSearch">
            <el-option label="全部会话" value="" />
            <el-option label="😊 含正面" value="positive" />
            <el-option label="😐 含中性" value="neutral" />
            <el-option label="😡 含负面" value="negative" />
          </el-select>
        </el-col>
        <el-col :span="7">
          <el-input v-model="searchSessionId" placeholder="搜索会话ID" clearable @keyup.enter="handleSearch" />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" plain @click="exportData">导出</el-button>
        </el-col>
      </el-row>
      <div style="margin-top: 10px; font-size: 13px; color: #999;">
        💡 默认按会话分组展示完整对话，共 {{ total }} 个会话
      </div>
    </el-card>

    <!-- 统计信息 -->
    <el-card style="margin-top: 20px">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总会话数" :value="total" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="😊 含正面" :value="stats.positive || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="😐 含中性" :value="stats.neutral || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="😡 含负面" :value="stats.negative || 0" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 会话列表（按 session_id 分组） -->
    <el-card style="margin-top: 20px">
      <div v-if="loading" class="loading-text">加载中...</div>
      <div v-else-if="sessions.length === 0" class="empty-text">暂无对话记录</div>
      <div v-else>
        <!-- 每个会话一个卡片 -->
        <el-collapse v-model="activeNames" accordion>
          <el-collapse-item
            v-for="(session, index) in sessions"
            :key="session.session_id"
            :name="index"
          >
            <template #title>
              <div style="display: flex; align-items: center; gap: 16px; width: 100%;">
                <el-tag type="info" size="small">{{ session.session_id }}</el-tag>
                <span style="font-size: 13px; color: #666;">共 {{ session.total_turns }} 轮</span>
                <span style="font-size: 13px; color: #666;">
                  😊 {{ session.sentiment_stats.positive }}
                  😐 {{ session.sentiment_stats.neutral }}
                  😡 {{ session.sentiment_stats.negative }}
                </span>
                <span style="font-size: 12px; color: #999; margin-left: auto;">
                  {{ session.conversations[0]?.created_at || '' }}
                </span>
              </div>
            </template>

            <!-- 会话内的完整对话 -->
            <el-timeline>
              <el-timeline-item
                v-for="conv in session.conversations"
                :key="conv.turn"
                :timestamp="conv.created_at"
                :type="getTimelineType(conv.sentiment)"
                placement="top"
              >
                <el-card shadow="hover" :body-style="{ padding: '12px 16px' }">
                  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <el-tag :type="getTagType(conv.sentiment)" size="small">
                      {{ getSentimentLabel(conv.sentiment) }}
                    </el-tag>
                    <span style="font-size: 12px; color: #999;">第 {{ conv.turn }} 轮</span>
                    <span style="font-size: 12px; color: #999; margin-left: auto;">响应 {{ conv.response_time }}s</span>
                  </div>
                  <div style="color: #409EFF; margin-bottom: 4px; font-size: 14px;">
                    <strong>👤 用户：</strong>{{ conv.user_question }}
                  </div>
                  <div style="color: #67C23A; font-size: 14px;">
                    <strong>🤖 小灵：</strong>{{ conv.ai_answer }}
                  </div>
                </el-card>
              </el-timeline-item>
            </el-timeline>
          </el-collapse-item>
        </el-collapse>

        <!-- 分页 -->
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadData"
          style="margin-top: 16px; justify-content: flex-end"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const API_BASE = '/api/admin'

// 筛选条件
const searchDate = ref(new Date().toISOString().slice(0, 10))
const searchSentiment = ref('')
const searchSessionId = ref('')

// 数据
const sessions = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const activeNames = ref([])

// 统计
const stats = computed(() => {
  const s = { positive: 0, neutral: 0, negative: 0 }
  sessions.value.forEach(session => {
    s.positive += session.sentiment_stats.positive || 0
    s.neutral += session.sentiment_stats.neutral || 0
    s.negative += session.sentiment_stats.negative || 0
  })
  return s
})

// ============================================================
// 工具函数
// ============================================================
const getTagType = (sentiment) => {
  const map = { positive: 'success', neutral: 'warning', negative: 'danger' }
  return map[sentiment] || 'info'
}

const getSentimentLabel = (sentiment) => {
  const map = { positive: '😊 正面', neutral: '😐 中性', negative: '😡 负面' }
  return map[sentiment] || '未知'
}

const getTimelineType = (sentiment) => {
  const map = { positive: 'success', neutral: 'warning', negative: 'danger' }
  return map[sentiment] || 'primary'
}

// ============================================================
// 数据加载
// ============================================================
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      date: searchDate.value,
      page: page.value,
      page_size: pageSize.value
    }
    if (searchSentiment.value) params.sentiment = searchSentiment.value
    if (searchSessionId.value) params.session_id = searchSessionId.value

    const res = await axios.get(`${API_BASE}/conversations/by-session`, { params })
    if (res.data.code === 0) {
      sessions.value = res.data.data.items
      total.value = res.data.data.total
      // 默认展开第一个
      if (sessions.value.length > 0) {
        activeNames.value = [0]
      }
    } else {
      ElMessage.warning(res.data.msg || '查询失败')
    }
  } catch (err) {
    console.error('加载失败:', err)
    ElMessage.error('加载对话记录失败')
  } finally {
    loading.value = false
  }
}

// ============================================================
// 操作函数
// ============================================================
const handleSearch = () => {
  page.value = 1
  loadData()
}

const resetFilters = () => {
  searchDate.value = new Date().toISOString().slice(0, 10)
  searchSentiment.value = ''
  searchSessionId.value = ''
  page.value = 1
  loadData()
}

const exportData = async () => {
  try {
    const params = {
      date: searchDate.value,
      page: 1,
      page_size: 9999
    }
    if (searchSentiment.value) params.sentiment = searchSentiment.value
    if (searchSessionId.value) params.session_id = searchSessionId.value

    const res = await axios.get(`${API_BASE}/conversations/by-session`, { params })
    if (res.data.code === 0) {
      let text = `会话导出报告\n`
      text += `导出时间：${new Date().toLocaleString()}\n`
      text += `日期范围：${searchDate.value}\n`
      text += `情感筛选：${searchSentiment.value || '全部'}\n`
      text += `共计：${res.data.data.total} 个会话\n`
      text += '='.repeat(60) + '\n\n'
      
      res.data.data.items.forEach((session, idx) => {
        text += `[会话 ${idx + 1}] ${session.session_id}\n`
        text += `总轮数：${session.total_turns}\n`
        text += `情绪统计：正面 ${session.sentiment_stats.positive}，中性 ${session.sentiment_stats.neutral}，负面 ${session.sentiment_stats.negative}\n`
        text += '-'.repeat(40) + '\n'
        session.conversations.forEach(conv => {
          text += `  [第${conv.turn}轮] ${conv.created_at} [${conv.sentiment}]\n`
          text += `  问：${conv.user_question}\n`
          text += `  答：${conv.ai_answer}\n`
          text += '\n'
        })
        text += '='.repeat(60) + '\n\n'
      })

      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `会话报告_${searchDate.value}_${new Date().toISOString().slice(0, 10)}.txt`
      link.click()
      URL.revokeObjectURL(link.href)
      ElMessage.success('导出成功！')
    }
  } catch (err) {
    console.error('导出失败:', err)
    ElMessage.error('导出失败')
  }
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.loading-text {
  text-align: center;
  color: #999;
  padding: 40px 0;
}

.empty-text {
  text-align: center;
  color: #999;
  padding: 40px 0;
  font-size: 16px;
}

:deep(.el-collapse-item__header) {
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e8ecf0;
}

:deep(.el-collapse-item__wrap) {
  border: 1px solid #e8ecf0;
  border-top: none;
  border-radius: 0 0 8px 8px;
}

:deep(.el-collapse-item__content) {
  padding: 16px;
}

:deep(.el-timeline) {
  padding: 0;
}

:deep(.el-timeline-item__content) {
  padding: 0;
}

:deep(.el-card) {
  border-radius: 8px;
}
</style>