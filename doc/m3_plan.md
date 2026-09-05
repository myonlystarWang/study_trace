# 里程碑 M3：提醒推送 + 番茄钟 + 月历打卡 实施方案（工程避坑与微信服务号升级版）

## 1. 核心改进与设计决策

根据最新实测审查与严格评审，本实施方案针对潜在工程阻塞点完成深度加固与风险清零：

### 1.1 新增微信服务号中转通道（最高优先级）
- **核心价值**：家庭日常主要看个人微信，无需安装额外 App（如 Bark、企微、钉钉），微信扫码关注服务号即可绑定，支持父母多成员建群推送，作业提醒直达微信会话卡片。
- **首选服务**：**PushPlus（推送加）**
  - **实名认证前置**：必须在微信公众号内完成手机实名认证，实名后方可享受 **200 条/天永久免费额度**（未实名接口返回 905 错误且可用额度为 0）。
  - **内容防静默丢弃机制**：PushPlus 官方对“相同内容 1 小时限 3 条”且会静默丢弃。在 `notifier.py` 生成推送内容时，**末尾统一附带微秒时间戳与唯一防重序号**（如 `\n\n> 🔖 记录 ID: 20260906-201001-a1b2`），彻底规避静默丢弃陷阱。
- **备选服务**：**Server酱（Turbo版）**，免费用户每日限 5 条，降为备用通道。
- **渠道优先级确立**：
  $$\text{PushPlus（微信首选，实名免费 200 条/天）} > \text{Server酱（备选，免费 5 条/天）} > \text{PWA Web Push（待 M6）} > \text{iOS Bark} > \text{钉钉 / 飞书 / 企微群机器人}$$

### 1.2 验收解耦（杜绝被未上线依赖阻断）
- **痛点**：iOS Web Push 依赖公网 HTTPS + Cloudflare 域名（M6 范围）+ `pywebpush`/`cryptography` 签名库 + `vite-plugin-pwa`，在 M3 本地局域网内无法端到端真机验证。
- **解耦决策**：
  - **M3 主验渠道**：微信服务号（PushPlus/Server酱）、iOS Bark、群机器人。三者**均无需公网 HTTPS**，局域网即可 100% 闭环真机验收。
  - **Web Push 状态**：保留数据表模型与接口壳，优雅捕获缺少依赖，真机验收明确标注为**「待 M6 HTTPS 后验证」**，坚决不阻塞 M3 交付。

### 1.3 消除 5 项工程隐患（P0 彻底闭环）
1. **SQLite 唯一约束迁移必须使用 `batch_alter_table` (P0-1)**：
   - SQLite 无法直接对已有表 `ALTER TABLE ADD CONSTRAINT`，原生调用 `op.create_unique_constraint()` 会抛出 `NotImplementedError` 导致迁移崩溃。
   - Alembic 迁移脚本必须严格手写：`with op.batch_alter_table("notification_logs") as batch_op: batch_op.create_unique_constraint(...)`，通过 SQLite 复制重建表机制安全落地。
2. **`httpx` 正式移入生产运行时依赖 (P0-2)**：
   - `httpx>=0.28.1` 已从 `[dependency-groups].dev` 移至 `[project].dependencies`，并完成 `uv sync`，确保在 `uv sync --no-dev` 生产部署环境下绝对不会发生 `ImportError`。
3. **TestClient 不触发 lifespan 避坑**：
   - `seed_database()` **严格保留在模块顶层**，绝不移入 lifespan，确保现有 18 个基础测试及新测试不受任何影响。
   - 测试定时业务逻辑时，直接调用核心处理函数 `check_and_dispatch_homework_reminders(slot, force_summary)`，杜绝在测试中等待后台定时触发的不可测行为。
4. **Windows 原生文件锁 API 规范**：
   - 严禁使用 Linux `fcntl`，严禁使用不存在的 `msvcrt.unlocking`。
   - 加锁：`msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)`（第二进程捕获 `OSError` 拦截双调度）。
   - 解锁：`msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)`。
5. **时间戳严格对齐 `Asia/Shanghai` 时区**：
   - `NotificationLog.sent_at` 使用 `lambda: datetime.now(ZoneInfo("Asia/Shanghai"))`，与全局上海时区严格统一，杜绝服务器为 UTC 时产生 8 小时偏差。

### 1.4 小项规范与体验优化
- **API 正则语法**：日历聚合接口参数使用 `Query(..., pattern=r"^\d{4}-\d{2}$")`，消除 FastAPI 0.115+ 废弃警告。
- **日历状态完整四色映射**：`green` (100% 完成)、`yellow` (部分完成)、`red` (0% 完成)、`gray` (无作业)，与 `development_plan.md` 保持完全一致。
- **iOS 音频兜底**：Safari 锁屏挂起 Web Audio 时，番茄钟完成由 Bark/微信推送在系统级振动提醒，DoD 标注尽力而为。
- **备份凭据警示**：设置页导出备份时醒目标注：“备份文件包含本地数据库与通知凭据，请妥善保管，切勿公开发布”。
- **即时发送汇总**：新增 `POST /api/notifications/send-summary-now` 接口，支持家长随时一键触发今日全貌日报快照。

---

## 2. 模块设计与代码组织

### 2.1 后端模块架构

```
backend/app/
├── models.py                  # [MODIFY] NotificationLog 补充 UniqueConstraint 与 Shanghai 时区 sent_at
├── scheduler.py               # [NEW] APScheduler 初始化、Windows msvcrt 锁、分时分级调度逻辑
├── utils/
│   └── notifier.py            # [NEW] PushPlus/Server酱、Bark、群机器人分发器与带防重序号的 Markdown 模板
├── routers/
│   ├── homework.py            # [MODIFY] 增加 GET /api/homework/calendar 接口 (pattern=..., 含 gray 映射)
│   ├── notifications.py       # [NEW] 渠道配置、单通道测试、立即发送汇总 (force_summary)
│   └── settings.py            # [MODIFY] 支持通知时段与渠道 Key 持久化
├── schemas.py                 # [MODIFY] 补充 Notification 相关与 Calendar 输出契约
└── main.py                    # [MODIFY] 挂载 notifications 路由，lifespan 安全启停调度器
```

#### A. 数据库迁移 (Alembic)
- 新建迁移文件，向 `notification_logs` 表应用复合唯一约束 `uq_notification_date_slot_channel`。
- 迁移脚本采用 `with op.batch_alter_table("notification_logs") as batch_op:` 安全构建。
- 执行 `alembic upgrade head`，杜绝任何 `create_all` 捷径。

#### B. 多渠道分发器 `backend/app/utils/notifier.py`
- 统一分发接口：`async def send_notification(title: str, content: str, channels: list[str] = None) -> dict[str, dict]`
- 渠道适配器：
  1. **PushPlus (`pushplus`)**：POST `https://www.pushplus.plus/send`
     ```json
     {"token": "...", "title": title, "content": content, "template": "markdown"}
     ```
     正文末尾注入防重序列号，防止静默丢弃。
  2. **Server酱 (`serverchan`)**：POST `https://sctapi.ftqq.com/{KEY}.send`
     ```json
     {"title": title, "desp": content}
     ```
  3. **iOS Bark (`bark`)**：GET/POST `https://api.day.app/{key}/{title}/{body}?group=学迹`
  4. **群机器人 (`webhook`)**：智能识别企微（`markdown.content`）、钉钉（`markdown.text`）、飞书（`content.post`）。
  5. **Web Push (`webpush`)**：通道代码预留，缺库或无 HTTPS 时返回友好指引，待 M6 激活。
- **容错隔离**：每个渠道使用 `httpx.AsyncClient(timeout=5.0)` 独立请求与异常捕获，单渠道超时报错不阻塞其他渠道。

#### C. 定时巡检与分级晚报 `backend/app/scheduler.py`
- 调度引擎：`AsyncIOScheduler(timezone="Asia/Shanghai")`。
- 时段配置：默认中途催办 `20:10` 与 `21:10`，晚间总结日报 `21:50`。
- Windows 文件锁：使用 `data/temp/scheduler.lock` 与 `msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)` 防止 `--reload` 重复拉起。
- 核心调度业务：`async def check_and_dispatch_homework_reminders(slot: str, force_summary: bool = False, db: Session = None)`
  - 统计当日作业：`total`, `completed`, `uncompleted_items` 及艾宾浩斯复习情况。
  - **中途催办时段 (20:10 / 21:10)**：若作业全部完成且非 `force_summary`，记录免打扰跳过日志，不调用推送。
  - **晚间总结时段 (21:50) 或 `force_summary`**：
    - 若全部完成：推送「🎉 今日作业满卡完成！」晚报，带连续打卡天数与表扬语。
    - 若有未完成：推送带有具体学科待办清单的终盘提醒。
  - 发送成功后落盘 `NotificationLog`，防重生效。

#### D. 月度作业打卡日历接口 `routers/homework.py`
```python
@router.get("/calendar", response_model=MonthlyCalendarOut)
def get_monthly_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), # 如 "2026-09"
    student_id: int = 1,
    db: Session = Depends(get_db)
):
    # SQL 聚合当月每日 total 与 completed
    # 状态映射: green(100%), yellow(部分), red(0%), gray(无作业)
```

---

## 2.2 前端交互设计

```
frontend/src/
├── components/
│   ├── CalendarModal.vue      # [NEW] 月度作业打卡红黄绿灰小圆点日历浮窗
│   └── PomodoroTimer.vue      # [NEW] 25分钟专注番茄钟（基于绝对时间戳后台不漂移）
├── views/
│   ├── HomeworkView.vue       # [MODIFY] 顶部集成日历入口 📅、番茄钟浮窗
│   └── SettingsView.vue       # [MODIFY] PushPlus/Server酱/Bark/机器人配置、立即发送汇总按钮
└── api/
    └── index.js              # [MODIFY] 补充 notificationApi 与 calendarApi
```

1. **`SettingsView.vue` 通知设置面板**：
   - 渠道开关列表（默认推荐勾选 PushPlus 微信推送）。
   - 提示认证：*“PushPlus 微信推送需先在公众号完成实名认证，每日享 200 条免费额度；未实名不可用。”*
   - PushPlus Token、Server酱 SendKey、Bark Key、群机器人 Webhook URL 输入框。
   - 每个通道独立「测试」按钮，带即时反馈弹窗与错误详情。
   - **「立即生成并发送今日汇总」** 按钮：随时手动触发一次全渠道推送。
   - 安全提示红框：*“提示：数据备份包包含本地数据库与通知凭据，请妥善保管勿外传。”*
2. **`CalendarModal.vue`**：
   - 月份切换器（`2026-09`）。
   - 7 列日历网格，每个日期格子展示数字，并在下方标注对应打卡状态圆点（🟢满卡 / 🟡部分完成 / 🔴零完成 / ⚪无作业灰色）。
   - 点击任意日期直接关闭弹窗并切换主页作业列表。
3. **`PomodoroTimer.vue`**：
   - 25 分钟倒计时，基于 `targetEndTime = Date.now() + remaining` 时间戳校准，防止移动端切后台定时器挂起漂移。
   - 结束播放提示音，配合弹窗与系统推送兜底。

---

## 3. 测试与完整 15 条 DoD 映射矩阵

对照 `development_plan.md`，精确分解为 13 条自动化测试与 2 条真机手动项：

| # | DoD 条目 | 验证方式 | 对应测试函数 / 动作 | 验证逻辑与断言 |
|---|:---|:---:|:---|:---|
| 0 | **家长门禁安全守卫** | 自动化 | `test_notification_endpoints_security_guard` | 未带 X-Parent-PIN 请求头时一律返回 401 拦截，防止凭据泄露与随意触发 |
| 1 | **真正并发分发验证** | 自动化 | `test_dispatch_notification_is_truly_parallel` | 验证多渠道使用 asyncio.gather 真正并发触发，双渠道耗时 < 0.25s (DoD #7) |
| 2 | **时区与时段配置** | 自动化 | `test_scheduler_timezone_and_slots` | 断言调度器 Cron 触发器显式绑定 `Asia/Shanghai`，时段严格包含 20:10, 21:10, 21:50 |
| 3 | **数据库级幂等约束** | 自动化 | `test_notification_idempotency_constraint` | 验证同一 `(date, slot, channel)` 重复插入时触发 SQLite 唯一约束违规，应用层拦截 |
| 4 | **中途满卡免打扰跳过** | 自动化 | `test_midway_reminder_skips_when_completed` | 当日作业全部打勾时，20:10 / 21:10 触发直接跳过，返回 `skipped`，不调用任何渠道 |
| 5 | **晚间满卡仍发晚报** | 自动化 | `test_evening_summary_dispatches_when_completed` | 当日作业全部打勾时，21:50 触发依然成功发出「🎉 今日满卡」喜报 |
| 6 | **催办带待办清单** | 自动化 | `test_reminder_contains_uncompleted_items` | 当有未完成作业时，催办内容中提取出具体的学科名称、待办题干与学生姓名 |
| 7 | **立即发送汇总与频控** | 自动化 | `test_force_summary_dispatch_and_rate_limit` | `force_summary=True` 立即推送最新快照，并有 30 秒防连击频控保护 |
| 8 | **微信服务号推送** | 自动化 | `test_wechat_pushplus_and_serverchan` | 模拟 PushPlus 与 Server酱 报文构造，验证附带防重序号，未实名 905 错误友好提示 |
| 9 | **iOS Bark 推送** | 自动化 | `test_bark_notification` | 验证 Bark 拼装 URL 包含分组、标题与正文，code!=200 失败时不误判为成功 |
| 10 | **群机器人与错误提示** | 自动化 | `test_webhook_adapter_and_error_handling` | 适配企微/钉钉/飞书格式；当 Webhook URL 格式非法时返回友好的中文提示 |
| 11 | **多渠道并行与容错** | 自动化 | `test_multichannel_fault_tolerance` | 模拟渠道 A 抛出网络超时，渠道 B 正常返回，验证通道互不干扰 |
| 12 | **月历 API 性能与准确度** | 自动化 | `test_monthly_calendar_api_performance_and_accuracy` | 测试 `GET /api/homework/calendar` 执行耗时 ≤ 50ms，红/黄/绿/灰四色状态精确匹配 |
| 13 | **Windows 文件锁防重** | 自动化 | `test_windows_msvcrt_scheduler_lock_real_assertion` | 测试同一环境二次获取 `scheduler.lock` 触发拦截返回 False，释放后可重用 (真断言) |
| 14 | **Web Push 解耦验证** | 自动化 | `test_webpush_decoupled_graceful_handling` | 验证 Web Push 缺库时返回提示而非 500，真机验收明确列入 M6 |
| 15 | **作业页月历交互** | 真机手动 | 前端交互实测 | 点击顶部日历图标弹出月历，红黄绿灰状态正确，点击任意日期切换加载作业 |
| 16 | **番茄钟切屏防漂移** | 真机手动 | 前端切后台实测 | 启动番茄钟切后台或黑屏 25 分钟后切回，基于时间戳剩余时间校准准确，系统推送兜底 |

---

## 4. 实施执行步骤

1. **Step 1：数据库模型与 SQLite Batch Alembic 迁移**
   - 在 `models.py` 中为 `NotificationLog` 添加 `UniqueConstraint`，修正 `sent_at` 为上海时区。
   - 编写手写批处理迁移脚本（使用 `with op.batch_alter_table("notification_logs") as batch_op:`）。
   - 执行 `uv run alembic upgrade head`。
2. **Step 2：多渠道分发器与富文本模板**
   - 编写 `backend/app/utils/notifier.py`（支持 PushPlus、Server酱、Bark、Webhook，注入防重序列号，预留 Web Push）。
   - 编写 `backend/app/routers/notifications.py`（单通道测试、获取/更新渠道配置、立即发送今日汇总）。
   - 在 `backend/app/main.py` 挂载路由。
3. **Step 3：定时调度引擎与 Windows 文件锁**
   - 编写 `backend/app/scheduler.py`（实现 Windows `msvcrt` 文件锁与分时分级逻辑）。
   - 在 `backend/app/main.py` lifespan 挂载调度器启停。保持 `seed_database()` 在模块级。
4. **Step 4：月度打卡日历接口与前端组件**
   - 在 `backend/app/routers/homework.py` 增加 `GET /api/homework/calendar` 接口（`pattern=r"^\d{4}-\d{2}$"`，支持红黄绿灰）。
   - 新建 `frontend/src/components/CalendarModal.vue`。
   - 更新 `frontend/src/views/HomeworkView.vue` 顶部集成日历入口 📅。
5. **Step 5：番茄钟与家长设置面板**
   - 新建 `frontend/src/components/PomodoroTimer.vue`（绝对时间戳校准）。
   - 在 `HomeworkView.vue` 添加番茄钟悬浮按钮。
   - 升级 `frontend/src/views/SettingsView.vue`，增加 PushPlus/Server酱/Bark/机器人配置表单、实名提示、单通道测试、立即发送汇总按钮及备份凭据安全警示。
6. **Step 6：全量自动化测试与工程验证**
   - 编写并运行 `tests/test_m3_notifications_and_calendar.py`，全量执行 `uv run pytest -v`（覆盖 M1+M2+M3 全部测试）。
   - 前端执行 `npm run build` 验证生产打包无错。
   - 提交代码，同时更新远端 `m2-done` tag 与新增 `m3-done` tag，并 push 到 GitHub。
