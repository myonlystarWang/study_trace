# StudyTrace (智学迹)

> **面向初中生与家长的全闭环学习追踪、智能错题复习与学情深度诊断平台**
> 
> 基于 **FastAPI + Vue 3 + Vant 4 + RapidOCR + SQLite** 打造的轻量级、本地化、移动端优先（Mobile-First）全栈学习管理系统。

---

## 🌟 核心设计理念

初中阶段学习任务繁重、科目增多（中考 7 科），学生常常面临“作业拖延忘打卡、错题只抄不重练、成绩波动无预警、家长催促起冲突”的普遍痛点。

**StudyTrace (智学迹)** 旨在建立一套健康、高效、温和且高度自洽的学习飞轮：
- **给学生**：清爽无干扰的今日作业打卡清单、沉浸式番茄钟专注计时、按记忆遗忘曲线自动流转的智能错题本、一键排版的周末 A4 重练试卷。
- **给家长**：微信公众号/Bark/群机器人分时分级温馨推送（中途免打扰催办 + 晚间喜报快报）、多维度学情雷达与成绩走势折线、初一各学科满分分值自定义管理、全量数据一键离线快照备份。

---

## 🚀 核心功能特色

```
┌────────────────────────────────────────────────────────────────────────┐
│                        StudyTrace 核心闭环架构                         │
└────────────────────────────────────────────────────────────────────────┘
     │                                                               │
     ▼ [今日作业打卡] ─── 遇到难点/失误 ───► [错题拍照/OCR提取]       │
  连续打卡 (Streak)                              │                  │
     │                                     [艾宾浩斯复习流转]        │
     ▼                               (+1d ➔ +3d ➔ +7d ➔ +15d)       │
  [分时推送提醒]                                 │                  │
  (微信 / Bark / 机器人)                         ▼                  │
     │                                 [周末 A4 智能组卷]           │
     ▼                            (标准单栏/强化留白/全题干)        │
  [历次成绩录入]                                 │                  │
     │                                           ▼                  │
     ▼                                  [重练完成·批量打卡] ────────┘
  [7科均衡学力雷达] ➔ [薄弱诊断提分建议] ➔ [全站离线备份]
```

### 1. 每日作业打卡与 Streak 连续签到
- **移动优先卡片流**：直观展示当日待办作业项，左右手势便捷操作，支持完成标记与一键转入错题本。
- **动态 Streak 连续打卡算法**：全天作业 100% 完成即累加打卡天数，支持断签重计与跨月边界无缝衔接。
- **双端自适应周历**：移动端支持轻量按周翻页切换，PC/Web 端支持横向平滑滚动与日历直接点选。
- **内置专注番茄钟**：提供 25 分钟标准专注与 50 分钟深度学习模式，计时器与录入按钮流式排版、无遮挡冲突。

### 2. 智能错题管理与艾宾浩斯抗遗忘流转
- **离线 OCR 拍照提取**：内置 RapidOCR 本地离线深度学习识别引擎，拍照上传后一键秒级提取题干，保护隐私无需联网。
- **艾宾浩斯记忆流转状态机**：
  - 收录错题 ➔ 进入待复习队列（+1天）
  - 巩固掌握 ➔ 自动推移复习周期（+3天 ➔ +7天 ➔ +15天 ➔ 完全掌握归档）
  - 复习遗忘 ➔ 自动回退至第 1 天重新流转
- **多维度检索与历史库**：支持按科目筛选、按题型标签检索，解耦“今日待复习”与“全局错题库”，交互清晰顺畅。

### 3. A4 周末重练试卷与智能排版打印引擎
- **智能分页与留白算法**：根据 S / M / L 草稿留白尺寸自动计算试卷分页高度，提供 4 套预设排版布局（紧凑两栏、标准单栏、强化留白、全题干模式）。
- **无干扰纯净打印**：独立 `@media print` 样式隔离层，手机/电脑端均可无缝导出高清 PDF 或直连打印机，移动端全宽自适应不截断。
- **试卷重练批量打卡**：重练完成后一键批量完成打卡，掌握状态自动回流艾宾浩斯复习流。

### 4. 成绩管理与学情深度诊断
- **单科走势与总分折线**：记录单元测验、月考、期中期末历次成绩，自动生成得分走势折线图与排名轨迹。
- **中考 7 科均衡学力雷达图**：基于真实中考满分折算各科学力得分率，直观呈现偏科与短板。
- **薄弱学科智能诊断算法**：智能识别学力洼地，根据近期得分走势输出针对性学科复习建议。

### 5. 家长管理视图与数据资产安全
- **6 位 PIN 口令门禁**：学生日常专注打卡，家长管理界面受口令保护（默认 `888888`），具备防爆破锁定保护。
- **多渠道分时分级推送**：
  - 渠道支持：微信公众号 (PushPlus)、Server酱 (Turbo版)、iOS Bark (iPhone 直推)、群机器人 Webhook (企微/钉钉/飞书)。
  - 分时策略：20:10 / 21:10 中途催办（全部完成则自动免打扰跳过）；21:50 晚报汇总（满卡送达喜报）。
- **学科满分灵活配置**：支持初一各科满分自由调整（如语数英 120/150 分，政史地生 100 分），支持添加或删除自定义拓展学科，核心 7 科名称与删除权限受底层保护。
- **全站离线数据一键备份与还原**：一键导出包含 SQLite 数据库与错题原图的 Zip 备份包；导入还原前强制创建本地安全快照。

---

## 🛠️ 技术选型与架构

| 模块 | 技术栈 | 说明 |
| :--- | :--- | :--- |
| **后端框架** | FastAPI (Python 3.11) | 高性能异步 ASGI 框架，原生集成 Swagger API 文档 |
| **ORM & 迁移** | SQLAlchemy + Alembic | 严格生产级数据库版本迁移管理，杜绝 `create_all` 捷径 |
| **本地数据库** | SQLite 3 + WAL 模式 | 零运维成本，单文件存储，数据资产 100% 掌握在本地 |
| **离线 OCR** | RapidOCR (ONNXRuntime) | 纯本地离线深度学习文字识别，极速且免外部 API 依赖 |
| **密码安全** | bcrypt | 家长管理口令安全加盐哈希存储 |
| **前端工程** | Vue 3 (Composition API) + Vite 6 | 新一代轻量前端构建架构，毫秒级热更新 |
| **移动组件库** | Vant 4 | 精致优雅的移动端 UI 组件体系 |
| **数据可视化** | Apache ECharts 5 (按需引入) | 折线图、柱状图、学力雷达图交互式渲染 |
| **视觉规范** | Vanilla CSS Design Tokens | 全局统一色阶、分级阴影、圆角规范，100% 零 Emoji |

---

## 📂 工程目录结构

```
study_trace/
├── backend/                  # 后端源码目录
│   ├── alembic/              # 数据库迁移版本脚本
│   ├── app/
│   │   ├── auth.py           # 家长门禁 PIN 口令与认证逻辑
│   │   ├── config.py         # 系统全局配置与路径管理
│   │   ├── database.py       # 数据库连接引擎与 SessionLocal
│   │   ├── main.py           # FastAPI 应用入口与路由挂载
│   │   ├── models.py         # SQLAlchemy 数据库模型
│   │   ├── schemas.py        # Pydantic v2 请求响应契约
│   │   ├── seed.py           # 初始预置初一学科与口令数据填充
│   │   ├── routers/          # RESTful API 路由模块
│   │   │   ├── homework.py   # 作业打卡与连续签到接口
│   │   │   ├── mistakes.py   # 错题收录与艾宾浩斯复习接口
│   │   │   ├── paper.py      # A4 智能组卷与批量打卡接口
│   │   │   ├── exams.py      # 成绩录入与学情雷达分析接口
│   │   │   ├── ocr.py        # 离线 OCR 异步识别接口
│   │   │   ├── notifications.py # 多渠道推送与定时日报接口
│   │   │   ├── backup.py     # 全站 Zip 备份导出与快照还原接口
│   │   │   └── settings.py   # 学科满分与家长安全设置接口
│   │   └── utils/            # 通用工具模块 (OCR引擎、图片防穿越处理等)
├── frontend/                 # 前端源码目录 (Vue 3 + Vite)
│   ├── src/
│   │   ├── api/              # Axios 请求接口封装层
│   │   ├── assets/
│   │   │   ├── design-tokens.css # 全局设计规范 (Tokens / Badges / Tags)
│   │   │   └── print.css     # A4 试卷纯净打印与 PDF 隔离样式
│   │   ├── router/           # 路由配置 (含四大主Tab与打印页)
│   │   ├── utils/            # ECharts 统一按需封装
│   │   ├── views/            # 核心业务视图
│   │   │   ├── HomeworkView.vue    # 作业打卡主界面
│   │   │   ├── MistakeView.vue     # 错题本与艾宾浩斯待复习
│   │   │   ├── ScoreView.vue       # 学情分析与成绩管理
│   │   │   ├── SettingsView.vue    # 家长管理与学科分值设置
│   │   │   ├── PaperCenterView.vue # A4 智能组卷工作台
│   │   │   ├── PaperPrintView.vue  # A4 试卷预览与打印视图
│   │   │   └── AboutView.vue       # 系统关于与运行环境自检
│   ├── index.html
│   └── vite.config.js
├── tests/                    # 自动化测试套件 (52/52 passed)
├── data/                     # 本地持久化数据目录 (SQLite & 上传图片，不入库)
├── doc/                      # 项目设计、演进与变更日志文档
│   ├── change_log.md         # 全量版本变更日志
│   ├── development_plan.md   # 原始开发全景规划
│   └── ...
├── run.py                    # 单进程统一启动服务器 (FastAPI 托管 SPA 前端)
├── start.bat                 # Windows 一键启动脚本
├── pyproject.toml            # Python 依赖清单
└── README.md                 # 项目说明文档
```

---

## ⚡ 快速开始

### 1. 环境准备
- **Python**: `>= 3.11` (推荐使用 [uv](https://github.com/astral-sh/uv) 极速包管理器)
- **Node.js**: `>= 18.0.0` (推荐 Node 20 或 22)
- **操作系统**: Windows 10/11, macOS, Linux 均可

### 2. 克隆与安装依赖

```bash
# 克隆仓库
git clone https://github.com/your-username/study_trace.git
cd study_trace

# 1. 安装后端 Python 依赖 (通过 uv)
uv sync

# 2. 安装前端 Node 依赖并构建
cd frontend
npm install
npm run build
cd ..
```

### 3. 初始化数据库与种子数据

```bash
# 执行数据库迁移与初始数据预置
uv run alembic upgrade head
uv run python -m backend.app.seed
```

### 4. 启动服务

**方法 A：统一生产/演示模式（推荐）**
直接运行根目录下的 `run.py`，FastAPI 将直接托管前端已构建好的静态资源，单端口运行：
```bash
uv run python run.py
```
或在 Windows 下双击 `start.bat`。  
打开浏览器访问：`http://localhost:8000`

**方法 B：前后端分离联调开发模式**
- 终端 1（后端 API）：
  ```bash
  uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- 终端 2（前端 Vite Dev）：
  ```bash
  cd frontend
  npm run dev
  ```
  访问开发调试地址：`http://localhost:5173`（自动代理 `/api` 请求至 8000 端口）

---

## 🧪 自动化测试与工程规范

项目保持 **100% 测试通过率** 与严格的工程准则。

```bash
# 运行后端全量自动化测试 (覆盖作业、艾宾浩斯、OCR、通知、A4组卷、成绩分析、备份等)
uv run pytest tests/
```

### 前端无 Emoji 约束与代码扫描
项目制定了严格的 **Zero-Emoji 规范**，所有界面图标统一采用矢量线性图标与轻量语义徽标，严禁侵入 Unicode 字符。
```bash
# 验证前端源码是否符合 0 Emoji 规范
uv run python -c "
import os, re
pattern = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]')
for root, _, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.vue', '.js', '.css', '.html')):
            with open(os.path.join(root, f), 'r', encoding='utf-8') as fp:
                for idx, line in enumerate(fp, 1):
                    if pattern.search(line):
                        print(f'Emoji found at {f}:{idx}')
"
```

---

## 📖 变更历史 (Change Log)

关于本项目从 M0 到当前版本的全部历史迭代与技术演进，请参阅详细变更记录文档：  
👉 [查看完整变更日志 (doc/change_log.md)](doc/change_log.md)

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 协议开源。
欢迎提出 Issue 或 Pull Request 共同优化初中生学习体验！
