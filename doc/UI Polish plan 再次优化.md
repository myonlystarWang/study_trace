# 全局视觉统一度、周历手势、番茄钟并列与无折行优化实施计划 (Polish Pass Phase 3)

根据深度访谈与多端体验反馈，本计划聚焦于彻底解决 8 处视觉统一度与交互细节瑕疵，确保移动端极致顺滑、Web PC 端平滑自适应，并达成全站字体字阶、组件规范的绝对严谨统一。

---

## 一、 优化目标与决策共识

1. **水平横向滑动与 100% 防折行**：
   - 全站所有筛选药丸胶囊（`.st-chip`）与学科栏彻底消除任何文字折行或强制竖排，一律采用 `white-space: nowrap !important; flex-shrink: 0; overflow-x: auto;` 水平平滑滑动。
2. **周历导航双端适配（切周手势 + Web 箭头）**：
   - 顶部横向 7 日药丸周历条：触屏手势左右滑动切换**上周 / 下周**；周内 7 天点击直接单选；
   - Web / PC 端兼容：在周历条左、右两侧增加精致小巧的 `<`（上周）与 `>`（下周）切换按钮，无触屏鼠标点击亦能自如翻周。
3. **专注计时器（番茄钟）与录入新作业并列布局**：
   - 移除 `PomodoroTimer.vue` 中固定在右下角 `bottom: 84px` 的悬浮球；
   - 首页底部常驻栏重构为水平双按钮并列：左侧 75% 宽度为品牌蓝「录入新作业」主按钮，右侧 25% 宽度为精致红/灰边框「专注计时」按钮（计时中显示分秒动态跳动），点击唤起专注面板，彻底消除位置重叠。
4. **学情成绩页面的【录入成绩】入口优雅化**：
   - 顶部导航栏右侧移除生硬的实心厚重按钮，改为标准规范的纯文字链接 `right-text="录入成绩"`；
   - 在页面下方「考试历史台账」区块头部同步放置 `+ 录入新考试` 操作按钮，自然融入业务台账。
5. **错题卡片底部操作区上下分层防挤压**：
   - 错题卡片底部复习操作区改为上下两层清晰结构：
     - 上层：左侧展示紫色徽章「第 X 轮复习」，右侧展示灰色标签「下次：X月X日」；
     - 下层：整齐并排平铺「又忘了」和「掌握啦」双操作按钮，文字 100% 单行不挤压，大拇指热区充足。
6. **全站状态徽章与学科标签风格绝对统一**：
   - 错题本中的「未掌握」「待复习」「已掌握」彻底告别无样式或不协调，升格为与左侧学科标签完全同高度（22px）、同字阶（11px）、同圆角与加粗度的标准微徽章体系（未掌握-红、待复习-橙/紫、已掌握-绿）。
7. **家长管理视图、自检页与 A4 组卷页视觉全局统一**：
   - 消除散乱的灰底边框，统一使用标准白底 `.st-card`、统一页面外边距（12px）；
   - 字体与字阶统一绑定全局令牌（标题 15px/16px 粗体 `#0f172a`，辅助文本 11px/12px `#64748b`）。

---

## 二、 拟修改文件与具体实施方案

### 1. 全局设计令牌统一与公共样式增强
#### [MODIFY] [frontend/src/assets/design-tokens.css](file:///d:/工作/ww/personal_work/study_trace/frontend/src/assets/design-tokens.css)
- 在 `.st-chip` 中强化 `white-space: nowrap !important; flex-shrink: 0;`；
- 在 `.st-subject-tag` 旁增加通用的状态微徽章 `.st-status-tag`（同 `height: 22px; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: var(--st-radius-sm);`），并预置 `--danger`（未掌握）、`--warning`（待复习）、`--success`（已掌握）、`--primary`（进行中）；
- 规范通用水平滚动条容器 `.st-scroll-x`。

---

### 2. 首页作业打卡流：周历切周、防折行与番茄钟并列重构
#### [MODIFY] [frontend/src/views/HomeworkView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/HomeworkView.vue)
- **顶部周历控制区重构**：
  - 包装 `.week-strip-wrapper`：左侧放置 `<`（上周按钮），中间为触屏滑动的 7 日药丸容器，右侧放置 `>`（下周按钮）；
  - 手势算法升级：左右滑动触发 `changeWeek(-1)` 和 `changeWeek(1)`（每次增减 7 天），周内直接点击胶囊切换该天；
- **学科筛选栏**：
  - `.subject-chips-bar` 配置 `white-space: nowrap; overflow-x: auto;`，彻底杜绝文字竖排换行；
- **底部常驻操作栏重构**：
  - `.floating-bottom-bar` 改为 Flex 并列容器：
    - 左侧 flex-grow: `<van-button type="primary" round block icon="plus">录入新作业</van-button>`
    - 右侧 flex-shrink: `<van-button round plain type="danger" icon="underway-o" class="pomodoro-bar-btn" @click="openPomodoro">专注</van-button>`
- **引入 PomodoroTimer 状态通信**：
  - 通过事件或共享状态在底部按钮上实时显示专注中倒计时（如 `24:35`），点击直接唤出专注抽屉。

#### [MODIFY] [frontend/src/components/PomodoroTimer.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/components/PomodoroTimer.vue)
- 移除原本固定在右下角 `bottom: 84px` 的独立浮球 `.floating-pomodoro-ball`，由外层底部常驻栏或显式控制唤起，提供统一的专注面板弹窗。

---

### 3. 错题本：状态徽章协调与卡片底部操作区上下分层
#### [MODIFY] [frontend/src/views/MistakeView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/MistakeView.vue)
- **卡片头部状态标签重塑**：
  - 替换原无样式的 `.hw-status-tag`，升级为标准的 `.st-status-tag`（根据 `mastery_status` 渲染危险红、警告橙、成功绿），视觉尺度与左侧 `.st-subject-tag` 100% 严谨对称；
- **卡片底部艾宾浩斯复习操作区结构重排**：
  - 拆分为清晰的两行：
    - 上行（元数据行）：左侧紫色微徽章 `第 X 轮复习`，右侧灰色标签 `下次: 2026-09-06`；
    - 下行（操作按钮行）：并排平铺 `van-button`「又忘了」与「掌握啦」，设为 `flex: 1` 均分宽度，`white-space: nowrap !important;`，彻底消除任何字号挤压与折行。
- **学科筛选横栏**：
  - 确保 `.chips-row` 包含 `white-space: nowrap; flex-shrink: 0;`。

---

### 4. 学情成绩页面：优雅文字按钮与台账入口强化
#### [MODIFY] [frontend/src/views/ScoreView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/ScoreView.vue)
- **顶栏右侧按钮优化**：
  - 移除 `<van-button>` 模板插槽，改为规范的 `right-text="录入成绩"`，符合移动端 NavigationBar 的轻量规范；
- **台账区块头部强化**：
  - 在「考试历史台账」Section 标题右侧增加小巧圆角 `<van-button size="mini" type="primary" plain round icon="plus">录入成绩</van-button>`；
- **学科胶囊栏与卡片文字规范**：
  - 确保折线图上方的科目切换 Chip 横向滑动不折行，统一字阶变量。

---

### 5. 家长管理视图、自检页与 A4 组卷页视觉全局统一
#### [MODIFY] [frontend/src/views/SettingsView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/SettingsView.vue)
- 移除散乱的自定义浅灰背景（`#f9fafb`, `#f0f0f0` 等），全面统一应用 `.st-card` 与柔和边框；
- 各 Section 标题与 Cell Group 规范内边距与文字颜色；
- 渠道测试输入框与保存按钮对齐全局圆角令牌。

#### [MODIFY] [frontend/src/views/HomeView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/HomeView.vue)
- 自检列表升级为统一卡片结构，标题采用 `.st-section-header`，字阶对齐系统主次变量；
- 状态标签统一尺寸。

#### [MODIFY] [frontend/src/views/PaperCenterView.vue](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/PaperCenterView.vue)
- 4 种预设卡片内边距与字体阶梯对齐系统标准，学科筛选药丸强制单行滑动。

---

## 三、 验证计划

### 1. 自动化测试与构建
- **前端打包**：`npm run build`，确保 0 Error，CSS 打包正常；
- **后端回归**：`uv run pytest tests/`，保证 51 项测试持续 100% 全部通过。

### 2. 多端实机视觉与交互验证（通过 browser_subagent）
- **移动端（375×667）与 PC 宽屏（1036×913）双重验证**：
  1. **首页作业打卡**：验证点击周历两侧 `<` / `>` 切换整周、触屏滑动切换整周；验证底部常驻栏「录入新作业」与「专注计时」并列排布无任何重叠；
  2. **学科胶囊栏**：验证作业页、错题页、组卷页的学科筛选栏水平流畅滑动，文字绝不竖排换行；
  3. **错题本卡片**：验证「未掌握」徽章与左侧学科徽章完全等高一致；验证复习操作区上下分层排布，按钮文字绝不折行；
  4. **学情成绩页**：验证 Navbar 右侧文字链接干净优雅，台账头部录入按钮协调；
  5. **家长设置与关于页**：验证卡片、字体与内边距完全对齐全站设计令牌。
