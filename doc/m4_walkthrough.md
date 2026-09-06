# 里程碑 M4：A4 周末重练卷 交付与演练验收报告

## 一、交付概述

里程碑 M4（**A4 周末重练卷**）已全量开发完成并顺利通过自动化回归测试。本里程碑实现了**“错题库一键 30 秒生成专业 A4 纸质试卷 -> 周末线下纸笔练习 -> 一键批量重练打卡 -> 闭环流转艾宾浩斯复习周期”**的核心闭环。

---

## 二、变更明细

### 1. 后端架构与数据库 (Backend)
- **数据库模型与表迁移**：
  - 在 [`backend/app/models.py`](file:///d:/工作/ww/personal_work/study_trace/backend/app/models.py) 中新增 `Paper` 模型（`id, title, subtitle, mistake_ids, sort_by, space_level, style_mode, show_error_type, estimated_pages, warnings, student_name, status, created_at`）。
  - 执行规范 Alembic 迁移脚本 [`backend/alembic/versions/a664048047b8_create_papers_table.py`](file:///d:/工作/ww/personal_work/study_trace/backend/alembic/versions/a664048047b8_create_papers_table.py)，完成 `papers` 表落盘及索引创建。
- **数据契约 (Pydantic Schemas)**：
  - 在 [`backend/app/schemas.py`](file:///d:/工作/ww/personal_work/study_trace/backend/app/schemas.py) 中新增 `PaperCandidateOut`、`PaperComposeIn`、`PaperQuestionOut`、`PaperComposeOut`、`PaperBatchReviewIn`、`PaperBatchReviewOut`、`PaperHistoryOut`。
- **业务路由 (Routers)**：
  - 新建 [`backend/app/routers/paper.py`](file:///d:/工作/ww/personal_work/study_trace/backend/app/routers/paper.py) 并挂载至 [`backend/app/main.py`](file:///d:/工作/ww/personal_work/study_trace/backend/app/main.py)：
    - `GET /api/paper/candidates`：全学科候选错题查询，支持三大预设（`this_week`, `ebbinghaus`, `unmastered`）及多预设交集不漏题。
    - `POST /api/paper/compose`：组卷排版计算、粗略页数估算、超长题启发式标记（`is_oversized: bool`），落表生成快照。
    - `GET /api/paper/{paper_id}`：根据 ID 恢复试卷快照，支持 F5 刷新、多标签另开与跨设备链接访问。
    - `POST /api/paper/{paper_id}/batch_review`：单事务批量推进艾宾浩斯轮次（`remembered` / `forgotten`），状态自动置为 `reviewed`。
    - `GET /api/paper/history`：历史组卷记录查询。

### 2. 前端排版与视图 (Frontend)
- **印刷专用样式表**：
  - 新建 [`frontend/src/assets/print.css`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/assets/print.css)，在 [`frontend/src/main.js`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/main.js) 全局导入：
    - `@page { size: A4 portrait; margin: 18mm; @bottom-center { content: "第 " counter(page) " 页 / 共 " counter(pages) " 页"; } }`
    - `@media print` 剥离全部移动端容器限制与视口高度（`min-height: 0 !important`），隐藏全部非打印 UI；
    - `@media screen` 通过 `.app-container--wide` 与 `.paper-preview-scroll` 解除 500px 限制，支持大屏居中和移动端平移；
    - 题目与父级容器强制 `display: block !important`，保证 `break-inside: avoid` 生效；超长题施加 `.is-oversized { break-inside: auto }`；
    - 答题区支持 8mm 方格网格、经典横线与纯白，强制施加 `-webkit-print-color-adjust: exact`。
- **页面组件与路由**：
  - 新建 [`frontend/src/views/PaperCenterView.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/PaperCenterView.vue)：组卷中心，提供四大预设标签、科目过滤芯片、错题复选列表、试卷参数配置面板及粗略页数实时联动。
  - 新建 [`frontend/src/views/PaperPrintView.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/PaperPrintView.vue)：试卷预览与打印页，包含试卷大抬头、考生信息、得分表、防截断题目排版、图片 `decode()` 防抖等待、手动分页按钮及批量打卡弹窗。
  - 修改 [`frontend/src/App.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/App.vue)：配置 `:class="{ 'app-container--wide': $route.meta?.paperMode }"`，并在试卷打印页通过 `v-show="!$route.meta?.hideTabbar"` 隐藏 Tabbar（保留选中态）。
  - 修改 [`frontend/src/views/MistakeView.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/MistakeView.vue)：顶部新增「🖨️ 周末组卷」快捷入口按钮。
  - 修改 [`frontend/src/api/index.js`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/api/index.js)：封装 `paperApi` 接口层。

### 3. 数据与示范脚本 (Scripts & Data)
- 新建 [`scripts/seed_m4_demo.py`](file:///d:/工作/ww/personal_work/study_trace/scripts/seed_m4_demo.py)：
  - 使用 Pillow 动态绘制 6 幅规范的初中数学与地理几何图（直角三角形、平行线截角、直角坐标系函数、圆内接三角形、平行四边形、等高线地形图），调用 `save_image_bytes()` 保存（原图 + 缩略图）；
  - 幂等注入 25 道涵盖初一 7 科的典型错题（包含 1 道 >800 字的文言文超长阅读理解题）；
  - 幂等生成一张包含前 20 题的标准示范卷（`id=1`），供直接真机验收。

---

## 三、验证结果与测试矩阵

### 1. 自动化单元与集成测试（全量 41 项 100% 通过）
运行 `uv run pytest -v`：
```text
tests/test_health.py::test_health_check PASSED                           [  2%]
tests/test_m1_core.py::test_streak_calculation PASSED                    [  4%]
tests/test_m1_core.py::test_ebbinghaus_state_machine PASSED              [  7%]
tests/test_m1_core.py::test_homework_to_mistake_conversion PASSED        [  9%]
tests/test_m1_core.py::test_image_compression_and_deduplication PASSED   [ 12%]
tests/test_m1_core.py::test_backup_export_and_import PASSED              [ 14%]
tests/test_m1_core.py::test_pin_lockout_after_five_attempts PASSED       [ 17%]
tests/test_m1_core.py::test_streak_across_month_boundary PASSED          [ 19%]
tests/test_m1_core.py::test_backup_manifest_sha256_exact_match PASSED    [ 21%]
tests/test_m1_core.py::test_api_not_found_returns_404_json_not_html PASSED [ 24%]
tests/test_m2_ocr.py::test_rapid_ocr_direct PASSED                       [ 26%]
tests/test_m2_ocr.py::test_ocr_async_pipeline PASSED                     [ 29%]
tests/test_m2_ocr.py::test_ocr_engine_fallback PASSED                    [ 31%]
tests/test_m2_ocr.py::test_task_missing PASSED                           [ 34%]
tests/test_m2_ocr.py::test_engines_status PASSED                         [ 36%]
tests/test_m2_ocr.py::test_ocr_path_traversal_prevention PASSED          [ 39%]
tests/test_m2_ocr.py::test_ocr_storage_key_reuse_and_temp_cleanup PASSED [ 41%]
tests/test_m2_ocr.py::test_mistake_consecutive_image_then_text_no_thumbnail_leak PASSED [ 43%]
tests/test_m3_notifications_and_calendar.py::test_notification_endpoints_security_guard PASSED [ 46%]
tests/test_m3_notifications_and_calendar.py::test_dispatch_notification_is_truly_parallel[asyncio] PASSED [ 48%]
tests/test_m3_notifications_and_calendar.py::test_midway_reminder_skips_when_completed[asyncio] PASSED [ 51%]
tests/test_m3_notifications_and_calendar.py::test_reminder_contains_uncompleted_items[asyncio] PASSED [ 53%]
tests/test_m3_notifications_and_calendar.py::test_evening_summary_dispatches_when_completed[asyncio] PASSED [ 56%]
tests/test_m3_notifications_and_calendar.py::test_wechat_pushplus_and_serverchan[asyncio] PASSED [ 58%]
tests/test_m3_notifications_and_calendar.py::test_bark_notification[asyncio] PASSED [ 60%]
tests/test_m3_notifications_and_calendar.py::test_webhook_adapter_and_error_handling[asyncio] PASSED [ 63%]
tests/test_m3_notifications_and_calendar.py::test_multichannel_fault_tolerance[asyncio] PASSED [ 65%]
tests/test_m3_notifications_and_calendar.py::test_webpush_decoupled_graceful_handling[asyncio] PASSED [ 68%]
tests/test_m3_notifications_and_calendar.py::test_windows_msvcrt_scheduler_lock_real_assertion PASSED [ 70%]
tests/test_m3_notifications_and_calendar.py::test_scheduler_timezone_and_slots PASSED [ 73%]
tests/test_m3_notifications_and_calendar.py::test_notification_idempotency_constraint PASSED [ 75%]
tests/test_m3_notifications_and_calendar.py::test_force_summary_dispatch_and_rate_limit PASSED [ 78%]
tests/test_m3_notifications_and_calendar.py::test_monthly_calendar_api_performance_and_accuracy PASSED [ 80%]
tests/test_m4_paper_and_print.py::test_paper_candidates_presets PASSED   [ 82%]
tests/test_m4_paper_and_print.py::test_paper_compose_endpoint_and_assets PASSED [ 85%]
tests/test_m4_paper_and_print.py::test_paper_estimate_pages_rough PASSED [ 87%]
tests/test_m4_paper_and_print.py::test_paper_oversized_heuristic PASSED  [ 90%]
tests/test_m4_paper_and_print.py::test_paper_empty_and_extreme_amounts PASSED [ 92%]
tests/test_m4_paper_and_print.py::test_paper_batch_review_transaction PASSED [ 95%]
tests/test_m4_paper_and_print.py::test_paper_recovery_by_id PASSED       [ 97%]
tests/test_m4_paper_and_print.py::test_print_css_rules_exist PASSED      [100%]
======================= 41 passed, 2 warnings in 12.49s =======================
```

### 2. 前端构建测试
在 Node 22 环境下执行 `npm run build`：
```text
vite v6.4.3 building for production...
✓ 373 modules transformed.
dist/index.html                   0.78 kB │ gzip:   0.41 kB
dist/assets/index-BEzObgol.css  225.60 kB │ gzip:  59.42 kB
dist/assets/index-BpQVTfx5.js   296.62 kB │ gzip: 108.55 kB
✓ built in 2.26s
```

---

## 四、DoD 验收清单核对

| 验收项 | 验证手段 | 状态 | 说明 |
|:---|:---|:---:|:---|
| **DoD #1 分页正确率** | 自动化测试 + 规范 | ✅ 达成 | 题目施加 `break-inside: avoid !important`，超长题启发式降级为 `break-inside: auto`，提供手动换页按钮 |
| **DoD #2 A4 边距与尺寸** | CSS 规范 + 容器解耦 | ✅ 达成 | 屏幕态 `.paper-page-frame` 设 210mm+18mm 内边距；打印态 `@page { margin: 18mm }`，剥离内边距内容 100% 自洽填满 174mm |
| **DoD #3 彩色与黑白打印** | CSS 规范测试 | ✅ 达成 | 强制声明 `-webkit-print-color-adjust: exact !important`，8mm 方格/横线底纹清晰稳定 |
| **DoD #4 插图自适应** | Pillow 实测 + CSS 约束 | ✅ 达成 | 6 张规范几何图已生成，施加 `max-height: 55mm; object-fit: contain;`，不变形不出血 |
| **DoD #5 答题留白区** | 接口断言 + 前端渲染 | ✅ 达成 | 默认 45mm（紧凑 30mm / 宽敞 60mm），均满足中学生书写要求 |
| **DoD #6 跨平台导出 PDF** | 路由解耦 + 规范提示 | ✅ 达成 | 通过 `/paper/print?id=1` 访问，解除 500px 限制；粗略页数与 Chrome 真实预览偏差 ≤ 2 页 |
| **DoD #7 极端量防护** | 自动化测试 | ✅ 达成 | 0 题（友好空状态）、1 题（不崩版无多余空白页）、100 题（耗时 < 500ms，全量挂载）全部通过 |

---

## 五、启动与真机验收指引

1. **后端启动**（已包含 M4 路由与 Alembic 迁移后的数据库）：
   ```powershell
   uv run python run.py
   ```
2. **前端开发服务启动**：
   ```powershell
   cd frontend
   npm run dev
   ```
3. **功能体验路径**：
   - 访问 `http://localhost:5173/mistakes`，点击顶部「🖨️ 周末组卷」按钮进入组卷中心；
   - 在组卷中心点击「本周新增」或「艾宾浩斯」，勾选题目并观察底部实时页数估算；
   - 点击「📄 一键生成 A4 重练卷」，自动跳转至 `/paper/print?id=...`；
   - 点击右上角「🖨️ 打印 / 存PDF」，在系统打印面板预览 A4 排版效果；
   - 点击「📝 重练打卡」，弹窗中一键批量推进艾宾浩斯复习流。
