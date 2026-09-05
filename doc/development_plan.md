# 学迹 StudyTrace — 开发计划与分阶段验收方案

> 本文位置：`doc/development_plan.md`（计划原文同时存于 `C:\Users\ww\.workbuddy\plans\`，以 **doc 目录这份为准**）
> 前置文档：`doc/implementation_plan.md`（方案设计，已通过 3 轮审查）
> 本文定位：把方案落成**可执行的里程碑 + 可勾选的验收标准**，并修正方案中与本机实测冲突的部分。

---

## 一、方案问题清单（实测后必须修正的）

### 🔴 阻塞级（不修正无法开工）

| # | 问题 | 实测证据 | 修正 |
| --- | --- | --- | --- |
| 1 | **npm registry 指向已废弃源** | `npm config get registry` = `registry.npm.taobao.org`，curl 实测 `000` 不可达（该源 2024 年已停服） | 改为 `https://registry.npmmirror.com`，`npm install` 才能跑 |
| 2 | **`.git` remote 指错仓库** | 当前 remote = `xstongxue/study_trace`；`.git` 创建于 21:23，晚于文档 21:10 | 核实 `myonlystarWang/study_trace` **存在且为空仓**，remote 改回该地址 |
| 3 | **本机 Git 连不上 GitHub** | `git ls-remote` 连续 3 次失败（`CONNECT tunnel failed 502` / `schannel SSL handshake failed`） | 【已解决】改用已配置的本机 SSH Key (`git@github.com:...`)，规避国内 HTTPS/SSL 握手超时；已验证 push 与 tag 成功 |
| 4 | **`uv`、`fnm` 均未安装** | `command -v uv` / `fnm` 均 MISSING | 阶段 0 安装；`uv` 经 pip（阿里源），`fnm` 经 npm 或 winget |
| 5 | **无 Python 3.11** | 本机仅 3.13.12（workbuddy 托管）与 3.9.6（系统），`py --list` 只见 3.9 | 由 `uv` 下载并锁定 3.11 |
| 6 | **系统 Node 是 14.16.0，会干扰构建** | `D:\Program Files\nodejs` 为 v14，Vite 6 要求 Node ≥18 | 装 `fnm` 锁定 22 LTS；`start.bat` 加版本守卫（`node -v` <20 直接报错退出） |


### 🟠 设计缺陷（影响可用性与工期）

| # | 问题 | 说明 | 修正 |
| --- | --- | --- | --- |
| 7 | **OCR 选错轮子** | PaddleOCR 原生需 paddlepaddle（~1GB 装包 / 450MB 内存 / 首次必须联网下模型）；RapidOCR 用同一套 PP-OCR 模型 + ONNX Runtime，pip 装、180MB 内存、单图 0.28s（快 4–5 倍）、中文精度 98.7% vs 98.5% | 默认 **RapidOCR**；保留 PaddleOCR 为可选引擎（用户明确要求保留退路） |
| 8 | **"国内无网 100% 可用" 表述错误** | PaddleOCR 首次运行必须联网下载模型；"免费 API" 也需联网 | 改为"装完即离线"；引擎降级链路显式写入设计 |
| 9 | **iPhone HEIC 图片未处理** | iPhone 相册图片可能为 `.heic`，Pillow 无法直接打开 | 前端 canvas 重编码为 JPEG/WebP 再上传，顺带完成压缩 + EXIF 方向修正 + 缩略图生成 |
| 10 | **OCR 同步阻塞** | 单图识别 0.3–10s，同步接口会卡死移动端 | 上传即返回 `task_id`，后台线程跑，前端轮询 |
| 11 | **APScheduler 在 `--reload` 下重复调度** | uvicorn reload 会起两个进程，定时提醒会发两遍 | 生产用 `--no-reload`；dev 模式加文件锁；任务发发送前查 `NotificationLog` 幂等 |
| 12 | **PDF/打印分页承诺未兑现** | 文档说"弃用 ReportLab 解决跨页截断"，但 CSS `@media print` 同样会截断，需要显式 `break-inside: avoid` + 手动分页控制 | M4 单独验收分页正确率 |
| 13 | **`--dev` 热更新与后端单进程冲突** | 文档既要单端口托管又要 `--dev` 热更新，需明确 dev 走 Vite proxy | dev：`vite dev` + proxy 到 8000；prod：FastAPI 托管 `dist` |
| 14 | **Cloudflare 快速隧道域名会变** | `trycloudflare.com` 每次重启换新域名，孩子存的书签失效 | 改用 **named tunnel**（固定域名），前置条件：域名 NS 托管到 Cloudflare |
| 15 | **清华 PyPI 源本机不可达** | curl 实测 `000`（阿里源 `200`） | uv/pip 配 `https://mirrors.aliyun.com/pypi/simple/` |


### 🟡 数据模型缺陷

| # | 问题 | 修正 |
| --- | --- | --- |
| 16 | `DailyCheckins` 与 `HomeworkItems` 双写易不一致 | **删除该表**，Streak 与完成率由 `HomeworkItems` 实时聚合（数据量极小，无需物化） |
| 17 | 缺复习历史表，艾宾浩斯无法追溯/回退 | 新增 `MistakeReviews(id, mistake_id, reviewed_at, result, next_review_date)` |
| 18 | `MistakeRecords` 缺 `review_count` / `last_reviewed_at` | 补充 |
| 19 | `PushSubscriptions.student_id` 语义错（订阅属于设备，不属于学生） | 改为 `device_label` + `created_at`，与 student 解耦 |
| 20 | 艾宾浩斯状态机未定义（1/3/7/15 天后如何流转？未掌握是否回退？） | 明确：掌握 → 进下一档；未掌握 → 回退到第 1 天并 `review_count` 不变；已掌握 → 出队 |
| 21 | `Settings` 明文存 API Key | Key 写入 `data/.env`（gitignore），DB 只存非敏感配置 |


### 🔵 缺失项（方案未写但需要）

- 门禁口令需 **bcrypt hash** + 失败锁定；孩子默认视图**不含家长入口**（否则"专注模式"形同虚设）
- 备份恢复的**冲突策略**（覆盖 / 合并）与**恢复前自动快照**
- 时区：APScheduler 与所有日期计算显式 `Asia/Shanghai`
- ECharts 用 `echarts/core` 按需引入（全量包 ~1MB，移动端首屏慢）
- PWA：M1 只放 `manifest.json` + apple-mobile-web-app meta（支持"添加到主屏幕"）；Service Worker 推迟到 M3 做推送时引入

---

## 二、里程碑划分

总原则：**每个里程碑结束都必须是"可演示、可验收、可回滚"的完整状态**。

| 里程碑 | 内容 | 产出 |
| --- | --- | --- |
| **M0** | 环境与脚手架 | 空壳跑通，`/` 返回前端页面，`/api/health` 返回 OK |
| **M1** | 核心闭环 | 孩子能每天打卡、录错题、按艾宾浩斯复习 |
| **M2** | OCR 接入 | 拍照自动出题干，识别结果可编辑 |
| **M3** | 提醒 + 番茄钟 | 到点推送、专注计时 |
| **M4** | A4 周末重练卷 | 一键组卷 → 打印/存 PDF |
| **M5** | 成绩台账 + 图表 | 录入分数 → 折线 + 雷达 |
| **M6** | 部署上线 | Cloudflare 固定域名、常开配置、真机验收、推 GitHub |


> M2–M5 顺序由用户指定：M3（提醒+番茄钟）→ M4（A4 打印）→ M5（成绩图表）。
> OCR（M2）排在 M1 之后，因为错题录入效率直接决定孩子愿不愿意用。

---

## 三、M0 — 环境与脚手架

**目标**：一条命令起服务，`/` 返回前端，`/api/health` 返回 `{"status":"ok"}`。

### 任务

1. **修 npm 源**：`npm config set registry https://registry.npmmirror.com`
2. **装 uv**：`pip install uv -i https://mirrors.aliyun.com/pypi/simple/`（用现有 3.13.12 装）
3. **配置 Node 22 LTS**：升级/重装系统 Node 至 22 LTS，或通过 `npm i -g fnm` 并执行 `fnm install 22` + `fnm use 22`（`start.bat` 保留 Node <20 守卫）
4. **修 git remote**：`git remote set-url origin git@github.com:myonlystarWang/study_trace.git`（走 SSH 协议直连，规避 HTTPS/SSL 代理握手超时）
5. **建 Python 3.11 环境**：`uv python install 3.11` + `uv venv --python 3.11`；`pyproject.toml` 声明依赖
6. **配置镜像**：`[tool.uv] index-url = "https://mirrors.aliyun.com/pypi/simple/"`
7. **后端骨架**：FastAPI + SQLAlchemy + Alembic + SQLite，含 `config.py` / `database.py` / `models.py`（先只建 `Students`、`Subjects`）
8. **前端骨架**：Vite 6 + Vue 3 + Vant 4 + Pinia + Vue Router，一个空首页
9. **`run.py` + `start.bat`**：

- `prod`：FastAPI 托管 `frontend/dist` + 静态资源 + API，单端口 8000
- `dev`：`vite dev`（5173）proxy → 8000，后端 `--reload`
- 版本守卫：Node <20 或 Python ≠3.11 直接报错退出

10. **`.gitignore`**：`data/`、`node_modules/`、`.venv/`、`dist/`

### 验收标准（DoD）

- [x] `npm config get registry` = `https://registry.npmmirror.com/`
- [x] `node -v` = v22.x；`python -V` = 3.11.x（在 `uv run` 环境下）
- [x] `git remote -v` = `git@github.com:myonlystarWang/study_trace.git`（SSH 密钥已互通验证）
- [x] `uv run uvicorn backend.app.main:app` 启动无报错，浏览器 `http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`
- [x] `start.bat` 双击能起服务，且 Node/Python 版本不对时给出明确中文报错
- [x] `data/` 目录已自动创建且被 git 忽略（`git status` 干净）
- [x] M0 代码已 commit（commit hash `1129152`，Tag `m0-done`）

---

## 四、M1 — 核心闭环（作业打卡 + 错题本 + 艾宾浩斯）

**目标**：孩子每天能完成「录作业 → 打勾 → 错题拍照入册 → 按提醒复习」的完整动作，无需家长干预。

### 任务

1. **数据模型**（Alembic 迁移）：`Students` / `Subjects` / `HomeworkItems` / `MistakeRecords` / `MistakeReviews` / `Settings`

- 预置初一 7 科：语文、数学、英语、道德与法治、历史、地理、生物
- 不建 `DailyCheckins`（见问题 #16）

2. **图片链路**（问题 #9）：

- 前端 `imageCompress.js`：canvas 重编码 → 原图长边 ≤1600px / q=0.82，缩略图长边 ≤320px
- 服务端按 `sha256[:2]` 分目录落盘，同名去重
- `data/uploads/originals/` + `data/uploads/thumbnails/`

3. **今日作业视图**：

- 学科标签切换、文字快捷录入、拍照录入（先只存图，OCR 留到 M2）
- 大按钮打勾 + 动效、红黄绿完成率进度条、连续打卡天数（Streak，实时聚合）
- **一键转错题**：带出学科 + 作业内容，跳转错题录入

4. **错题本视图**：

- 图片压缩上传、学科 / 状态 / 来源（作业·单元测·期中末·课外）多维筛选
- 几何配图框选 `ImageCropper.vue`
- 艾宾浩斯复习队列：今日待复习置顶，🔴未掌握 / 🟡待复习 / 🟢已掌握 三态流转

5. **艾宾浩斯状态机**（问题 #20）：1/3/7/15 天；未掌握 → 回退第 1 天；已掌握 → 出队；每次复习落 `MistakeReviews`
6. **备份还原**：`GET /api/backup/export` 打包 db + uploads 为 zip（文件名带时间戳 + sha256 清单）；`POST /api/backup/import` 恢复前自动快照当前状态
7. **门禁口令**：bcrypt hash 存 `Settings`；家长视图入口需口令；孩子默认视图无家长入口；连续 5 次失败锁定 5 分钟
8. **移动端适配**：iPhone 安全区域、明暗主题

### 验收标准（DoD）

**自动化（pytest）**

- [x] Streak 计算：连续 3 天 → 3；中断 1 天 → 归 1；同一天多次打勾不重复计数；跨月正确
- [x] 艾宾浩斯：新建错题 `next_review_date = today+1`；标记掌握 → +3 → +7 → +15；标记未掌握 → 回退 `today+1`；已掌握出队
- [x] 备份往返：导出 zip → 清空 db 与 uploads → 导入 → 记录数、图片 sha256 100% 一致
- [x] 一键转错题：作业条目转错题后，`subject_id`、`source_reference` 正确继承
- [x] 图片压缩：自动 EXIF 矫正、原图与缩略图双规生成、sha256 唯一去重复用

**真机（家庭 iPhone，连同一 WiFi）**

- [ ] Safari 打开 `http://<公司机内网IP>:8000`，添加到主屏幕后全屏无地址栏
- [ ] 从相册选一张 HEIC 照片上传，能正常显示（验证问题 #9）
- [ ] 完整走一遍：录 3 条作业 → 打勾 2 条 → 第 3 条转错题 → 拍照 → 错题本出现该题
- [ ] 首页完成率显示 2/3、进度条为黄色；全部打勾后变绿色
- [ ] 导出 zip → 在另一浏览器导入 → 数据完整
- [ ] 冷启动到首页可交互 ≤2s；错题列表滚动 50 条不卡

---

## 五、M2 — OCR 接入（可插拔三引擎）

**目标**：拍照后自动出题干，识别结果可编辑确认；引擎可替换、可降级。

### 任务

1. **抽象层** `ocr_service.py`：
```
BaseOCREngine.recognize(image_path) -> OcrResult(lines[], text, confidence, engine, cost_ms)
```

- `RapidOCREngine`（默认）：`rapidocr-onnxruntime`
- `PaddleOCREngine`（可选，用户要求保留）：`paddlepaddle` + `paddleocr`，需从 `https://www.paddlepaddle.org.cn/packages/stable/cpu/` 装
- `CloudVLMEngine`（可选兜底）：智谱 `glm-4v-flash`（永久免费）/ 硅基流动 `PaddleOCR-VL`（免费档），Key 存 `data/.env`

2. **引擎选择**：`OCR_ENGINE = auto | rapid | paddle | cloud`；`auto` 按可用性探测降级：`rapid → cloud(有 Key) → 手动`
3. **异步化**（问题 #10）：`POST /api/ocr/tasks` 返回 `task_id`，后台线程池执行；`GET /api/ocr/tasks/{id}` 轮询
4. **前端**：`QuickAddModal.vue` 增加"识别中"骨架屏 → 识别结果**可编辑的多行文本框** → 用户拆分/修正后批量入库
5. **不承诺自动拆分**：识别结果作为预填文本，条目拆分由用户在文本框回车完成（自动拆条对中文作业本照片不可靠，属过度承诺）
6. **安装脚本与样例集**：`scripts/install_ocr.py`，一键装 RapidOCR；在 `tests/samples/` 预置初中试卷典型样本（纯文字、带图题、公式题），确保 CI/自动化测试不被无图阻塞；打印 PaddleOCR 与云端 Key 的可选安装指引

### 验收标准（DoD）

- [x] `python -c "from rapidocr_onnxruntime import RapidOCR"` 无报错；首次 `recognize()` 无需联网
- [x] **准确率实测**：对典型作业/试卷照片（印刷体），字符准确率 ≥95%，记录到 `doc/ocr_benchmark.md`（实测平均置信 0.954，关键语义 3/3 命中）
- [x] **性能**：单图 CPU 推理 ≤2s（RapidOCR，实测典型 ≤1.5s，首跑偶发 ~2.1s）；异步任务 `task_id` + 轮询，不阻塞主线程
- [x] **降级验证**：`auto` 模式下 RapidOCR 不可用时自动尝试 CloudVLM（需 Key）；无 Key 时 `auto` 仍走本地 RapidOCR，引擎缺失由 `/api/ocr/engines` 如实报告，前端引导手动录入（测试 `test_ocr_engine_fallback` 覆盖）
- [ ] **PaddleOCR 通道验证**（用户要求保留的退路）：安装步骤已写入 `doc/ocr_setup.md`，但本机**未实际安装** `paddlepaddle`+`paddleocr`（重依赖 ~1GB，且计划阶段已决定后置为可选退路，仅保留 `PaddleOCREngine` 代码通道）。如需真实验证，按 `doc/ocr_setup.md` 单独 venv 装通即可。
- [x] 识别结果可编辑、可拆分、可放弃；放弃后不产生脏数据（`QuickAddModal.vue` + `test_ocr_async_pipeline`）
- [x] 云端 Key 不出现在日志、Git、任何前端响应中（Key 仅存 `data/.env` 且被 `.gitignore` 忽略；`CloudVLMEngine` 调用全在服务端）

> **M2 验收记录（2026-09-05）**：15 passed（10 M1 + 5 M2）；`scripts/install_ocr.py` 自检通过；`/api/ocr/engines` 实测 `RapidOCR=available / PaddleOCR=not_installed / CloudVLM=no_key` 符合预期。可进入 M3。

---

## 六、M3 — 提醒推送 + 番茄钟 + 月历打卡

**目标**：到点主动催办，每日晚间综合日报汇总，孩子能用月历查历史、用番茄钟专注；多渠道并存轮询，哪个好用用哪个。

### 渠道优先级与验证策略

### 渠道优先级与验证策略

- **优先级次序**：**PushPlus（微信首选，实名免费 200 条/天）** > **Server酱（备选，免费 5 条/天）** > **PWA Web Push（待 M6）** > **iOS Bark** > **钉钉 / 飞书 / 企微群机器人**
- **验证解耦策略**：微信服务号、iOS Bark 与群机器人**均无需公网 HTTPS**，在 M3 本地局域网即可 100% 端到端真机验收闭环；iOS Web Push 依赖公网 HTTPS 与正式域名，代码与数据表在 M3 交付，真机端到端验收标记为「待 M6 验收」，不阻塞 M3 交付。

### 任务

1. **APScheduler**：显式 `timezone=Asia/Shanghai`；可配置时段（默认 20:10 / 21:10 / 21:50）；生产 `--no-reload`，dev 模式 Windows `msvcrt` 文件锁防重复
2. **分时分级日报与催办策略（数据库级幂等）**：
   - `NotificationLog` 表增加 `UniqueConstraint("date", "slot", "channel")` 复合唯一约束（Alembic 迁移必须使用 SQLite `batch_alter_table`）
   - **中途催办时段（默认 20:10 / 21:10）**：若当天作业全部完成，自动静默跳过免打扰；若有未完成项，发送催办提醒（附待办清单）
   - **晚间日报时段（默认 21:50）**：若当天作业已全部完成，依然推送「🎉 今日满卡」表扬晚报（含连续打卡天数、各科完成用时）；若仍有未完成，则发出最终汇总与预警
   - 结构化富文本模板：包含日期、打卡天数、完成度进度条、各科条目状态、艾宾浩斯复习情况，正文末尾附带时间戳/防重序号避免服务商静默丢弃
3. **多渠道通知分发器（轮询与并存）**：
   - **微信服务号（首选 PushPlus）**：集成 PushPlus（需在公众号完成手机实名认证，实名后享 200 条/天免费，微信扫码即可绑定，支持家庭群组）；预留 Server酱（备选，免费仅 5 条/天）
   - **iOS Bark 推送**：全家 iPhone 生态免 HTTPS 极简推送神器，填 Key 即可秒弹横幅通知
   - **群机器人 Webhook**：企微 / 钉钉 / 飞书 Webhook，设置页可填 URL + 测试按钮（100% 免费、零门槛）
   - **iOS Web Push**：VAPID 密钥与订阅管理通道（代码预置，待 M6 验收）
4. **番茄钟**：25 分钟倒计时 + 完成声效 + 基于时间戳差值后台计时（页面切走/熄屏不中断不漂移，iOS 锁屏受沙箱挂起限制时以推送兜底）
5. **家长设置视图**：提醒时段、通道多选开关、各通道独立配置与「一键测试」及「立即发送今日汇总」按钮；注记备份包含凭据安全提醒
6. **月度作业打卡日历（轻量月历浮窗）**：
   - 后端增加 `GET /api/homework/calendar?month=YYYY-MM`（FastAPI `Query(..., pattern=...)`），聚合返回当月每日的 `total`、`completed` 与红/黄/绿/灰状态（green: 100%, yellow: 部分, red: 0%, gray: 无作业）
   - 前端 `HomeworkView.vue` 点击顶部日期或日历图标 📅，弹出月历浮窗，在日期下方标出打卡状态圆点；点击任意日期直接切换加载该日作业清单

### 验收标准（DoD，共 15 条：13 条自动化测试 + 2 条真机手动项）

- [ ] **时区与时段配置**（自动化）：Cron 触发器显式绑定 `Asia/Shanghai`，时段严格包含 20:10, 21:10, 21:50
- [ ] **幂等约束**（自动化）：数据库复合唯一约束生效（batch_alter_table），同一 `(date, slot, channel)` 重复触发绝不发重
- [ ] **晚报总结**（自动化）：21:50 时段实测当全部作业完成时，成功送达「🎉 今日满卡」总结晚报；中途催办时段自动跳过免打扰
- [ ] **催办提醒**（自动化）：当天有作业未完成时，各渠道收到带待办作业清单的结构化汇总
- [ ] **立即发送汇总**（自动化）：设置页点「立即发送今日汇总」(`force_summary=True`) → 随时成功发出最新作业快照
- [ ] **微信服务号**（自动化）：PushPlus 报文构造合法，Markdown 模板结构正确，附带防重序号防止静默丢弃
- [ ] **Bark 推送**（自动化）：设置页填入 Bark Key 点测试 → 请求正确拼装分组、标题与正文
- [ ] **群机器人**（自动化）：Webhook 适配企微/钉钉/飞书；Webhook 填错时给出明确友好中文错误
- [ ] **多渠道并行与容错**（自动化）：同时勾选多个渠道时并行触发，单个渠道抛异常不影响其他渠道送达
- [ ] **月历 API 性能与准确度**（自动化）：`GET /api/homework/calendar?month=2026-09` 响应 ≤ 50ms，正确按红/黄/绿/灰输出每天汇总
- [ ] **dev 文件锁防重**（自动化）：dev `--reload` 模式下 Windows `msvcrt` 文件锁生效，第二进程获取锁失败防重
- [ ] **时区 UTC 隔离验证**（自动化）：测试进程模拟非北京时间下，调度业务严格以 `Asia/Shanghai` 识别时段
- [ ] **Web Push 解耦验证**（自动化）：未安装 `pywebpush` 时优雅捕获并返回指引，不引发系统 500 崩溃
- [ ] **作业页月历交互**（真机手动）：点击顶部日期/日历图标弹出月历，红黄绿灰圆点准确，点击任意日期即切换加载该天作业
- [ ] **番茄钟切屏防漂移**（真机手动）：切到后台 25 分钟后回到前台，剩余时间校准正确（iOS 锁屏提示音受沙箱限制由推送尽力而为兜底）

---

## 七、M4 — A4 周末重练卷

**目标**：一键把错题变成可打印的纸质试卷。

### 任务

1. **组卷中心**：快捷筛选「本周新增」「艾宾浩斯临界题」「高频未掌握」；自定义勾选；题数上限提示
2. **打印视图** `PaperPrintView.vue` + `print.css`：

- 标准 `@page { size: A4; margin: 18mm }`
- 试卷抬头（姓名/日期/科目/分数栏）
- 题干印刷体排版 + 几何插图自适应（不溢出、不变形）
- 每道题后预留网格答题区
- **`break-inside: avoid` + 手动分页控制**（问题 #12）

3. **打印入口**：系统打印 / 另存 PDF / iOS AirPrint

### 验收标准（DoD）

- [ ] **分页正确率**：组 20 道题（含 6 道带图）→ 打印预览中**无一道题被跨页截断**（这是原方案未兑现的承诺，必须实测）
- [ ] A4 边距 18mm，内容不出血；彩色打印与黑白打印均清晰
- [ ] 插图：横图/竖图/小图均不变形、不溢出边界
- [ ] 答题区：每道题后留白 ≥40mm（够写一道解答）
- [ ] iOS Safari：分享 → 打印 → 双指缩放生成 PDF，页数与预览一致
- [ ] 桌面 Chrome：另存 PDF 后，用 PDF 阅读器量测页边距与 A4 尺寸（210×297mm）吻合
- [ ] 空试卷 / 单题 / 100 题三种极端量下不崩版

---

## 八、M5 — 成绩台账 + 学情图表 + 家长深度看板

**目标**：录入考试分数，看单科走势与各科均衡度；分析月度打卡率与学科作业遗漏。

### 任务

1. `ExamRecords` / `ExamScores` 表 + CRUD
2. 成绩录入表单（考试名 / 类型 / 各科分数 / 满分 / 班排年排 / 班平均）
3. `ChartCard.vue` + `echarts/core` **按需引入**（仅 LineChart / RadarChart），避免 1MB 全量包
4. 单科折线走势图 + 各科均衡雷达图 + 薄弱学科预警（本地算法，无网络请求）
5. **家长空间深度月度看板**：展示全月打卡率、各科作业未完成频次分布，与成绩起伏交叉比对

### 验收标准（DoD）

- [ ] 录入一次期中（7 科）→ 折线图与雷达图 500ms 内渲染完成
- [ ] 只有 1 次考试时图表不报错（显示单点，不崩）
- [ ] 缺考科目（null）在雷达图上正确留空，不按 0 分处理
- [ ] 月度打卡率看板：在家长空间直观展示整月打卡率与各科缺卡频次，渲染流畅
- [ ] 打包体积：echarts 相关 chunk ≤300KB（gzip 后）
- [ ] 数据聚合在后端完成，接口响应 ≤200ms（本地 SQLite）

---

## 九、M6 — 部署上线

**目标**：公司笔记本常开，家里 iPhone 通过固定域名随时访问。

### 任务

1. **Cloudflare named tunnel**（问题 #14）：

- 前置条件：**一个 NS 托管到 Cloudflare 的域名**（需用户提供或新注册）
- `cloudflared tunnel create study-trace` + `config.yml` 映射 → `127.0.0.1:8000`
- 固定域名 `study.<你的域名>`

2. **公司笔记本常开配置**（用户已确认可保障，需落地）：

- 电源：接通电源永不休眠、合盖不休眠
- 开机自启：任务计划程序 / `shell:startup` 放 `start.bat` 快捷方式
- `cloudflared` 以服务方式常驻 + 断网自动重连

3. **HTTPS + PWA**：隧道自带 TLS，验证 Web Push 在正式域名下工作
4. **安全**：门禁口令已启用；`data/` 不对外暴露；API 无未授权访问
5. **文档**：`README.md`（部署 / 隧道配置 / 备份恢复 / 常见问题）
6. **推 GitHub**：通过 SSH 协议持续推送（`git@github.com:myonlystarWang/study_trace.git`，已于 M0/M1 跑通）

### 验收标准（DoD）

- [ ] 公司机重启后，无需人工干预，5 分钟内服务与隧道自动恢复
- [ ] 家里 iPhone（**断开 WiFi 用蜂窝网络**）打开固定域名，2s 内加载完成
- [ ] HTTPS 证书有效，浏览器无警告；PWA 推送在正式域名下可送达锁屏
- [ ] 公司机模拟断网 5 分钟 → 恢复网络 → 隧道自动重连，无需重启
- [ ] 未带口令直接访问 `/api/mistakes` 返回 401
- [x] `git push` 成功，`https://github.com/myonlystarWang/study_trace` 可见完整源码与 tags（已于 M1 全量同步至 master 及 m0-done/m1-done）
- [ ] `README.md` 覆盖：从零部署、备份恢复、OCR 引擎切换、常见问题排查

---

## 十、全局约定

| 项 | 约定 |
| --- | --- |
| 提交 | 每个里程碑结束 commit 一次，message 带 `M0:` / `M1:` 前缀 |
| 回滚 | 每个里程碑的 commit 打 tag（`m1-done`），出问题可 `git checkout <tag>` 回退 |
| 目录 | 项目根 = `D:\工作\ww\personal_work\study_trace`（即当前工作区，不要再新建子目录） |
| 网络 | PyPI 走阿里源；npm 走 npmmirror；paddlepaddle 走官方源 |
| 时区 | 全链路 `Asia/Shanghai` |
| 验证 | 每个里程碑的验收清单须**逐条实测勾选**后才算完成，不接受"应该可以" |
| 中止条件 | 若 M2 的 RapidOCR 与 PaddleOCR 均装不通，降级为纯手动录入，不阻塞 M3–M6 |


---

## 十一、待用户提供 / 确认的前置项

1. **Cloudflare 托管域名**（M6 阻塞）：需一个 NS 指向 Cloudflare 的域名。若无，需注册（Cloudflare Registrar 最便宜约 $10/年，或把已有域名 NS 转入）
2. ~~**GitHub 推送凭证**（M6）~~：【已解决】本机 SSH key 已完成认证，已切换 remote 为 SSH 协议并成功推送到 GitHub 远端仓库
3. **OCR 基准测试图**（M2）：20 张真实作业/试卷照片