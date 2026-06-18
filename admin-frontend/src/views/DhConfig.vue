<template>
  <el-card>
    <template #header>数字人形象配置</template>
    <el-form label-width="120px">
      <el-form-item label="语音类型">
        <el-select v-model="config.voiceType" placeholder="请选择">
          <el-option label="温柔女声（中文）" value="zh-CN-XiaoxiaoNeural" />
          <el-option label="活力男声（中文）" value="zh-CN-YunxiNeural" />
          <el-option label="英文女声" value="en-US-JennyNeural" />
        </el-select>
      </el-form-item>
      <el-form-item label="语速">
        <el-slider v-model="config.speed" :min="0.5" :max="1.5" :step="0.1" show-stops />
      </el-form-item>
      <el-form-item label="服装风格">
        <el-radio-group v-model="config.clothing">
          <el-radio label="古风汉服" />
          <el-radio label="现代休闲" />
          <el-radio label="景区工作服" />
        </el-radio-group>
      </el-form-item>
      <el-form-item label="预设动作">
        <el-select v-model="config.defaultMotion" placeholder="选择开场动作">
          <el-option label="挥手致意" value="wave" />
          <el-option label="微笑点头" value="nod" />
          <el-option label="指引方向" value="guide" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const config = ref({
  voiceType: 'zh-CN-XiaoxiaoNeural',
  speed: 1.0,
  clothing: '古风汉服',
  defaultMotion: 'wave'
})

const saveConfig = () => {
  ElMessage.success('数字人配置已保存（模拟），实际项目将同步至游客端')
}
</script>