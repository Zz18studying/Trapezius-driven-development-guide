<template>
  <div>
    <el-button type="primary" @click="dialogUploadVisible = true" style="margin-bottom: 20px">
      批量上传知识文档
    </el-button>

    <el-table :data="docList" stripe border row-key="id">
      <el-table-column prop="title" label="文档标题" />
      <el-table-column prop="docType" label="文档类型" />
      <el-table-column prop="uploadTime" label="上传时间" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === '已索引' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-card style="margin-top: 30px">
      <template #header>测试知识库问答</template>
      <el-input v-model="testQuestion" placeholder="输入一个问题，测试检索效果" style="margin-bottom: 15px" />
      <el-button type="success" @click="testQuery">测试</el-button>
      <div v-if="testAnswer" class="answer-box">
        <strong>检索结果：</strong>
        <div style="white-space: pre-line; margin-top: 8px;">{{ testAnswer }}</div>
      </div>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog 
      v-model="dialogUploadVisible" 
      title="批量上传知识文档" 
      width="30%" 
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
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .pdf, .docx, .txt 格式<br>
            <span style="color: #e6a23c; font-size: 12px;">注意：非支持格式的文件将被自动忽略，不会显示在列表中</span>
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="dialogUploadVisible = false">取消</el-button>
        <el-button type="primary" :disabled="fileList.length === 0" @click="handleUpload">
          上传 ({{ fileList.length }}个文件)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// ===================== 文档列表 =====================
const docList = ref([])

const loadDocList = async () => {
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
  }
}

// ===================== 上传相关 =====================
const dialogUploadVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])

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

const testQuery = async () => {
  if (!testQuestion.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  try {
    const res = await request.post('/api/admin/knowledge/test', {
      question: testQuestion.value,
      n_results: 3
    })
    if (res.code === 0) {
      const results = res.data.results
      if (results && results.length > 0) {
        testAnswer.value = results.map((r, i) => 
          `【${i+1}】问题：${r.question}\n   答案：${r.answer}`
        ).join('\n\n')
      } else {
        testAnswer.value = '未找到相关内容'
      }
    } else {
      testAnswer.value = '检索失败：' + (res.msg || '未知错误')
    }
  } catch (error) {
    console.error('测试查询失败:', error)
    testAnswer.value = '请求失败，请检查网络'
  }
}

// ===================== 生命周期 =====================
onMounted(() => {
  loadDocList()
})
</script>

<style scoped>
.el-upload-dragger {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  background: #f9fafb;
  transition: all 0.2s;
}
.el-upload-dragger:hover {
  border-color: #10b981;
  background: #f0fdf4;
}
:deep(.el-upload-dragger) {
  width: 100%;
}

.answer-box {
  margin-top: 15px;
  background: #f0fdf4;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #10b981;
}
</style>