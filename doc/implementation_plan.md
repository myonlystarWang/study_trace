# 「学迹 StudyTrace」初中生作业打卡与错题本系统实现方案（实测修正版）

本项目专为**初一学生**及家庭学习督导设计，打造一个**现代化、极简无分心、移动端优先、学习全闭环**的作业打卡与错题复习系统。

经过 3 轮方案审查、`/grill-me` 针对性推演以及本机环境实测纠偏，本方案已完成对**过度设计模块的精简裁剪**、**环境兼容性陷阱的避让**与**关键业务闭环的补全**，确保工程架构健壮、依赖干净、国内网络 100% 畅通且零外部成本。

---

## 核心设计决策汇总

| 维度 | 最终选定方案 | 决策深度考量 |
| :--- | :--- | :--- |
| **产品形态** | **移动端优先 Web / PWA** | 浏览器秒开；家庭 iPhone 手机通过 Safari「添加到主屏幕」即可获得原生 App 般的全屏体验与系统通知；免去小程序繁琐的备案审核。 |
| **协同模式** | **单一家庭空间 + 双视图切换** | 孩子专注模式（大按钮打勾、作业拍照、番茄钟）；家长管理视图（学情分析、组卷排版打印、通知配置、备份）。底层数据表均预留 `student_id` 字段以供未来多孩子扩展。 |
| **识别引擎 (OCR/AI)** | **可插拔三引擎（默认 RapidOCR + 备选 PaddleOCR + 可选国内免费云端）** | **默认引擎**：采用 `rapidocr-onnxruntime`，使用与百度同源的 PP-OCRv4 模型，但基于 ONNX Runtime 推理，安装包仅数十 MB、内存占用仅 ~180MB、单图推理 0.28s，无需安装 1GB+ 的 PaddlePaddle，彻底解决 Windows C++ 依赖痛点；<br>**可选引擎**：保留原生 PaddleOCR 通道（满足纯离线深度用户）；预留国内免费云端大模型开关（硅基流动 Qwen-VL / 智谱 glm-4v-flash，填 Key 即享超高精度公式识别）；<br>**异步与保底**：后台线程执行不卡界面，且始终保留原图高清展示与几何配图框选。 |
| **A4 试卷重练排版** | **前端专用 A4 打印视图（CSS `@media print`）** | 彻底弃用后端 ReportLab 容易产生跨页截断与中文字体乱码的死板代码；采用 HTML/CSS 所见即所得排版，配置 `break-inside: avoid` 防止单题跨页断裂，支持手机/电脑一键调用无线打印（AirPrint）或另存为 PDF。 |
| **主动提醒机制** | **多渠道轮询与并存调度器（群机器人 + iOS Bark + iOS PWA Push）** | 允许多渠道并存测试，家长端可自由勾选与一键测试：<br>1. **群机器人 Webhook**：企业微信/钉钉/飞书群机器人，100% 永久免费、零配置门槛；<br>2. **iOS Bark 推送**：全家 iPhone 生态首选，App Store 免费安装，零 HTTPS 依赖，填 Key 即弹系统通知；<br>3. **iOS PWA Web Push**：配合正式 HTTPS 域名，提供主屏 PWA 原生通知。 |
| **学习流程闭环** | **作业一键转错题 + 周末智能快捷组卷** | 作业打勾时一键将错题转入错题本（自动带入学科与作业名称）；周末复习支持「本周新增」「待复习」「未掌握」一键批量组卷，避免逐题勾选繁琐。 |
| **图片处理链路** | **前端 Canvas 转码压缩 + EXIF 矫正** | 针对 iPhone 拍照特有的 `.heic` 格式，前端利用 Canvas 解码并转码为高质量 JPEG/WebP，自动纠正旋转方向，生成长边 ≤1600px 原图与 ≤320px 缩略图后上传，避免后端 Pillow 格式崩溃与大图卡顿。 |
| **服务交付与穿透** | **FastAPI 单端口一体化托管（端口 8000）** | FastAPI 统一托管前端构建产物（`dist`）、原图静态资源与后端 API。电脑仅需运行单一 Python 进程，Cloudflare Named Tunnel 映射单一端口 8000 绑定固定域名。保留 `--dev` 参数供前端热更新调试。 |
| **工具链锁定** | **`uv`（Python 3.11）+ Node 22 LTS** | 使用 `uv` 锁定 Python 3.11 独立环境；Node 升级/安装至 22 LTS（可通过 fnm 管理或直接升级系统全局 Node），启动脚本加版本守护（Node < 20 直接报错退出）。npm 源锁定 `https://registry.npmmirror.com`，PyPI 源锁定阿里镜像。 |

---

## 版本分期规划

### V1 — 核心交付范围（高可靠全闭环）

1. **每日作业打卡**：
   - 预置初一 7 门主副科学科标签（语、数、英、道法、史、地、生），支持自定义增删；
   - 文字快捷录入 + 拍照录入（异步 OCR 提取拆分条目）+ 浏览器语音辅助录入；
   - 醒目打勾反馈、红黄绿今日完成率进度条、连续打卡天数（Streak，实时聚合计算）；
   - **作业一键转错题**：做题出错时，作业列表一键直通错题录入并继承上下文。
2. **错题本与艾宾浩斯复习**：
   - 手机拍照上传（Canvas 压缩生成缩略图秒开列表，保留原图供高清打印，HEIC 格式自适应）；
   - 异步提取文字题干 + 几何配图自由框选（`ImageCropper`）；
   - 错题来源打标（作业错题 / 单元测验 / 期中期末 / 课外辅导）；
   - 艾宾浩斯智能复习流（第 1/3/7/15 天自动纳入今日复习，🔴未掌握 / 🟡待复习 / 🟢已掌握，完整落盘复习流水）。
3. **周末 A4 重练卷中心**：
   - **智能快捷筛选**：一键勾选「本周新增错题」「艾宾浩斯临界题」「高频未掌握题」；
   - **所见即所得 A4 排版**：标准试卷抬头、印刷体排版、几何插图自适应、预留网格答题区；
   - **无截断分页防护**：`break-inside: avoid` + 手动分页控制；
   - 浏览器原生一键打印 / 另存为 PDF / 手机 AirPrint 无线打印。
4. **定时督促与每日综合晚报**：
   - APScheduler 后端定时巡检（显式 `Asia/Shanghai` 时区，默认 20:10 / 21:10 / 21:50）；
   - 分时分级策略：中途催办时段（20:10 / 21:10）满卡自动跳过免打扰；晚间 21:50 依然发送结构化每日作业完成日报（包含连续天数、各科打卡状态与用时）；
   - 任务防重复调度（幂等记录表 `NotificationLog` + dev 模式文件锁）；
   - 多渠道分发器：微信服务号（PushPlus / Server酱，首选推荐）+ iOS Bark 推送 + 企微/钉钉/飞书群机器人 + iOS PWA Web Push（代码预置，待 M6 HTTPS 真机验收）。
5. **成绩记录与学情月度看板**：
   - 月度作业打卡日历（作业页轻量红黄绿月历浮窗快速切日期；家长空间整月打卡率与学科遗漏深度看板）；
   - 单元测验/期中/期末成绩台账；
   - 本地纯离线 ECharts 图表（按需引入，单科与总分起伏折线图、各科均衡雷达图、薄弱学科预警）。
6. **专注与数据安全**：
   - 25 分钟番茄钟专注计时器 + 完成声效（切后台不中断）；
   - 门禁口令（bcrypt hash，家长视图入口需口令，连续失败锁定，孩子专注视图无入口）；
   - 一键全站数据打包导出 Zip 与一键上传还原恢复（恢复前自动创建快照）。

### V2 — 进阶扩展范围（后续迭代）

1. **AI 语音与非结构化长文本意图解析分发引擎 (Voice & Text Intent Parser & Dispatcher)**:
   - **预留能力定位**：支持通过麦克风长语音输入或直接粘贴家校大段非结构化作业通知（如班级群发作业清单），由 AI 意图解析器自动结构化提取并自动化分发调用系统现有 RESTful API，免去孩子或家长手工逐项填表。
   - **分层处理管道架构 (Pipeline Architecture)**：
     - **采集与转写层 (Capture & STT)**：前端通过 Web Audio API 捕获录音或用户直接粘贴大段非结构化文字；音频流交由后端轻量本地 `faster-whisper` 或开放 STT 接口完成文字转写。
     - **意图分类与实体抽取层 (LLM Intent & Entity Extraction)**：设计统一 Prompt 规范将文本解析为强类型 JSON 动作契约，分类识别四大核心意图：
       - `intent: "batch_create_homework"` -> 提取目标日期、学科、作业条目列表；
       - `intent: "create_mistake"` -> 提取学科、题目文本、错因类型、来源标记；
       - `intent: "record_exam_score"` -> 提取考试名称、日期、科目及得分；
       - `intent: "schedule_query"` -> 查询某天或某科目的作业与复习安排。
     - **自动化编排与分发器 (Action Dispatcher)**：调度系统内置 API 客户端，自动组装 Payload 并调用对应接口（`POST /api/homework`、`POST /api/mistakes`、`POST /api/exams`）。
     - **人机协同确认环 (Human-in-the-Loop)**：前端弹窗展示 AI 解析出的动作清单与预填数据预览卡片，支持一键确认入库或快捷微调，保障核心数据精准无误。
2. **AI 名师学情长文诊断**：一键调用大模型根据学期成绩走势与错题分布生成深度提分建议；
3. **知识点图谱体系**：初中各科系统化知识点树形目录与薄弱知识点穿透下钻；
4. **手写笔记智能擦除**：通过轻量图像模型擦除试卷上原本写下的红笔批改与铅笔字迹。

---

## 数据库模型设计（实测精简健全版）

```
Students (学生表 — 预留多孩子架构)
  ├── id, name, grade, avatar, created_at

Subjects (学科表 — 预置初一7科，支持增删改)
  ├── id, name, full_score, is_default, sort_order

HomeworkItems (作业条目)
  ├── id, student_id, subject_id, date, content
  ├── is_completed, completed_at, source_image_path
  ├── created_at
  # 注：Streak与每日完成率由本表实时聚合计算，不设冗余 DailyCheckins 表

MistakeRecords (错题主记录)
  ├── id, student_id, subject_id
  ├── source_type (homework/exam/exercise)     # 来源标记
  ├── source_reference                         # 来源说明（如：10.12数学作业 / 期中试卷第18题）
  ├── original_image_path, thumbnail_path, cropped_diagram_path
  ├── extracted_text                           # 题目印刷体文本（OCR 结果）
  ├── error_type, mastery_status (未掌握/待复习/已掌握)
  ├── review_count, last_reviewed_at           # 复习统计
  ├── next_review_date                         # 艾宾浩斯下一次复习日期
  ├── created_at

MistakeReviews (错题复习历史流水)
  ├── id, mistake_id, reviewed_at, result (remembered/forgotten), next_review_date

ExamRecords (考试总台账)
  ├── id, student_id, exam_name, exam_type, exam_date

ExamScores (单科考试成绩)
  ├── id, exam_id, subject_id
  ├── score, full_score, class_rank, grade_rank, class_avg

NotificationLog (提醒幂等记录)
  ├── id, date, slot, channel, sent_at

PushSubscriptions (Web Push 设备订阅)
  ├── id, device_label, endpoint, p256dh, auth, user_agent, created_at

Settings (系统通用配置)
  ├── key, value (JSON — 口令、Webhook 机器人 URL、Bark Key、提醒时段等；敏感 API Key 存 data/.env)
```

---

## 完整工程目录结构

```text
study_trace/
├── .gitignore
├── .python-version                    # 声明 Python 3.11（uv 自动管理与隔离）
├── .node-version                      # 声明 Node 22
├── pyproject.toml                     # 项目依赖声明（uv 驱动，配置阿里镜像源）
├── README.md                          # 部署指南、Named Tunnel 穿透配置、使用文档
├── run.py                             # 一键启动脚本（默认托管前端 dist，--dev 支持热更新）
├── start.bat                          # Windows 双击一键启动脚本（含版本守卫）
├── doc/
│   ├── implementation_plan.md         # 方案设计文档
│   └── development_plan.md            # 开发计划与验收方案
│
├── backend/
│   ├── alembic/                       # Alembic 数据库版本迁移
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                  # 配置项（路径、时区、密钥）
│   │   ├── database.py                # SQLite 引擎与 Session 工厂
│   │   ├── models.py                  # SQLAlchemy 表模型
│   │   ├── schemas.py                 # Pydantic v2 请求响应契约
│   │   ├── scheduler.py               # APScheduler 作业巡检（带文件锁与幂等）
│   │   ├── auth.py                    # 家庭访问口令校验（bcrypt）
│   │   ├── routers/
│   │   │   ├── homework.py            # 作业增删改查、打勾、Streak 聚合、月度打卡日历接口(/calendar)、一键转错题
│   │   │   ├── mistakes.py            # 错题上传、艾宾浩斯复习流、来源打标
│   │   │   ├── ocr.py                 # 异步 OCR 任务提交与结果轮询
│   │   │   ├── exams.py               # 考试成绩管理、本地聚合统计接口
│   │   │   ├── notifications.py       # 多渠道推送配置与一键测试（Webhook / Bark / Web Push）
│   │   │   ├── backup.py              # 数据与图片一键打包 Zip 与快照恢复
│   │   │   └── settings.py            # 家庭设置、学科配置
│   │   └── utils/
│   │       ├── ocr_service.py         # 可插拔 OCR 引擎（默认 RapidOCR，备选 PaddleOCR/云端）
│   │       ├── image_handler.py       # 后端图片落盘与分级目录管理
│   │       ├── notifier.py            # 多渠道通知发送器（Webhook / Bark / Web Push）
│   │       └── statistics.py          # 偏科离散度、提分潜力等纯本地算法
│
├── frontend/                          # Vite 6 + Vue 3 SFC + Vant 4
│   ├── package.json
│   ├── vite.config.js                 # 含 dev proxy 配置
│   ├── index.html
│   ├── public/
│   │   ├── manifest.json              # PWA 配置（支持 iOS 添加到主屏幕独立运行）
│   │   ├── sw.js                      # Service Worker（离线资源缓存与 Push 监听）
│   │   └── icons/                     # 应用图标
│   └── src/
│       ├── App.vue
│       ├── main.js                    # 全局注册 Vant 4、Pinia、Router
│       ├── router/index.js
│       ├── stores/                    # Pinia 状态管理
│       ├── api/                       # Axios API 请求封装
│       ├── utils/
│       │   └── imageCompress.js       # Canvas 解码 HEIC、旋转矫正、生成缩略图与原图
│       ├── views/
│       │   ├── HomeworkView.vue       # 今日作业打卡、打勾动效、Streak、月历浮窗、番茄钟、一键转错题
│       │   ├── MistakeView.vue        # 错题本（学科/状态/来源筛选、艾宾浩斯复习队列）
│       │   ├── PaperCenterView.vue    # 周末快捷组卷中心（本周/待复习快捷选中）
│       │   ├── PaperPrintView.vue     # A4 专用打印排版视图（CSS @media print，防跨页截断）
│       │   ├── ExamView.vue           # 考试台账、ECharts 走势图与均衡雷达图、月度打卡看板
│       │   └── SettingsView.vue       # 家长管理视图、提醒渠道设置与测试、备份还原
│       ├── components/
│       │   ├── PomodoroTimer.vue      # 25分钟专注倒计时组件
│       │   ├── QuickAddModal.vue      # 拍照/文字录入弹窗与异步识别编辑确认
│       │   ├── CalendarModal.vue      # 月度作业打卡热力圆点与快速切日浮窗组件
│       │   ├── ImageCropper.vue       # 几何配图交互式裁剪框选组件
│       │   └── ChartCard.vue          # ECharts 按需引入卡片封装
│       ├── composables/
│       │   ├── useSpeech.js           # 浏览器语音录入辅助
│       │   └── useNotifications.js    # iOS PWA 推送订阅交互
│       └── styles/
│           ├── theme.css              # 现代化移动端 UI 主题变量
│           ├── mobile.css             # iPhone 底部横条与刘海屏安全区域适配
│           └── print.css              # 标准 A4 试卷打印样式（break-inside: avoid）
│
└── data/                              # 数据持久化目录（Git 排除）
    ├── study_trace.db                 # SQLite 数据库
    ├── .env                           # 敏感 API Key（如云端视觉模型 Key）
    ├── uploads/
    │   ├── originals/                 # 手机拍照原图（用于高清打印）
    │   └── thumbnails/                # 压缩缩略图（用于移动端丝滑浏览）
    └── backups/                       # 本地自动/手动备份 zip 包
```
