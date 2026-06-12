// app.js
App({
  onLaunch() {
    console.log('小程序启动')
  },
  globalData: {
    userInfo: null,
    apiBaseUrl: 'http://110.42.246.141:8000'  
  }
})