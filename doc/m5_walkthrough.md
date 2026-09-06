# M5 — 成绩台账 + 学情图表 + 家长深度看板 完整交付报告

> 依据 `doc/m5_plan.md` 约束与核心架构共识，M5 里程碑已全部编码落地，并通过全量自动化测试（51/51 通过）与前端构建体积断言（ECharts 独立分包 Gzip ~204KB）。

---

## 一、 核心功能与架构落地清单

### 1. 权限归属与双入口设计
- **孩子专注端**：底部 Tabbar 新增第 3 项 `学情成绩`（`/scores`），默认只读呈现成绩走势折线、7 科均衡雷达、薄弱学科诊断与考试历史台账。
- **保护性门禁**：在 `/scores` 页面点击「录入成绩」、单项「编辑」或「删除」时，触发家长 6 位 PIN 码验证弹窗（默认 `888888`）。验证通过后缓存于会话，无需重复输入。
- **家长空间入口**：在 `/settings` 家长管理空间显式新增「成绩管理与录入」入口，实现双入口闭环。

### 2. 数据库与数据迁移
- 新建 `exam_records`（考试主表）与 `exam_scores`（成绩明细表），建立级联删除与 `(exam_id, subject_id)` 唯一复合索引。
- 执行 Alembic 物理迁移版本：`b7751890cf12_create_exam_tables.py`。

### 3. ECharts 按需加载与体积控制
- 在 `frontend/src/utils/echarts.js` 中按需引入 `LineChart`、`RadarChart`、`BarChart` 及 `CanvasRenderer`。
- 配置 `vite.config.js` 的 `manualChunks` 将 `echarts-vendor` 独立拆包，生产构建测得：
  - `echarts-vendor.js`: 600.61 kB │ **gzip: 204.26 kB**（远低于 300KB 严苛约束指标）。
  - `vant-vendor.js`: 161.11 kB │ **gzip: 60.16 kB**。
  - `index.js`: 170.49 kB │ **gzip: 60.47 kB**。

### 4. 关键算法与业务规则
- **缺考分子分母跳过规则**：单科标记缺考（`is_absent=True`）时，`score` 自动置空，`total_score` 与 `total_full_score` 分子分母同时跳过该科目。
- **雷达图动态指标轴防御**：ECharts 雷达对 `null` 不原生跳过，因此后端动态过滤实考科目构建 indicators（如 6 科实考生成 6 边形），并在图表下方明确标注「⚠️ XX 缺考，未计入本次雷达图」；实考不足 3 科时优雅降级为占位提示。
- **单次考试单点安全防御**：走势折线图在仅有 1 次考试数据时以单参考点平稳呈现，绝不发生前端报错。
- **薄弱学科极简诊断**：
  $$\text{单科近期得分率} < 60\% \quad \lor \quad \text{错题本未掌握顽固题} \ge 3$$
  命中时直观展示诊断卡片并支持一键直跳错题本复习。
- **家长月度作业透视**：
  - 整月每日打卡率平滑曲线（1~31 日）。
  - 各学科未完成频次分布柱状图，直观比对作业缺口与考试起伏。

---

## 二、 自动化验证结果

### 1. 后端单元测试
执行命令：`.venv\Scripts\python.exe -m pytest tests/`
- **全项目测试用例集**：**51 passed**（耗时 15.84s，通过率 100%）。
  - `test_health.py`: 1 passed
  - `test_m1_core.py`: 9 passed
  - `test_m2_ocr.py`: 8 passed
  - `test_m3_notifications_and_calendar.py`: 15 passed
  - `test_m4_paper_and_print.py`: 13 passed
  - `test_m5_scores_and_analytics.py`: 5 passed（涵盖 CRUD、缺考分子分母、单点折线、雷达动态轴、薄弱诊断与月度聚合）

### 2. 演示数据播种
执行命令：`.venv\Scripts\python.exe scripts\seed_m5_demo.py`
成功预置 4 场典型考试：
1. **初一上学期第 1 次月考**（7 科齐全，满分 760，实考 668，满分率 87.9%）；
2. **初一上学期期中考试**（7 科齐全，满分 760，实考 697，满分率 91.7%）；
3. **初一上学期第 2 次月考**（地理因感冒缺考，满分自动核算为 660，实考 598，雷达图生成 6 边形并标注地理缺考）；
4. **初一数学第 3 单元周测**（单科测试，118/120，雷达图触发友好不足 3 科 fallback）。

### 3. Git 状态纯净度
工作区无遗留临时文件，无未识别的 `.venv` 或开发缓存目录，完全满足工程规范。
