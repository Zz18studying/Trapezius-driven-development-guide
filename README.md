# 灵山胜境 AI 数字导游系统

> 比赛上传最终版 README

灵山胜境 AI 数字导游系统是一套面向智慧文旅场景的全栈应用，围绕“游客咨询、景点讲解、路线推荐、语音交互、数字人展示、游客评价、后台运营分析”构建。系统以灵山胜境景区资料为知识基础，通过 RAG 检索增强生成连接 DeepSeek 大模型，让游客能够用自然语言获取更贴近景区资料的导览回答，同时为景区运营方沉淀对话、热点、情感和知识库维护数据。

本项目不是单一问答机器人，而是一套“游客端服务 + AI 知识问答 + 语音数字人交互 + 管理后台分析”的智慧景区导览平台。

## 一、项目亮点

- **垂直景区知识问答**：围绕灵山胜境构建专属知识库，使用 ChromaDB 进行向量检索，再由 DeepSeek 基于参考资料生成导游式回答。
- **低幻觉 RAG 链路**：结合问题扩展、景点名精确兜底、关键词重排、相似度阈值控制和事实约束 Prompt，降低通用大模型凭空生成风险。
- **多模态导览体验**：游客端支持文字问答、语音识别、语音播报和 Live2D 数字人“小灵”展示，增强现场导览的陪伴感。
- **个性化路线建议**：支持历史文化、自然风光、亲子家庭、祈福体验、摄影打卡、雨天、老人、半日游等场景化游览建议。
- **运营数据闭环**：后台支持对话记录、游客关注词云、热点话题、情感分析、高风险会话和知识库管理，把游客咨询转化为可分析的数据资产。
- **完整工程实现**：包含游客 Web 前端、Vue 管理端、FastAPI 后端、SQLite 业务库、ChromaDB 向量库、RAG 服务、LLM 服务、语音服务和数字人资源。

## 二、系统功能

### 1. 游客端

游客端位于 `web/` 目录，面向景区游客使用。

| 页面 | 文件 | 功能 |
| --- | --- | --- |
| 首页 | `web/index.html` | 景区形象展示、热门景点、推荐路线、天气信息、数字人入口 |
| AI 导游 | `web/chat.html` | 文本问答、语音提问、TTS 播报、Live2D 数字人、聊天记录缓存 |
| 路线推荐 | `web/routes.html` | 场景化路线展示、路线筛选、导览地图示意 |
| 景点列表 | `web/spots.html` | 景点卡片、标签、评分展示、搜索与详情跳转 |
| 景点详情 | `web/spot-detail.html` | 景点图文介绍、语音讲解、评分评论、问导游入口 |

### 2. 管理端

管理端位于 `admin-frontend/` 目录，面向景区运营与内容维护人员。

| 模块 | 文件 | 功能 |
| --- | --- | --- |
| 欢迎页 | `Welcome.vue` | 后台入口与系统概览 |
| 数据看板 | `Dashboard.vue` | 服务人次、响应耗时、游客关注词云、满意度趋势 |
| 对话管理 | `Conversations.vue` | 按日期、情感、会话 ID 查询游客提问与 AI 回答 |
| 知识库管理 | `Knowledge.vue` | 上传知识文档、查看文档状态、测试知识库检索 |
| 游客感受度报告 | `Sentiment.vue` | 情感分布、热点主题、高风险会话、服务建议、报告生成 |

### 3. 后端能力

后端位于 `backend/` 目录，基于 FastAPI 构建。

| 能力 | 对应模块 |
| --- | --- |
| AI 问答接口 | `backend/routers/chat.py` |
| 语音识别与合成 | `backend/routers/voice.py` |
| 管理后台接口 | `backend/routers/admin.py` |
| 知识库管理接口 | `backend/routers/knowledge.py` |
| 景点评价接口 | `backend/routers/spots.py` |
| RAG 检索服务 | `backend/services/rag_service.py` |
| DeepSeek 调用与提示词约束 | `backend/services/llm_service.py` |
| 检索重排与意图识别 | `backend/services/retrieval_ranker.py` |
| 情感分析与运营建议 | `backend/services/sentiment_service.py` |
| 热点话题统计 | `backend/services/topic_service.py` |

## 三、技术架构

```text
游客端 Web / 管理端 Web
        ↓
FastAPI 后端服务
        ↓
业务接口层：Chat / Voice / Admin / Knowledge / Spots / Health
        ↓
智能能力层：RAG 检索、DeepSeek 生成、关键词重排、情感分析、话题分析
        ↓
数据资源层：ChromaDB 向量库、SQLite 业务库、景区原始资料、静态图片、Live2D 模型
```

### 技术栈

| 类型 | 技术 |
| --- | --- |
| 游客端 | HTML、CSS、JavaScript、PixiJS、Live2D Cubism |
| 管理端 | Vue 3、Vite、Vue Router、Pinia、Element Plus、ECharts |
| 后端 | FastAPI、Pydantic、Uvicorn、SQLAlchemy |
| AI 问答 | DeepSeek API、RAG、Prompt 约束生成 |
| 向量检索 | ChromaDB、Sentence Transformers、本地中文 n-gram embedding 兜底 |
| 数据库 | SQLite |
| 语音能力 | 百度智能云 ASR / TTS、ffmpeg |
| 静态资源 | 景区图片、导览地图、Live2D 模型文件 |

## 四、RAG 知识库设计

系统采用“FAQ + 原文知识块”的双知识组织方式：

- FAQ 适合匹配游客口语化问题，例如“门票多少钱”“半天怎么逛”。
- 原文知识块保留景点资料完整内容，例如景点介绍、文化背景、路线说明。
- ChromaDB 负责向量召回，`retrieval_ranker.py` 负责结合意图、景点名和关键词进行重排。
- 用户明确提到景点名称时，系统会通过元数据精确兜底，降低景点错配风险。

知识库构建流程：

```text
原始景区资料 / Excel 数据
        ↓
scripts/01_extract_and_merge_data.py
        ↓
抽取景点结构化数据与知识单元
        ↓
scripts/02_generate_faq.py
        ↓
规则生成 FAQ
        ↓
scripts/03_build_vector_db.py
        ↓
写入 ChromaDB 向量库
        ↓
RAGService 检索 + LLMService 生成回答
```

## 五、目录结构

```text
.
├── backend/                 # FastAPI 后端服务
│   ├── main.py              # 服务入口，注册路由与启动任务
│   ├── config.py            # 模型、检索、路线推荐配置
│   ├── routers/             # API 路由
│   ├── services/            # RAG、LLM、情感分析、话题统计等服务
│   ├── models/              # SQLAlchemy 数据模型
│   └── data.db              # SQLite 业务数据库
├── admin-frontend/          # Vue 3 管理后台
├── web/                     # 游客端静态页面
│   ├── index.html           # 首页
│   ├── chat.html            # AI 导游页面
│   ├── routes.html          # 路线推荐页面
│   ├── spots.html           # 景点列表页面
│   └── spot-detail.html     # 景点详情页面
├── scripts/                 # 知识库构建与检索测试脚本
├── data/                    # 原始景区数据
├── models/                  # Live2D 数字人模型资源
├── 产品设计文档_黑色表格版.docx # 比赛用产品设计文档
└── README.md                # 本说明文件
```

完整部署、启动、使用与比赛演示流程见：[产品部署与使用说明.md](产品部署与使用说明.md)。

## 六、环境要求

### 1. 基础环境

- Python 3.10+
- Node.js 20.19+ 或 22.12+
- ffmpeg，语音识别时用于浏览器音频格式转换

### 2. 后端 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 管理端前端依赖

```bash
cd admin-frontend
npm install
```

### 4. 环境变量

如需完整体验大模型问答与语音能力，需要配置：

```bash
DEEPSEEK_API_KEY=你的 DeepSeek API Key
BAIDU_API_KEY=你的百度智能云 API Key
BAIDU_SECRET_KEY=你的百度智能云 Secret Key
```

未配置 DeepSeek 时，普通前端页面仍可查看，但 AI 生成能力不可用。未配置百度语音密钥时，文本问答仍可使用，ASR/TTS 语音功能会返回未配置提示。

## 七、运行方式

### 1. 构建知识库

首次运行或更新景区资料后，按顺序执行：

```bash
python scripts/01_extract_and_merge_data.py
python scripts/02_generate_faq.py
python scripts/03_build_vector_db.py
python scripts/04_test_retrieval.py
```

### 2. 启动后端服务

```bash
cd backend
python main.py
```

默认端口为 `8000`。接口文档地址：

```text
http://127.0.0.1:8000/docs
```

### 3. 访问游客端

游客端页面在 `web/` 目录。线上部署时由 FastAPI 或 Nginx 挂载静态文件；本地演示时建议通过后端服务或本地静态服务器访问，确保 `/api/*` 请求能够转发到后端。

核心页面：

```text
web/index.html
web/chat.html
web/routes.html
web/spots.html
web/spot-detail.html
```

### 4. 启动管理端

```bash
cd admin-frontend
npm run dev
```

管理端默认使用相对路径请求后端接口。若前后端分端口运行，需通过代理或部署配置保证 `/api/*` 能访问 FastAPI 服务。

## 八、核心接口

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/chat/ask` | POST | AI 导游问答 |
| `/api/chat/search` | POST | 仅检索知识库 |
| `/api/chat/session/init` | GET | 初始化或复用游客会话 |
| `/api/chat/clear` | POST | 清空会话上下文 |
| `/api/voice/asr` | POST | 语音识别 |
| `/api/voice/tts` | POST | 语音合成 |
| `/api/spots/ratings` | GET | 获取景点评分汇总 |
| `/api/spots/{spot_id}/reviews` | POST | 提交景点评价 |
| `/api/admin/dashboard/stats` | GET | 管理端数据看板 |
| `/api/admin/conversations` | GET | 对话记录查询 |
| `/api/admin/knowledge/upload` | POST | 上传知识文档 |
| `/api/admin/knowledge/list` | GET | 知识文档列表 |
| `/api/admin/sentiment/*` | GET | 情感分析、趋势、高风险会话和报告 |

## 九、比赛演示建议

推荐演示路径：

1. 打开游客端首页，展示景区视觉、热门景点、推荐路线和数字人入口。
2. 进入 AI 导游页，提问“灵山大佛有什么看点？”展示 RAG 问答能力。
3. 提问“带老人半天怎么玩比较轻松？”展示场景化路线建议。
4. 使用语音按钮提问，再播放 AI 回答，展示 ASR + TTS + 数字人链路。
5. 进入景点详情页，展示语音讲解和景点评价。
6. 打开管理端，展示数据看板、对话记录、情感分析、热点话题和知识库管理。
7. 在知识库管理中测试检索，说明系统如何通过知识资料约束大模型回答。

建议重点讲清楚三句话：

- 本项目不是普通聊天机器人，而是面向灵山胜境景区资料的垂直 AI 导览系统。
- 系统通过 RAG 检索增强生成降低事实类问题的幻觉风险。
- 前台服务和后台运营形成闭环，游客咨询可以反向推动景区知识库和服务优化。

## 十、当前版本边界

当前版本已完成比赛演示所需的核心闭环，但以下内容属于后续可扩展方向：

- 管理端登录认证与 RBAC 权限控制。
- 生产级 HTTPS、限流、日志监控和自动备份。
- 真实地图导航、实时客流、票务系统和活动报名系统接入。
- 多语言讲解、小程序封装和更多数字人动作表情。
- 知识库版本管理、未命中问题池和回答质量人工反馈。

## 十一、项目价值

灵山胜境 AI 数字导游系统将景区导览从“静态信息展示”提升为“自然语言交互 + 可信知识问答 + 多模态讲解 + 运营数据闭环”。它既能提升游客获取信息和规划路线的效率，也能帮助景区运营方持续识别游客关注点、负面反馈和知识库缺口，具备向其他景区、展馆、博物馆和校园导览场景迁移的应用价值。
