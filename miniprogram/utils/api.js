// utils/api.js
const app = getApp()

const getBaseUrl = () => {
  const url = app.globalData.apiBaseUrl || 'http://localhost:8000'
  console.log('🔍 请求地址:', url)
  return url
}

// AI 对话
const askQuestion = (question) => {
  console.log('📤 发送问题:', question)
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/api/chat/ask`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        question: question,
        use_rag: true,
        n_results: 3
      },
      timeout: 30000,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`))
        }
      },
      fail: (err) => {
        console.error('API请求失败:', err)
        reject(err)
      }
    })
  })
}

// 语音合成（文字转语音）
const textToSpeech = (text) => {
  console.log('🔊 语音合成:', text.substring(0, 50))
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}/api/voice/tts`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { 
        text: text, 
        voice_type: 0  // 0:女声
      },
      timeout: 10000,
      success: (res) => {
        if (res.data.success) {
          resolve(res.data.audio_url)
        } else {
          reject(new Error(res.data.error))
        }
      },
      fail: (err) => {
        console.error('TTS请求失败:', err)
        reject(err)
      }
    })
  })
}

// 播放音频
const playAudio = (audioUrl, onEnd) => {
  console.log('🔊 播放音频:', audioUrl)
  const innerAudio = wx.createInnerAudioContext()
  innerAudio.src = audioUrl
  innerAudio.autoplay = true
  innerAudio.onEnded(() => {
    innerAudio.destroy()
    if (onEnd) onEnd()
  })
  innerAudio.onError((err) => {
    console.error('播放失败:', err)
  })
  return innerAudio
}

module.exports = {
  askQuestion,
  textToSpeech,
  playAudio,
  getBaseUrl
}