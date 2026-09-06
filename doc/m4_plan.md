# 里程碑 M4：A4 周末重练卷 实施方案（终审加固版）

## 1. 目标与闭环设计

本里程碑的目标是**一键把错题变成符合专业印刷排版规范的 A4 纸质试卷，并在孩子完成线下做卷后无缝将练习成果回流至错题库，闭环流转艾宾浩斯复习周期**。

### 核心业务闭环
$$\text{错题库（筛选/预设）} \xrightarrow{\text{30秒组卷}} \text{专业 A4 试卷（打印/另存PDF）} \xrightarrow{\text{周末线下纸笔重练}} \text{一键批量打卡} \xrightarrow{\text{推进艾宾浩斯进度（1/3/7/15天/已掌握）}}$$

---

## 2. 审查与评审决策清零（核心防截断、尺寸与架构清零）

### 2.1 🔴 关键排版尺寸与防截断规范（彻底杜绝出血与断裂）
1. **纸张与容器宽度自洽（杜绝右侧出血 36mm，P0-1）**：
   - `@page` 的 `margin: 18mm` 会将物理内容区限制在 $210 - 18 \times 2 = 174\text{mm}$。因此**页边距只能由 `@page` 给一次，绝不能在 DOM 打印流中重复给**。
   - 屏幕预览采用 `.paper-page-frame`（A4 210mm 外框 + 18mm 内边距，内容区精确为 174mm），打印时剥离外框与内边距，内容自适应 100% 填满 174mm 内容区，彻底规避右侧 36mm 出血裁切：
     ```css
     @media screen {
       .paper-page-frame {
         width: 210mm;
         padding: 18mm;
         box-sizing: border-box;
         margin: 0 auto;
         background: #ffffff;
         box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
       }
       .paper-page-sheet {
         width: 100%;
       }
     }
     @media print {
       .paper-page-frame {
         width: 100% !important;
         padding: 0 !important;
         margin: 0 !important;
         box-shadow: none !important;
         background: transparent !important;
       }
       .paper-page-sheet {
         width: 100% !important;
       }
     }
     ```
2. **分页交由浏览器原生 CSS，屏幕不绘制精确参考线（P0-2）**：
   - A4 物理高度为 297mm，扣除上下页边距 $18 \times 2 = 36\text{mm}$ 后，**单页内容有效高度严格为 261mm**。
   - **分页决策 100% 交给浏览器 `break-inside: avoid`**（WebKit/Blink 是最了解真实字体度量的引擎，后端任何 mm 级模拟都会因 iOS 苹方 / Windows 微软雅黑 / CJK 避头尾规则差异产生 1~2 行偏差）。
   - 屏幕模式**不再绘制 `.page-divider-guide` 精确分割线**，仅在组卷中心顶部展示"预计约 N 页"的粗略提示（见 §3.1.3）。
   - 打印预览的真实性由 Chrome 打印对话框自身的分页预览保证 —— 用户点"打印"看到什么就是什么，不需要前端二次模拟。
3. **打印时彻底清除 `min-height: 100vh`（P1-1）**：
   - 覆盖清除 `html, body, #app, .app-container { min-height: 0 !important; height: auto !important; }`，防止单题试卷因视口高度被撑出空白次页。
4. **强制背景图色打印输出**：
   ```css
   .paper-answer-area {
     -webkit-print-color-adjust: exact !important;
     print-color-adjust: exact !important;
   }
   ```
   确保 8mm 方格网格与横线底纹在彩色/黑白打印下 100% 清晰呈现。
5. **页码计数器：单一 `@page @bottom-center`**：
   ```css
   @page {
     size: A4 portrait;
     margin: 18mm;
     @bottom-center {
       content: "第 " counter(page) " 页 / 共 " counter(pages) " 页";
       font-size: 8pt;
       color: #666;
     }
   }
   ```
   - **打印提示**：请**勾选「背景图形」**、**勾选「页眉和页脚」**（Chrome 中取消勾选会连带抑制自定义 `@page` margin box）；页边距保持「默认」；iOS 请确认纸张大小为 A4。
   - ⚠️ **Firefox 降级说明**：Firefox 不支持 `@page` margin box，`@bottom-center` 静默无输出，此时依赖 Firefox 自带页码（用户勾选"页眉和页脚"即可）。属已知降级，不判为缺陷。
   - **不做 DOM `position: fixed` 兜底**：避免与 margin box 在 Chrome/Safari 下重叠打印成黑块。
6. **打印输出必须采用原图，杜绝模糊缩略图**：`compose` 接口明确返回高清原图 URL（`original_image_path`），绝对不取 320px 缩略图，测试硬断言。
7. **打印态彻底隐藏全局与页面 UI（`@media print`）**：
   - 彻底隐藏 `App.vue` 中的全局常驻 `van-tabbar`、页面工具栏、换页虚线按钮、打卡按钮。
   - 打印态解除 `.app-container` 的 `max-width: 500px` 限制，全幅输出 A4（**屏幕态见第 8 条**）。
     ```css
     @media print {
       .no-print, .van-tabbar, .van-tabbar-placeholder, .paper-toolbar, .page-break-btn, .review-action-bar {
         display: none !important;
       }
       .app-container {
         max-width: none !important;
         width: 100% !important;
         margin: 0 !important;
         padding: 0 !important;
         background: transparent !important;
         box-shadow: none !important;
       }
       body, #app {
         background: #ffffff !important;
         margin: 0 !important;
         padding: 0 !important;
       }
     }
     ```
   - 在 `router/index.js` 为 `/paper/print` 配置 `meta: { hideTabbar: true, paperMode: true }`，在 `App.vue` 中绑定 `<van-tabbar v-show="!$route.meta?.hideTabbar" ...>`（**用 `v-show` 而非 `v-if`**，避免 tabbar 卸载导致 `active` 状态丢失，从 `/paper/print` 返回时保持之前选中的 tab）。
8. **屏幕预览态解除 500px 限制与横向平移（P1 — DoD #6 可观测性的前提）**：
   - **问题**：`App.vue` 的 `.app-container { max-width: 500px; margin: 0 auto }` 在**屏幕态**同样生效。A4 外框 `210mm ≈ 794px > 500px`，子元素宽于容器时 `margin: 0 auto` 会退化为左对齐 → 预览页贴左、右侧溢出、整页出现横向滚动条，**DoD #6「页数与预览一致」失去观测手段**。第 7 条的 print 覆盖管不到屏幕态，必须单独处理。
   - **改法（路由 meta + 动态 class，不污染其他页面）**：
     ```js
     // router/index.js
     { path: '/paper/print', name: 'PaperPrint', component: PaperPrintView,
       meta: { hideTabbar: true, paperMode: true } }
     ```
     ```html
     <!-- App.vue -->
     <div class="app-container" :class="{ 'app-container--wide': $route.meta?.paperMode }">
     ```
     ```css
     @media screen {
       .app-container--wide { max-width: none !important; }
       .paper-preview-scroll {
         overflow-x: auto;
         -webkit-overflow-scrolling: touch;
       }
     }
     ```
   - `.paper-preview-scroll` 包裹 `.paper-page-frame`：手机上可横向平移查看完整 A4 幅面；桌面端 794px 通常不触发滚动。
   - 备选纯 CSS 方案：`.app-container:has(.paper-page-frame) { max-width: none !important; }`（需 Chrome 105+ / Safari 15.4+）——**仅作兜底**，不作为唯一手段。
9. **题目容器与其所有父级强制 `display: block !important`**：
   - 覆盖 Vant 等默认 flex/grid，保障 Blink/WebKit 下子元素 `break-inside: avoid` 绝对生效：
     ```css
     .paper-body, .paper-question-list, .van-cell-group, .paper-page-sheet, .paper-page-frame {
       display: block !important;
     }
     .paper-question-item {
       display: block !important;
       break-inside: avoid !important;
       page-break-inside: avoid !important;
       margin-bottom: 24px;
     }
     ```

---

### 2.2 🟠 架构落地与边界保障
1. **单一长容器自洽路线**：全部题目渲染在单一 `.paper-page-sheet` 内，分页交由浏览器原生 `@page` 与 `break-inside: avoid`。
2. **图片异步解码等待与高度跳动防抖（P1-2）**：
   - 插图容器提供固定最大高度占位（`max-height: 55mm`）。
   - 打印调用前通过 `Promise.all(Array.from(document.images).map(img => (img.complete && img.naturalWidth > 0) ? Promise.resolve() : img.decode().catch(() => {})))` 确保全部图片解码完毕，坏图容错跳过，高度稳定后再弹出打印窗口（避免浏览器分页时图片尚未 decode 导致页数抖动）。
3. **超长题目兜底（P2-2，交给浏览器 + UI 提示）**：
   - 留白档位 `space_mm` 上限 80mm、下限 20mm，用户可切换。
   - **单题极端高度 > 261mm 时**（例：语文长阅读 + 图 + 宽敞留白），后端**不预测**具体降级，只做**极简启发式判断**：若 `题干字符数 > 800` 或 `用户选了 60mm 宽敞留白且题干 > 400 字`，在 compose 回包的 `warnings` 中提示"第 X 题内容较长，可能跨页显示"，并标记 `is_oversized: true`。
   - 实际分页行为完全由浏览器 CSS 决定：
     ```css
     .paper-question-item {
       break-inside: avoid;  /* 默认尝试整题不切 */
     }
     .paper-question-item.is-oversized {
       break-inside: auto;   /* 后端 warnings 命中时前端加此 class，允许自然跨页 */
     }
     ```
   - **关键经验**：单题比一整页还长时如果保留 `break-inside: avoid`，浏览器会硬撑截断或死循环；显式降级为 `auto` 让其自然跨页是最稳的解法。
4. **试卷刷新防白屏 + 持久化与跨端直连（P1-C）**：
   - **主存储：后端 `papers` 表**（新增）：`id / title / subtitle / mistake_ids JSON / sort_by / space_level / style_mode / show_error_type / estimated_pages / warnings JSON / student_name / created_at / status(draft|printed|reviewed)`。`POST /api/paper/compose` 落表返回 `paper_id`，用户调起打印回写 `status=printed`，重练打卡完成更新 `status=reviewed`。
   - **页面路由直连**：生成试卷后前端跳转至 `/paper/print?id=${paper_id}`，优先通过 `route.query.id` 请求 `GET /api/paper/{id}` 渲染试卷，辅以 `sessionStorage` 本地容错。天然支持 F5 刷新、多标签另开、以及将链接复制到电脑桌面端直接打印。
5. **随机乱序在后端完成且结果固定（P1-E）**：`sort_by='random'` 由后端一次性打乱并写入 `papers.mistake_ids`，前端纯展示，杜绝预览和打印二次重排漂移。
6. **seed 脚本复用 `save_image_bytes()`（P1-F）**：动态生成 Pillow 图片后，通过 `image_handler.save_image_bytes`（M2 已有工具，M4 直接复用，不新增）保存，自动计算 sha256 并生成缩略图（320px）和原图（1600px），杜绝列表页 404。
7. **全学科动态扩展与综合兜底架构**：
   - **DB-Driven 零硬编码**：系统所有科目完全以 `subjects` 表为单一真理来源（已具备设置接口）。当前预置初一核心 7 科（精准使用「道德与法治」，杜绝「政治」或初一预设「物理」）。
   - **双轨候选与综合大题**：候选题目接口默认过滤核心 7 科，通过 `include_all_subjects=True` 支持美术/信息科技等错题入卷。试卷排版按科目（`sort_by="subject"`）时，核心 7 科按 `Subject.sort_order` 顺序排前，非核心 7 科错题统一在末尾归入“综合”大题，杜绝数据孤岛与大题碎片化。
8. **双入口定位规范（P2-3）**：在错题本顶部放置「🖨️ 周末组卷」作为学生/家长通用的复习工具入口，同时在设置页（家长空间）保留对应组卷入口，兼顾孩子自主性与家长把控。
9. **preset 重叠去重（P1-G）**：`ebbinghaus`（`next_review_date <= today` 且未掌握）与 `unmastered`（`review_count >= 2` 且未掌握）可能命中同一题。**后端行为**：每个 preset 独立返回候选列表，前端组卷中心在"已选题目"集合层面自动去重（同一 `mistake_id` 只算一次），UI 显示"其中 X 题同时命中艾宾浩斯与高频标签"，让用户知情但不重复计数。
10. **`original_image_path` URL 契约（P1-H）**：后端返回**完整可访问 URL**（例如 `http://<host>/uploads/images/<sha256>.jpg` 或相对路径 `/uploads/images/<sha256>.jpg`），前端 `<img :src="q.original_image_path">` 直接绑定，无需拼接。测试需 HTTP GET 断言 200 且 `Content-Type: image/*`。

---

## 3. 详细设计与功能拆解

### 3.1 组卷中心 (`PaperCenterView.vue`)

路径：`/paper`

1. **四大预设快捷标签（一键组卷）**：
   - 🌟 **本周新增错题**：自动匹配本周一 00:00:00 至今录入的错题（上海时区）。
   - 🧠 **艾宾浩斯临界题**：`next_review_date <= today` 且未掌握。
   - ⚠️ **高频未掌握**：`review_count >= 2` 且未掌握的顽固题（与 0 次新题彻底解耦）。
   - 📚 **全库自选**：科目筛选、错因分类、关键词搜索。
2. **试卷配置面板**：
   - 试卷主标题（默认："初一错题周末重练卷"）。
   - 副标题（"满分: 100分 · 建议用时: 45分钟"）。
   - 题目排序方式（按科目分大题 / 连续统一编号 / 随机乱序【后端固定】）。
   - 留白高度切换（默认标准 45mm ≥ 40mm / 紧凑 30mm / 宽敞 60mm）。
   - 留白底纹切换（8mm 方格网格 / 经典横线 / 纯白无底纹）。
   - 错因提示开关（默认隐藏还原考场环境，可切换开启）。
3. **容量粗略估算与上限提示（P2-4）**：
   - **算法（极简，仅供家长心理预期）**：`estimated_pages = max(1, round(total_questions / 4))`（假设平均 4 题一页，含图题目权重稍高：`+ ceil(图片题数 / 6)`）。
   - **不做 mm 级精确计算**：字体度量、CJK 换行、图片缩放全由浏览器实时决定，后端任何模拟都会因 iOS 苹方 / Windows 微软雅黑 / Android 思源黑体差异产生 ±1~2 页偏差，"精确但错"比"粗略但诚实"更糟。
   - 超过 30 题时提示："已选 35 题（预计约 9 页），建议分批打印"。
   - **实际打印页数以 Chrome 打印对话框预览为准**，用户在打印前一定能看到真实分页，不需要前端二次模拟。
   - DoD #6 的验收口径改为"打印预览无跨页截断 + 用户能手动数清页数"，不再要求后端估算与真实页数硬对齐。

---

### 3.2 打印排版视图 (`PaperPrintView.vue` + `print.css`)

路径：`/paper/print`

1. **A4 物理排版与抬头**：
   - 主标题、考生姓名（后端自动注入）、班级、学号、日期、得分统计表格。
   - 考生须知 3 条。
2. **防截断题目排版**：
   - 单题容器 `.paper-question-item` 与所有父级容器均显式 `display: block !important`。
   - 题目插图自适应（`max-height: 55mm; object-fit: contain;`）。
   - 答题留白（默认标准 45mm ≥ 40mm，下限 20mm，上限 80mm，施加 `-webkit-print-color-adjust: exact`）。
3. **手动分页控制**：
   - 每题上方提供「✂️ 在此处换页」按钮，点击附加 `.manual-page-break { break-before: page }`，纯前端交互，不重新调 compose。
   - **不再绘制屏幕分页参考线**（见 §2.1.2），真实分页由 Chrome 打印对话框预览。
4. **重练打卡闭环弹窗（批量事务，非 N 次单请求）**：
   - 顶部工具栏提供「📝 重练打卡」按钮。
   - 弹窗展示本卷所有题目，每道题提供【掌握 / 遗忘】快捷开关，全部标注后**一次性调用** `POST /api/paper/{paper_id}/batch_review`，body 传 `[{mistake_id, result}]`（`result: "remembered" | "forgotten"` 对齐既有复习模型），后端**单事务**推进所有艾宾浩斯轮次，避免 100 题 = 100 次 HTTP 请求导致的掉包与幂等风险。
   - 部分失败处理：后端返回 `{success: [...], failed: [{mistake_id, reason}]}`，前端弹窗标红失败项并允许重试。
5. **极端量防护**：
   - 0 题：友好空状态引导并禁用打印。
   - 1 题：居中规整，不崩版，清除 min-height 杜绝多印空白页。
   - 100 题：全量挂载渲染，流畅分页。

---

### 3.3 后端 API 支撑 (`backend/app/routers/paper.py`)

1. `GET /api/paper/candidates`:
   - 参数：`preset` (`this_week` / `ebbinghaus` / `unmastered` / `all`)、`subject_id` (可选，不传查全科)、`error_type`、`include_all_subjects` (bool，默认 False 仅查初一核心 7 科；设为 True 时包含所有科目)、`limit`。
   - 查询并返回候选错题列表与统计。多 preset 命中同一题时不去重（前端在"已选集合"层面去重，见 §2.2.9）。
2. `POST /api/paper/compose`:
   - 参数：`mistake_ids: List[int]`、`title`、`subtitle`、`sort_by`、`space_level`、`style_mode`、`show_error_type`。
   - 排序策略：`sort_by="subject"` 时核心 7 科按 `sort_order` 优先成卷，非核心科目（如艺术、信息科技）自动归入"综合"大题；`sort_by="order"` 保持输入顺序；`sort_by="random"` 随机打乱。
   - **落 `papers` 表**（见 §2.2.4），返回结构化试卷模型：
     - `paper_id`: 数据库主键，用于后续恢复与批量打卡
     - `student_name`: 当前学生姓名（从 `students` 表读取 `id=1` 的 `name`，若无则回退到 `"初一同学"`）
     - `questions`: 顺序排好的一组试卷题目（题号、科目标签、题干文本、**完整可访问 URL** `original_image_path`、留白高度 `space_mm` 默认 45mm、`is_oversized: bool`）
     - `total_questions`, `estimated_pages`（粗略估算，见 §3.1.3）
     - `warnings: List[str]`（超长题目启发式警告，含字数与插图综合判定，见 §2.2.3）
3. `GET /api/paper/history`:
   - **路由守卫**：必须严格注册在 `GET /{paper_id}` 之前，防止 FastAPI 路由匹配时将 `"history"` 误当成整数 `paper_id` 抛出 422 `int_parsing` 错误。
   - 参数：`limit`、`status`（`draft` / `printed` / `reviewed`）。返回历史试卷列表，供家长空间查看"最近组卷记录"。
4. `GET /api/paper/{paper_id}`:
   - 从数据库恢复试卷快照，供 F5 刷新与跨设备访问使用。若不存在返回 404。
5. `POST /api/paper/{paper_id}/mark_printed`:
   - 试卷状态流转：用户在预览页调起系统打印后回写为 `printed`（状态机：`draft` → `printed` → `reviewed`，已打卡试卷重印不逆转状态）。
6. `POST /api/paper/{paper_id}/batch_review`:
   - 参数：`reviews: List[{mistake_id, result: "remembered"|"forgotten"}]`。
   - **单事务**推进所有艾宾浩斯轮次，更新 `papers.status = reviewed`，返回 `{success: [...], failed: [{mistake_id, reason}]}`。
   - 前端弹窗交互防误触：默认单题选择均为 `null`，必须全部手动做出显式标记后确认按钮才可点击，防止不可逆污染艾宾浩斯复习周期。

---

## 4. Proposed Changes

### [Backend] API & Schemas

#### [NEW] [paper.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/routers/paper.py)
- 提供候选题目拉取接口 `GET /api/paper/candidates`。
- 提供试卷组装规范接口 `POST /api/paper/compose`（落 `papers` 表，粗略估算页数，启发式标记 `is_oversized`）。
- 提供试卷恢复接口 `GET /api/paper/{paper_id}` 与历史列表 `GET /api/paper/history`。
- 提供批量重练打卡接口 `POST /api/paper/{paper_id}/batch_review`（单事务推进艾宾浩斯）。

#### [MODIFY] [models.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/models.py)
- 新增 `Paper` 模型：`id / title / subtitle / mistake_ids JSON / sort_by / space_level / style_mode / show_error_type / estimated_pages / warnings JSON / student_name / status / created_at`。

#### [NEW] [alembic migration](file:///d:/工作/ww/personal_work/study_trace/backend/alembic/versions/)
- 新增 `papers` 表迁移脚本，含 `status` 索引与 `created_at` 索引。

#### [MODIFY] [schemas.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/schemas.py)
- 新增 `PaperCandidateOut`、`PaperComposeIn`、`PaperQuestionOut`、`PaperComposeOut`、`PaperBatchReviewIn`、`PaperBatchReviewOut`、`PaperHistoryOut` 数据契约。

#### [MODIFY] [main.py](file:///d:/工作/ww/personal_work/study_trace/backend/app/main.py)
- 挂载 `paper.router`。

---

### [Frontend] Views, Styles & Navigation

#### [NEW] [print.css](file:///d:/工作/ww/personal_work/study_trace/frontend/src/assets/print.css)
- 建立 `frontend/src/assets/print.css`。
- 标准 A4 打印样式：`@page` 边距 18mm + `@bottom-center` 页码计数器（含 **Firefox 不支持 margin box 的降级注释**）、`break-inside: avoid` + `.is-oversized { break-inside: auto }`、`-webkit-print-color-adjust: exact`、父容器 `display: block !important`。
- `@media print`：彻底隐藏 tabbar 与工具栏、清除 `min-height: 100vh`、解除 500px 宽度限制（§2.1.7）。
- `@media screen`：**解除屏幕态 500px 限制**（`.app-container--wide { max-width: none !important }`）与 A4 横向平移容器 `.paper-preview-scroll { overflow-x: auto }`（§2.1.8）——缺此项则预览被挤在 500px 内。
- **不做**：DOM `position: fixed` 页脚兜底（会与 margin box 重叠）、屏幕分页参考线（跨字体渲染不可靠）。

#### [MODIFY] [main.js](file:///d:/工作/ww/personal_work/study_trace/frontend/src/main.js)
- 全局引入 `import './assets/print.css'`。

#### [NEW] [PaperCenterView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/PaperCenterView.vue)
- 组卷中心页面，集成预设标签、错题勾选、试卷参数设置与**粗略页数提示**（不再显示精确参考线）。

#### [NEW] [PaperPrintView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/PaperPrintView.vue)
- 打印预览页面，采用 `.paper-page-frame` 屏幕外框与 `.paper-page-sheet` 内容架构、防截断属性、手动分页按钮、重练打卡弹窗；对 `is_oversized=true` 的题目加 `.is-oversized` class 允许自然跨页。

#### [MODIFY] [App.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/App.vue)
- `<van-tabbar v-show="!$route.meta?.hideTabbar" ...>`（隐藏 tabbar，用 `v-show` 保留 active 状态）。
- 根容器绑定宽度模式：`<div class="app-container" :class="{ 'app-container--wide': $route.meta?.paperMode }">`（屏幕态解除 500px，见 §2.1.8）。

#### [MODIFY] [index.js (router)](file:///d:/工作/ww/personal_work/study_trace/frontend/src/router/index.js)
- 注册 `/paper`（组卷中心，保持 500px 常规宽度）与 `/paper/print`（`meta: { hideTabbar: true, paperMode: true }`）。

#### [MODIFY] [index.js (api)](file:///d:/工作/ww/personal_work/study_trace/frontend/src/api/index.js)
- 封装 `paperApi.getCandidates()`、`paperApi.composePaper()`、`paperApi.getPaper(id)`、`paperApi.batchReview(id, reviews)`、`paperApi.getHistory()`。

#### [MODIFY] [MistakeView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/MistakeView.vue)
- 顶部增加「🖨️ 周末组卷」按钮，列表支持多选并一键生成重练卷。

---

### [Scripts & Data] Demo Seed Script

#### [NEW] [seed_m4_demo.py](file:///d:/工作/ww/personal_work/study_trace/scripts/seed_m4_demo.py)
- 使用 Pillow 动态绘制 6 幅规范的初中数学与地理几何/函数图，通过 `save_image_bytes()` 保存（自动计算 sha256 并生成缩略图与原图）。
- **幂等注入 25 道**初一真实科目（语数英+史地生+道德与法治）典型错题到数据库；**其中至少 20 道满足组卷候选条件**（未掌握或本周新增），**且恰好 6 道带几何图**，直接对齐 DoD #1「组 20 道题（含 6 道几何带图题）」的验收口径。
- 额外注入 1 道**超长语文阅读理解题**（题干 > 800 字），用于验证 `is_oversized` 启发式判断与自然跨页 CSS。
- 脚本额外执行一次 `POST /api/paper/compose`（选取前 20 道）落一张 demo 试卷到 `papers` 表，供人工真机验收直接消费 `paper_id`。

---

### [Tests] Automated Regression Suite

**测试策略**：遵循 M3 确立的"**自动化验逻辑契约，真机手动验视觉排版**"原则。**不引入 Playwright / pdfplumber 等重型 E2E 依赖**（Chromium 内核下载 300MB+、Windows 网络易卡、维护成本远超业务价值）；分页与截断的真机验证由 Chrome 打印预览 10 秒完成。

#### [NEW] [test_m4_paper_and_print.py](file:///d:/工作/ww/personal_work/study_trace/tests/test_m4_paper_and_print.py)
- `test_paper_candidates_presets`: 验证本周新增、艾宾浩斯临界、高频未掌握的快捷过滤（上海时区、未掌握>=2次）；额外断言 `ebbinghaus ∩ unmastered` 存在交集时后端不去重、返回各自完整列表。
- `test_paper_compose_endpoint_and_assets`: 验证组装接口生成顺序编号、**`original_image_path` 是完整 URL 且 HTTP GET 返回 200 + `Content-Type: image/*`**、留白高度（默认 45mm ≥ 40mm）、学生姓名自动注入、`papers` 表落库、返回 `paper_id` / `estimated_pages`。
- `test_paper_estimate_pages_rough`: 验证粗略估算公式 `max(1, round(total/4) + ceil(image_count/6))`：20 题 6 图 → 6 页；0 题 → 1 页；100 题 → 25 页。**只测公式，不测与真实打印是否吻合**（那是浏览器的事）。
- `test_paper_oversized_heuristic`: 构造题干 > 800 字 / 60mm 宽敞留白+题干>400 字场景，断言后端在 `warnings` 中标记且对应题目 `is_oversized=true`。
- `test_paper_empty_and_extreme_amounts`: 验证 0 题、1 题、100 题极限数据下的接口稳定性和响应速度（<500ms）。
- `test_paper_batch_review_transaction`: 20 题批量打卡，其中 3 题 `mistake_id` 不存在，断言 (a) 事务不因部分失败整体回滚；(b) 成功 17 题的 `next_review_date` / `review_count` / `mastery_status` 已按艾宾浩斯规则推进；(c) 失败 3 题在 `failed` 列表中返回；(d) `papers.status` 更新为 `reviewed`。
- `test_paper_recovery_by_id`: compose 后重新 `GET /api/paper/{id}`，断言返回数据与原 compose 完全一致（`mistake_ids` 顺序、`student_name`、`estimated_pages`）。
- `test_print_css_rules_exist`: 文本断言 `print.css` 中包含 (a) `@page @bottom-center` 规则；(b) `break-inside: avoid`；(c) `.is-oversized { break-inside: auto }`；(d) `-webkit-print-color-adjust: exact`；(e) 父级 `display: block`；(f) 对 tabbar、工具栏的隐藏与 min-height 清除。**任一缺失即失败**。（纯字符串检查，无需浏览器）

---

## 5. 验收标准（DoD 7 项全量实测矩阵）

- [ ] **DoD #1 分页正确率（真机手动）**：组 20 道题（含 6 道几何带图题）→ 打印预览中**无一道题被跨页截断**（实测验证 `break-inside: avoid` 与手动分页）
- [ ] **DoD #2 A4 边距与尺寸（真机手动）**：A4 边距 18mm，内容不出血（通过 frame/sheet 双层宽度解耦隔离）；物理尺寸严格为 210×297mm
- [ ] **DoD #3 彩色与黑白打印（真机手动）**：彩色与黑白打印均清晰，包含答题区 8mm 网格底纹（`-webkit-print-color-adjust: exact`）
- [ ] **DoD #4 插图自适应（真机手动）**：横图/竖图/几何图均自适应居中，不变形、不溢出边界（`max-height: 55mm`，`object-fit: contain`）
- [ ] **DoD #5 答题留白区（自动化接口 + 真机手动）**：每道题后默认留白 45mm ≥ 40mm（允许可选紧凑 30mm，下限 20mm），适合中学生黑色水笔书写解答
- [ ] **DoD #6 跨平台导出 PDF（真机手动）**：桌面 Chrome 另存为 PDF 与 iOS Safari 打印双指缩放导出 PDF（提示手动确认 A4 纸型），**打印预览无题目跨页截断、内容不出血、页码正常显示**。组卷中心的粗略页数估算与真实页数偏差 ≤ 2 页属正常（字体度量差异，见 §3.1.3）。
- [ ] **DoD #7 极端量防护（自动化接口 + 性能验证）**：空试卷（0 题）、单题（1 题，无多余空白页）、大批量（100 题）三种极端量下不崩版，DOM 分页清晰流畅（接口 <500ms）
