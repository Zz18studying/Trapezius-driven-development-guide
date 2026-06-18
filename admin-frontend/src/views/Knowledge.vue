<template>
  <div>
    <el-button type="primary" @click="dialogUploadVisible = true" style="margin-bottom: 20px">
      批量上传知识文档
    </el-button>

    <!-- 添加 :key 以优化渲染性能 -->
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
      <!-- 将内联样式提取为类名，提高可维护性 -->
      <div v-if="testAnswer" class="answer-box">
        <strong>检索结果：</strong> {{ testAnswer }}
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
        <el-button type="primary" :disabled="fileList.length === 0" @click="mockUpload">
          模拟上传 ({{ fileList.length }}个文件)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 文档列表
const docList = ref([
  { id: 1, title: '景区历史讲解词.pdf', docType: '讲解词', uploadTime: '2025-03-01', status: '已索引' },
  { id: 2, title: '常见问题FAQ.docx', docType: 'FAQ', uploadTime: '2025-03-05', status: '已索引' },
  { id: 3, title: '景点地图标注.txt', docType: '地图', uploadTime: '2025-03-10', status: '处理中' }
])

// 用于生成唯一ID的计数器，避免 Date.now() 在高并发下的冲突
let idCounter = Date.now()

// 上传相关
const dialogUploadVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])

// 允许的扩展名 (常量，无需响应式)
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']

// 判断文件是否允许
const isFileAllowed = (fileName) => {
  if (!fileName || !fileName.includes('.')) return false
  const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase()
  return ALLOWED_EXTENSIONS.includes(ext)
}

// ===== 文件变化时处理 (静默过滤，不弹窗) =====
const handleFileChange = (file, fileListNew) => {
  // 分离合规和不合规文件
  const validFiles = []
  
  fileListNew.forEach(f => {
    if (isFileAllowed(f.name)) {
      validFiles.push(f)
    }
    // 非法文件直接忽略，不加入 validFiles，也不弹窗
  })
  
  // 只保留合规文件
  fileList.value = validFiles
}

// 移除文件时更新列表
const handleRemove = (file, fileListNew) => {
  // 直接同步 el-upload 传递的最新列表
  fileList.value = fileListNew
}

// 模拟批量上传
const mockUpload = () => {
  // 此时 fileList.value 已经是经过 handleFileChange 过滤后的合法文件
  if (fileList.value.length === 0) {
    ElMessage.warning('当前列表中没有可上传的有效文件（仅支持 .pdf, .docx, .txt）')
    return
  }

  const newDocs = fileList.value.map((file) => ({
    id: ++idCounter, // 使用自增计数器保证 ID 唯一且递增
    title: file.name,
    docType: '其他',
    uploadTime: new Date().toLocaleDateString(),
    status: '待处理'
  }))

  // 批量插入，避免多次触发响应式更新
  docList.value.unshift(...newDocs)

  ElMessage.success(`成功上传 ${fileList.value.length} 个文件（模拟）`)
  
  // 清理状态
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  fileList.value = []
  dialogUploadVisible.value = false
}

// 对话框关闭时清空
const handleDialogClosed = () => {
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  fileList.value = []
}

// 删除文档
const handleDelete = (row) => {
  docList.value = docList.value.filter(d => d.id !== row.id)
  ElMessage.success('删除成功')
}

// 测试问答
const testQuestion = ref('')
const testAnswer = ref('')

const testQuery = () => {
  const question = testQuestion.value.trim()
  if (!question) {
    ElMessage.warning('请输入问题')
    return
  }
  // 避免直接拼接用户输入到可能被视为 HTML 的上下文中，虽然这里是纯文本插值，但保持良好习惯
  testAnswer.value = `【模拟检索】根据知识库，关于“${question}”的答案是：示例内容。`
}
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

/* 提取样式类 */
.answer-box {
  margin-top: 15px;
  background: #f0fdf4;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #10b981;
}
</style>