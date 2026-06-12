// pages/index/index.js
const api = require('../../utils/api.js')

Page({
  data: {
    messages: [],
    inputText: '',
    isTyping: false,
    scrollTop: 0
  },

  onLoad() {
    this.addMessage('您好！我是灵山胜境的AI导游小灵，有什么可以帮助您的吗？', 'assistant')
  },

  addMessage(content, role) {
    const messages = this.data.messages
    messages.push({
      id: Date.now(),
      content: content,
      role: role,
      time: new Date().toLocaleTimeString()
    })
    this.setData({ messages })
    this.scrollToBottom()
  },

  scrollToBottom() {
    this.setData({ scrollTop: 99999 })
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  async sendMessage() {
    const question = this.data.inputText.trim()
    if (!question) return

    this.setData({ inputText: '', isTyping: true })
    this.addMessage(question, 'user')

    try {
      const res = await api.askQuestion(question)
      if (res.success) {
        this.addMessage(res.answer, 'assistant')
        
        // 百度云语音播报
        try {
          const audioUrl = await api.textToSpeech(res.answer)
          if (audioUrl) {
            api.playAudio(audioUrl)
          }
        } catch (ttsErr) {
          console.error('语音合成失败:', ttsErr)
        }
      } else {
        this.addMessage('抱歉，服务暂时不可用，请稍后再试。', 'assistant')
      }
    } catch (err) {
      console.error('请求失败:', err)
      this.addMessage('网络开小差了，请稍后再试。', 'assistant')
    } finally {
      this.setData({ isTyping: false })
    }
  },

  goToRoute() {
    wx.navigateTo({
      url: '/pages/route/route'
    })
  }
})