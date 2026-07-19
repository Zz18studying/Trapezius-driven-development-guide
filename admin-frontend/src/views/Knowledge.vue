<template>
  <div class="knowledge-page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-header">
      <div>
        <h2 class="page-title">📚 知识库管理</h2>
        <p class="page-desc">管理景区知识文档，AI 将基于这些内容回答游客问题</p>
      </div>
      <el-button type="primary" size="large" @click="dialogUploadVisible = true">
        <el-icon><Upload /></el-icon>
        批量上传知识文档
      </el-button>
    </div>

    <!-- ===== 文档列表 ===== -->
    <el-card class="list-card" shadow="hover">
      <template #header>
        <span class="card-title">📄 文档列表</span>
        <span class="card-subtitle">共 {{ docList.length }} 个文档</span>
      </template>

      <el-table
        :data="docList"
        stripe
        row-key="id"
        style="width: 100%"
        empty-text="暂无文档，请上传知识文件"
      >
        <el-table-column prop="title" label="文档标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="docType" label="文档类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.docType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploadTime" label="上传时间" width="130" align="center" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '已索引' ? 'success' : 'warning'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              class="delete-btn"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ===== 测试知识库问答 ===== -->
    <el-card class="test-card" shadow="hover">
      <template #header>
        <span class="card-title">🔍 测试知识库问答</span>
        <span class="card-subtitle">输入问题，验证 AI 能否从知识库中检索到答案</span>
      </template>

      <div class="test-area">
        <!-- 输入框 + 按钮分行布局 -->
        <div class="test-input-row">
          <el-input
            v-model="testQuestion"
            placeholder="输入一个问题，测试检索效果..."
            size="large"
            clearable
            @keyup.enter="testQuery"
            class="test-input"
          />
          <el-button
            type="primary"
            size="large"
            class="test-btn"
            @click="testQuery"
            :loading="testing"
          >
            <el-icon><Search /></el-icon>
            测试
          </el-button>
        </div>

        <div v-if="testAnswer" class="test-result" :class="{ 'has-error': testAnswer.includes('失败') || testAnswer.includes('未找到') }">
          <div class="result-label">
            <span class="result-icon">📋</span>
            <span>检索结果</span>
          </div>
          <div class="result-content">{{ testAnswer }}</div>
        </div>

        <div v-else-if="tested" class="test-result empty-result">
          <div class="result-label">
            <span class="result-icon">💡</span>
            <span>提示</span>
          </div>
          <div class="result-content">输入问题后点击“测试”按钮，查看检索效果</div>
        </div>
      </div>
    </el-card>

    <!-- ===== 上传对话框 ===== -->
    <el-dialog
      v-model="dialogUploadVisible"
      title="📤 批量上传知识文档"
      width="480px"
      class="upload-dialog"
      @closed="handleDialogClosed"
    >
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        :auto-upload="false"
        :file-list="fileList"
        :on-change="handleFileChange"
        :on-remove="handleRemove"
        accept=".pdf,.docx,.txt"
        multiple
        class="upload-area"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或 <em>点击选择文件</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 <strong>.pdf</strong> · <strong>.docx</strong> · <strong>.txt</strong> 格式
            <br>
            <span style="color: var(--text-light); font-size: 12px;">
              ⚠️ 不支持的文件格式将被自动忽略
            </span>
          </div>
        </template>
      </el-upload>

      <div v-if="fileList.length > 0" class="file-preview">
        <div class="file-preview-title">已选文件 ({{ fileList.length }}个)</div>
        <div v-for="file in fileList" :key="file.uid" class="file-preview-item">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogUploadVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="fileList.length === 0"
          :loading="uploading"
          @click="handleUpload"
        >
          {{ uploading ? '上传中...' : `上传 (${fileList.length}个文件)` }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { UploadFilled, Upload, Delete, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// ===================== 文档列表 =====================
const docList = ref([])
const loading = ref(false)

const loadDocList = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/admin/knowledge/list')
    if (res.code === 0) {
      docList.value = res.data.map(item => ({
        id: item.id,
        title: item.filename,
        docType: item.file_type || '未知',
        uploadTime: item.created_at ? item.created_at.slice(0, 10) : '',
        status: item.status === 'processed' ? '已索引' : '待处理'
      }))
    }
  } catch (error) {
    console.error('加载文档列表失败:', error)
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// ===================== 上传相关 =====================
const dialogUploadVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])
const uploading = ref(false)

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']

const isFileAllowed = (fileName) => {
  if (!fileName || !fileName.includes('.')) return false
  const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase()
  return ALLOWED_EXTENSIONS.includes(ext)
}

const handleFileChange = (file, fileListNew) => {
  const validFiles = fileListNew.filter(f => isFileAllowed(f.name))
  fileList.value = validFiles
}

const handleRemove = (file, fileListNew) => {
  fileList.value = fileListNew
}

const handleDialogClosed = () => {
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  fileList.value = []
}

const handleUpload = async () => {
  const validFiles = fileList.value.filter(f => isFileAllowed(f.name))
  if (validFiles.length === 0) {
    ElMessage.warning('请选择 .pdf, .docx, .txt 格式的文件')
    return
  }

  uploading.value = true
  let successCount = 0

  for (const file of validFiles) {
    const formData = new FormData()
    formData.append('file', file.raw)
    try {
      const res = await request.post('/api/admin/knowledge/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.code === 0) successCount++
    } catch (error) {
      console.error('上传失败:', file.name, error)
    }
  }

  uploading.value = false
  ElMessage.success(`成功上传 ${successCount} 个文件`)
  await loadDocList()
  uploadRef.value.clearFiles()
  fileList.value = []
  dialogUploadVisible.value = false
}

// ===================== 删除 =====================
const handleDelete = async (row) => {
  try {
    await request.delete(`/api/admin/knowledge/${row.id}`)
    ElMessage.success('删除成功')
    await loadDocList()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

// ===================== 测试检索 =====================
const testQuestion = ref('')
const testAnswer = ref('')
const tested = ref(false)
const testing = ref(false)

const testQuery = async () => {
  if (!testQuestion.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  testing.value = true
  tested.value = true

  try {
    const res = await request.post('/api/admin/knowledge/test', {
      question: testQuestion.value,
      n_results: 3
    })
    if (res.code === 0) {
      const results = res.data.results
      if (results && results.length > 0) {
        testAnswer.value = results.map((r, i) =>
          `【${i+1}】问题：${r.question || '相关内容'}\n   答案：${r.answer || '无具体答案'}`
        ).join('\n\n')
      } else {
        testAnswer.value = '未找到相关内容，请尝试更换问题'
      }
    } else {
      testAnswer.value = '检索失败：' + (res.msg || '未知错误')
    }
  } catch (error) {
    console.error('测试查询失败:', error)
    testAnswer.value = '请求失败，请检查网络连接'
  } finally {
    testing.value = false
  }
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  loadDocList()
})
</script>

<style scoped>
.knowledge-page {
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

/* ===== 文档列表卡片 ===== */
.list-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
  margin-bottom: 20px;
}
.list-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.list-card :deep(.el-card__body) {
  padding: 0;
}
.list-card :deep(.el-table) {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.list-card :deep(.el-table th.el-table__cell) {
  background: rgba(44, 110, 138, 0.04) !important;
  color: var(--text-mid);
  font-weight: 600;
}
.list-card :deep(.el-table .el-table__row:hover td.el-table__cell) {
  background: rgba(44, 110, 138, 0.02) !important;
}
.list-card :deep(.el-table .cell) {
  padding: 6px 8px;
}

/* ===== 删除按钮 ===== */
.delete-btn {
  color: #ffffff !important;
  background-color: #f56c6c !important;
  border-color: #f56c6c !important;
}
.delete-btn:hover {
  color: #ffffff !important;
  background-color: #f78989 !important;
  border-color: #f78989 !important;
}
.delete-btn:active {
  color: #ffffff !important;
  background-color: #e34b4b !important;
  border-color: #e34b4b !important;
}
.delete-btn .el-icon {
  color: #ffffff !important;
}

/* ===== 测试卡片 ===== */
.test-card {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-light);
}
.test-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.3);
}
.test-card :deep(.el-card__body) {
  padding: 20px 24px;
}

.test-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 输入框 + 按钮分行布局 ===== */
.test-input-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.test-input-row .test-input {
  flex: 1;
}
.test-input-row .test-btn {
  flex-shrink: 0;
  height: 40px;
  padding: 0 24px;
  background: linear-gradient(135deg, #2c6e8a, #3a8aaa);
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 8px;
}
.test-input-row .test-btn:hover {
  background: linear-gradient(135deg, #3a7a9a, #4a9aba);
}
.test-input-row .test-btn:active {
  transform: scale(0.97);
}
.test-input-row .test-btn .el-icon {
  color: white;
}

.test-result {
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-md);
  padding: 16px 20px;
}
.test-result.has-error {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.15);
}
.test-result.empty-result {
  background: rgba(44, 110, 138, 0.04);
  border-color: var(--border-light);
}

.result-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-mid);
  margin-bottom: 8px;
}
.result-icon {
  font-size: 16px;
}

.result-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-dark);
  white-space: pre-line;
  word-break: break-word;
}

/* ===== 上传对话框 ===== */
.upload-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  backdrop-filter: blur(var(--glass-blur));
}
.upload-dialog :deep(.el-dialog__header) {
  padding: 20px 24px 12px;
  border-bottom: 1px solid var(--border-light);
}
.upload-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
.upload-dialog :deep(.el-dialog__footer) {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--border-light);
}

.upload-area :deep(.el-upload-dragger) {
  border: 2px dashed var(--border-mid);
  border-radius: var(--radius-md);
  background: rgba(44, 110, 138, 0.02);
  transition: all var(--transition-base);
  padding: 32px 20px;
  width: 100%;
}
.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: rgba(44, 110, 138, 0.04);
}
.upload-area :deep(.el-upload-dragger.is-dragover) {
  border-color: var(--primary-color);
  background: rgba(44, 110, 138, 0.06);
}

.upload-icon {
  font-size: 48px;
  color: var(--text-light);
  margin-bottom: 12px;
  display: block;
}
.upload-text {
  font-size: 14px;
  color: var(--text-gray);
}
.upload-text em {
  color: var(--primary-color);
  font-style: normal;
  font-weight: 500;
}
.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-light);
  line-height: 1.6;
}
.upload-tip strong {
  color: var(--text-mid);
  font-weight: 600;
}

/* ===== 文件预览 ===== */
.file-preview {
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(44, 110, 138, 0.04);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
}
.file-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-mid);
  margin-bottom: 8px;
}
.file-preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}
.file-preview-item .file-name {
  color: var(--text-dark);
}
.file-preview-item .file-size {
  color: var(--text-light);
  font-size: 12px;
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
  .list-card :deep(.el-card__header) {
    padding: 12px 16px;
  }
  .test-card :deep(.el-card__body) {
    padding: 16px;
  }
  .test-input-row {
    flex-wrap: wrap;
  }
  .test-input-row .test-btn {
    width: 100%;
    justify-content: center;
  }
  .upload-dialog {
    width: 95% !important;
  }
}
</style>