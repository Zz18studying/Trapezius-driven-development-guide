<template>
  <div class="conversations-page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-header">
      <div>
        <h2 class="page-title">💬 对话查询</h2>
        <p class="page-desc">按日期、情绪或会话 ID 检索游客对话记录，支持导出分析</p>
      </div>
      <div class="page-actions">
        <el-tag type="info" size="large" style="font-size: 14px; padding: 8px 16px;">
          共 {{ total }} 个会话
        </el-tag>
      </div>
    </div>

    <!-- ===== 筛选栏 ===== -->
    <el-card class="filter-card" shadow="hover">
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
          <el-select
            v-model="searchSentiment"
            placeholder="全部情绪"
            clearable
            style="width: 100%"
            @change="handleSearch"
          >
            <el-option label="全部会话" value="" />
            <el-option label="😊 正面" value="positive" />
            <el-option label="😡 负面" value="negative" />
          </el-select>
        </el-col>
        <el-col :span="7">
          <el-input
            v-model="searchSessionId"
            placeholder="搜索会话ID，如 lingshan_20260703_0001"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" @click="exportData">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </el-col>
      </el-row>
      <div class="filter-hint">
        💡 ID 格式为 <strong>lingshan_YYYYMMDD_XXXX</strong>，点击卡片查看完整对话
      </div>
    </el-card>

    <!-- ===== 会话卡片列表 ===== -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>
    <div v-else-if="sessions.length === 0" class="empty-state">
      <div class="empty-icon">📭</div>
      <div class="empty-title">暂无对话记录</div>
      <div class="empty-desc">尝试调整筛选条件或选择其他日期</div>
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
          <div class="card-hint">查看完整对话 →</div>
        </div>
      </el-card>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadData"
        />
      </div>
    </div>

    <!-- ===== 会话详情对话框 ===== -->
    <el-dialog
      v-model="dialogVisible"
      :title="'会话详情：' + currentSession?.session_id"
      width="80%"
      top="5vh"
      class="history-dialog"
    >
      <div v-if="currentSession" class="dialog-content">
        <div class="dialog-stats">
          <span><span class="stat-icon">📝</span> 共 {{ currentSession.total_turns }} 轮</span>
          <span class="stat-positive">😊 {{ currentSession.sentiment_stats.positive }}</span>
          <span class="stat-neutral">😐 {{ currentSession.sentiment_stats.neutral }}</span>
          <span class="stat-negative">😡 {{ currentSession.sentiment_stats.negative }}</span>
        </div>
        <el-timeline>
          <el-timeline-item
            v-for="conv in currentSession.conversations"
            :key="conv.turn"
            :timestamp="conv.created_at"
            :type="getTimelineType(conv.sentiment)"
            placement="top"
          >
            <el-card shadow="hover" class="history-message-card">
              <div class="history-message-header">
                <el-tag :type="getTagType(conv.sentiment)" size="small">
                  {{ getSentimentLabel(conv.sentiment) }}
                </el-tag>
                <span class="turn-label">第 {{ conv.turn }} 轮</span>
                <span class="response-time">响应 {{ conv.response_time }}s</span>
              </div>
              <div class="history-message-body">
                <div class="user-question">
                  <strong>用户：</strong>{{ conv.user_question }}
                </div>
                <div class="ai-answer">
                  <strong>小灵：</strong>{{ conv.ai_answer }}
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" plain @click="exportSession">
          <el-icon><Download /></el-icon>
          导出会话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Download } from '@element-plus/icons-vue'
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
/* ===== 页面布局 ===== */
.conversations-page {
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

/* ===== 筛选栏卡片 ===== */
.filter-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
  margin-bottom: 20px;
}
.filter-card :deep(.el-card__body) {
  padding: 20px 24px;
}

.filter-hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-light);
}
.filter-hint strong {
  color: var(--text-mid);
  font-weight: 600;
}

/* ===== 加载状态 ===== */
.loading-state {
  padding: 40px 0;
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 60px 0;
}
.empty-icon {
  font-size: 56px;
  opacity: 0.3;
  margin-bottom: 16px;
}
.empty-title {
  font-size: 18px;
  color: var(--text-mid);
  font-weight: 500;
  margin-bottom: 4px;
}
.empty-desc {
  font-size: 14px;
  color: var(--text-light);
}

/* ===== 会话卡片列表 ===== */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 会话卡片 ===== */
.session-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all var(--transition-base);
}
.session-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.session-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.session-card :deep(.el-card__body) {
  padding: 12px 20px 14px;
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
  color: var(--text-dark);
  background: rgba(44, 110, 138, 0.08);
  padding: 2px 12px;
  border-radius: var(--radius-sm);
}
.session-turns {
  font-size: 13px;
  color: var(--text-gray);
}
.session-time {
  font-size: 12px;
  color: var(--text-light);
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0;
}
.preview-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-mid);
  font-size: 14px;
  flex: 1;
  overflow: hidden;
}
.preview-message .el-icon {
  font-size: 18px;
  color: var(--primary-color);
  flex-shrink: 0;
}
.preview-message span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-hint {
  font-size: 13px;
  color: var(--primary-color);
  flex-shrink: 0;
}

/* ===== 分页 ===== */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* ===== 对话框 ===== */
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

.dialog-content {
  max-height: 70vh;
  overflow-y: auto;
}

.dialog-stats {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: rgba(44, 110, 138, 0.04);
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--text-mid);
  flex-wrap: wrap;
}
.dialog-stats span {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}
.stat-icon {
  font-size: 16px;
}
.stat-positive {
  color: #10b981;
}
.stat-neutral {
  color: #f59e0b;
}
.stat-negative {
  color: #ef4444;
}

/* ===== 对话历史消息卡片 ===== */
.history-message-card {
  border-radius: var(--radius-sm) !important;
}
.history-message-card :deep(.el-card__body) {
  padding: 12px 16px !important;
}

.history-message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.turn-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-mid);
}
.response-time {
  font-size: 12px;
  color: var(--text-light);
  margin-left: auto;
}

.history-message-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.user-question {
  font-size: 14px;
  padding: 6px 10px;
  background: rgba(44, 110, 138, 0.04);
  border-radius: var(--radius-sm);
  color: var(--text-dark);
  line-height: 1.6;
}
.ai-answer {
  font-size: 14px;
  padding: 6px 10px;
  background: rgba(16, 185, 129, 0.05);
  border-radius: var(--radius-sm);
  color: #065f46;
  line-height: 1.6;
}

/* ===== 通用覆盖 ===== */
:deep(.el-timeline) {
  padding: 0;
}
:deep(.el-timeline-item__content) {
  padding: 0;
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
  .filter-card :deep(.el-card__body) {
    padding: 14px 16px;
  }
  .filter-card .el-row {
    gap: 10px;
  }
  .filter-card .el-col {
    flex: 1 1 100%;
    max-width: 100%;
  }
  .session-card :deep(.el-card__header) {
    padding: 10px 14px;
  }
  .session-card :deep(.el-card__body) {
    padding: 10px 14px 12px;
  }
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
  .card-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .card-hint {
    align-self: flex-end;
  }
  .dialog-stats {
    gap: 12px;
    font-size: 13px;
    padding: 10px 14px;
  }
  .history-dialog :deep(.el-dialog) {
    width: 95% !important;
  }
  .pagination-wrapper {
    justify-content: center;
  }
}
</style>