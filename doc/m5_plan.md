# M5 — 成绩台账 + 学情图表 + 家长深度看板（校准精简版）

> 本文位置：`doc/m5_plan.md`  
> 目标：录入初中各次测验与考试成绩，生成单科走势折线图与 7 科均衡学力雷达图；联动错题本诊断薄弱学科；在家长空间提供月度作业打卡深度看板与成绩管理入口。  
> 准则：**彻底剔除过度设计，遵循 8 项极简核心工程约束**。

---

## 一、 核心架构决策（已对齐拍板）

1. **权限归属与双入口设计**：
   - **孩子端 `/scores`**：作为底部 Tabbar 第 3 项（`作业打卡 / 错题本 / 学情成绩`），默认**只读查看**走势折线图、7 科学力雷达图、薄弱学科提示与历史考试台账。
   - **录入/修改/删除门禁**：在 `/scores` 页面点击「录入新成绩」或修改操作时，进行前端 PIN 码校验（若当前会话未解锁则弹窗验证，解锁后缓存于 `sessionStorage`）；与 `homework` / `mistakes` 的轻量设计保持一致，兼顾孩子防误触与本地/测试脚本的极简免鉴权。
   - **设置页（家长空间）双入口**：在家长空间设置页（`/settings`）明确保留「成绩管理与录入」直达入口与「月度学情看板」。
2. **ECharts 雷达图缺考渲染方案**：
   - **动态维度（缺考科目不入轴）**：仅将本次考试实际有成绩的科目作为雷达图 indicator 维度轴（例如 7 科中有 1 科缺考，雷达图生成 6 边形），杜绝 `null` 值被强制拉至轴心 0 点造成严重图形畸变。
   - **显式标注提示**：雷达图下方以卡片标签明确提示「⚠️ 地理缺考，未计入本次雷达图」。
   - **少于 3 科 Fallback**：若实考科目不足 3 门，雷达图展示友好空状态「至少需 3 门科目方可生成雷达图」，绝不报错。
3. **总分与满分缺考计算铁律**：
   - **一句话规则**：缺考科目不计入 `total_score` 与 `total_full_score`（分子、分母同时跳过）。
4. **薄弱预警极简判定规则**：
   - **一句话规则**：单科得分率 $< 60\%$ **或** 该科在错题本中未掌握错题 $\ge 3$ $\to$ 标记为「薄弱学科」，并在页面给出强化复习建议。
5. **核心 7 科白名单复用**：
   - 雷达图与诊断白名单直接从 `backend.app.routers.paper` 导入 `CORE_7_SUBJECTS`，严禁两处重复定义造成漂移。
6. **时区一致性**：
   - 月度数据聚合与统计全链路沿用 `Asia/Shanghai`。
7. **数据播种验证**：
   - 提供 `scripts/seed_m5_demo.py`，预置 3~4 次典型测验（含期中 7 科、含 1 次单科缺考、含 1 次单科周测），支持真机直观验收折线与雷达渲染。

---

## 二、 数据库设计与轻量 API

### 2.1 数据表定义 (`backend/app/models.py`)

#### `exam_records`（考试主表）
- `id`: Integer, primary_key, autoincrement
- `student_id`: Integer, ForeignKey("students.id"), default=1, index=True
- `title`: String(100), nullable=False（如 "初一上学期期中考试"）
- `exam_type`: String(30), default="期中"（自由字符串，如 期中/期末/月考/周测/单元测试）
- `exam_date`: Date, nullable=False, index=True
- `total_score`: Float, nullable=True
- `total_full_score`: Float, nullable=True
- `class_rank`: Integer, nullable=True
- `grade_rank`: Integer, nullable=True
- `remarks`: Text, nullable=True
- `created_at`: DateTime, default=datetime.now

#### `exam_scores`（成绩明细表）
- `id`: Integer, primary_key, autoincrement
- `exam_id`: Integer, ForeignKey("exam_records.id", ondelete="CASCADE"), nullable=False, index=True
- `subject_id`: Integer, ForeignKey("subjects.id"), nullable=False, index=True
- `score`: Float, nullable=True（缺考为 null）
- `full_score`: Float, nullable=False（默认 100/120）
- `class_average`: Float, nullable=True
- `class_rank`: Integer, nullable=True
- `grade_rank`: Integer, nullable=True
- `is_absent`: Boolean, default=False
- 唯一约束：`UniqueConstraint("exam_id", "subject_id", name="uq_exam_subject")`

### 2.2 极简后端接口 (`backend/app/routers/exams.py`)

1. `GET /api/exams`: 获取全部考试列表（无需分页复杂参数，初中全量考试仅几十场，轻量直出）。
2. `POST /api/exams`: 录入单次考试与科目成绩（单事务落库，自动过滤缺考科目的分子分母）。
3. `GET /api/exams/{id}`: 获取指定考试完整科目明细。
4. `PUT /api/exams/{id}`: 修改考试与科目成绩（单事务清空原子重插，无复杂补丁逻辑）。
5. `DELETE /api/exams/{id}`: 级联删除考试及对应明细。
6. `GET /api/exams/charts/trends`: 走势折线数据（支持全科总分走势或指定 `subject_id` 单科走势；1 次考试时返回单点，安全渲染）。
7. `GET /api/exams/charts/radar`: 学力雷达数据（支持动态指标轴，缺考科目输出在 `absent_subjects` 数组中）。
8. `GET /api/exams/diagnostics/weaknesses`: 输出薄弱科目列表（得分率 < 60% 或 未掌握错题 >= 3）。
9. `GET /api/exams/analytics/monthly`: 家长月度深度看板（当月打卡率、各科缺卡频次分布）。

---

## 三、 前端组件与按需 ECharts

1. **`frontend/src/utils/echarts.js`**：
   - 仅引入 `LineChart`、`RadarChart`、`BarChart`、`Grid`、`Tooltip`、`Legend`、`Radar`、`CanvasRenderer`。
   - 打包构建（`npm run build`）肉眼断言产物体积，严格受控。
2. **`ScoreView.vue` (`/scores`)**：
   - 走势折线图卡片（支持总分与 7 科快速切换，单点安全显示）；
   - 学力均衡雷达图卡片（动态轴，缺考显式提示，不足 3 科友好占位）；
   - 薄弱学科预警条（一键直通错题本复习）；
   - 考试台账历史卡片；
   - 录入弹窗：自动排齐 7 科与默认满分，支持缺考开关，需验证家长 PIN 后方可调起/提交。
3. **`SettingsView.vue`（家长空间）**：
   - **成绩管理与录入入口**：新增 `van-cell title="成绩管理与录入" is-link to="/scores"` 单元格，确保双入口无缝闭环；
   - **月度学情深度看板**：提供整月打卡率走势折线 + 各科未完成频次柱状图，支持与考试成绩起伏交叉比对。
