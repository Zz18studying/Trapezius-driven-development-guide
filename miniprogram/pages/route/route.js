// pages/route/route.js
Page({
  data: {
    selectedInterest: '',
    routes: {
      history: {
        name: '历史文化路线',
        duration: '6小时',
        spots: ['灵山大照壁', '祥符禅寺', '灵山大佛', '灵山梵宫', '五印坛城'],
        description: '深度体验佛教文化与历史遗迹'
      },
      nature: {
        name: '自然风光路线',
        duration: '5小时',
        spots: ['九龙灌浴', '菩提大道', '灵山大佛', '曼飞龙塔', '灵山精舍'],
        description: '欣赏太湖风光与园林景观'
      },
      family: {
        name: '亲子家庭路线',
        duration: '4小时',
        spots: ['九龙灌浴', '佛手广场', '百子戏弥勒', '灵山梵宫'],
        description: '轻松有趣，适合带孩子游览'
      }
    },
    currentRoute: null
  },

  onLoad() {
    // 默认显示历史文化路线
    this.setData({ currentRoute: this.data.routes.history })
  },

  selectInterest(e) {
    const interest = e.currentTarget.dataset.interest
    this.setData({ 
      selectedInterest: interest,
      currentRoute: this.data.routes[interest]
    })
  },

  askAboutRoute() {
    const route = this.data.currentRoute
    const question = `请介绍一下${route.name}，包括${route.spots.join('、')}`
    
    // 跳回对话页并发送问题
    const pages = getCurrentPages()
    const prevPage = pages[pages.length - 2]
    if (prevPage) {
      prevPage.setData({ inputText: question })
      prevPage.sendMessage()
    }
    wx.navigateBack()
  }
})