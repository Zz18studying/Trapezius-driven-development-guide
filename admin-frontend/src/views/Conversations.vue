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
            <el-option label="😊 正面" value="positive" />
            <el-option label="😡 负面" value="negative" />
          </el-select>
        </el-col>
        <el-col :span="7">
          <el-input
            v-model="searchSessionId"
            placeholder="搜索会话ID（支持部分匹配）"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" plain @click="exportData">导出</el-button>
        </el-col>
      </el-row>
      <div style="margin-top: 10px; font-size: 13px; color: #999;">
        💡 共 {{ total }} 个会话，点击卡片查看完整对话
      </div>
    </el-card>

    <!-- 会话卡片列表 -->
    <div v-if="loading" class="loading-text">加载中...</div>
    <div v-else-if="sessions.length === 0" class="empty-text">
      <div class="empty-icon">📭</div>
      <div>暂无对话记录</div>
    </div>
    <div v-else class="session-list">
      <el-card
        v-for="session in sessions"
        :key="session.session_id"
        class="session-card"
        shadow="hover"
        @click="openSessionDialog(session)"
      >
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="session-id">{{ session.session_id }}</span>
              <span class="session-turns">共 {{ session.total_turns }} 轮</span>
            </div>
            <div class="header-right">
              <el-tag size="small" type="success">
                😊 {{ session.sentiment_stats.positive }}
              </el-tag>
              <el-tag size="small" type="warning">
                😐 {{ session.sentiment_stats.neutral }}
              </el-tag>
              <el-tag size="small" type="danger">
                😡 {{ session.sentiment_stats.negative }}
              </el-tag>
              <span class="session-time">{{ session.conversations[0]?.created_at || '' }}</span>
            </div>
          </div>
        </template>
        <div class="card-content">
          <div v-if="session.conversations.length > 0" class="preview-message">
            <el-icon><ChatDotRound /></el-icon>
            <span>{{ session.conversations[0].user_question }}</span>
          </div>
          <div class="card-hint">点击查看完整对话 →</div>
        </div>
      </el-card>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </div>

    <!-- 会话详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="'会话详情：' + currentSession?.session_id"
      width="80%"
      top="5vh"
    >
      <div v-if="currentSession" class="dialog-content">
        <div class="dialog-stats">
          <span>共 {{ currentSession.total_turns }} 轮对话</span>
          <span>😊 {{ currentSession.sentiment_stats.positive }}</span>
          <span>😐 {{ currentSession.sentiment_stats.neutral }}</span>
          <span>😡 {{ currentSession.sentiment_stats.negative }}</span>
        </div>
        <el-timeline>
          <el-timeline-item
            v-for="conv in currentSession.conversations"
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
              <!-- 用户问题 -->
              <div style="margin-bottom: 4px; font-size: 14px; padding: 4px 8px; background: #f0f4f8; border-radius: 4px;">
                <strong>用户：</strong>{{ conv.user_question }}
              </div>
              <!-- AI回答 -->
              <div style="font-size: 14px; padding: 4px 8px; background: #e8f5e9; border-radius: 4px;">
                <strong>小灵：</strong>{{ conv.ai_answer }}
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportSession">导出会话</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
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

// 对话框
const dialogVisible = ref(false)
const currentSession = ref(null)

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

const openSessionDialog = (session) => {
  currentSession.value = session
  dialogVisible.value = true
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

const exportSession = () => {
  if (!currentSession.value) return
  const session = currentSession.value
  let text = `会话ID：${session.session_id}\n`
  text += `导出时间：${new Date().toLocaleString()}\n`
  text += `总轮数：${session.total_turns}\n`
  text += `情绪统计：正面 ${session.sentiment_stats.positive}，中性 ${session.sentiment_stats.neutral}，负面 ${session.sentiment_stats.negative}\n`
  text += '='.repeat(60) + '\n\n'
  
  session.conversations.forEach(conv => {
    text += `[第${conv.turn}轮] ${conv.created_at} [${conv.sentiment}]\n`
    text += `问：${conv.user_question}\n`
    text += `答：${conv.ai_answer}\n`
    text += '-'.repeat(40) + '\n'
  })

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `会话_${session.session_id}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('导出成功！')
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
  font-size: 16px;
}

.empty-text {
  text-align: center;
  color: #999;
  padding: 60px 0;
  font-size: 16px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.session-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.session-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 12px;
}
.session-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  flex-wrap: wrap;
  gap: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.session-id {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #1a3a4a;
  background: #f0f4f8;
  padding: 2px 10px;
  border-radius: 6px;
}

.session-turns {
  font-size: 13px;
  color: #6a8a9a;
}

.session-time {
  font-size: 12px;
  color: #999;
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.preview-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
}
.preview-message .el-icon {
  font-size: 18px;
  color: #5ba3c7;
  flex-shrink: 0;
}
.preview-message span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-hint {
  font-size: 13px;
  color: #5ba3c7;
  flex-shrink: 0;
}

.dialog-content {
  max-height: 70vh;
  overflow-y: auto;
}

.dialog-stats {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #475569;
}
.dialog-stats span {
  font-weight: 500;
}

:deep(.el-timeline) {
  padding: 0;
}
:deep(.el-timeline-item__content) {
  padding: 0;
}
:deep(.el-card__body) {
  padding: 12px 16px;
}
</style>