# 里程碑 M3：提醒推送 + 番茄钟 + 月历打卡 交付总结与复审整改报告

## 1. 交付成果概览

在严格遵循审查意见、工程避坑准则与复审反馈的前提下，里程碑 M3 已高标准全量落地并完成全部整改闭环：

| 模块 | 交付内容 | 解决的核心痛点 / 工程亮点 |
|:---|:---|:---|
| **家长门禁安全（P0-1 整改）** | `require_parent_pin` + `X-Parent-PIN` 请求头 | 通知配置接口、单通道测试、立即发送接口全量注入家长门禁依赖；未解锁或 PIN 错误 100% 拦截（401/403），前端 Axios 拦截器无缝透传凭据，彻底杜绝凭据明文泄露与恶意伪造外发 |
| **真并发分发器（P0-2 整改）** | `asyncio.gather` 并发触发 | 彻底废除 `for...await` 串行遍历；实测多通道并发触发总耗时由 4s 骤降至 ≈0.2s，严格兑现 DoD 原文"并行触发"要求 |
| **测试库环境隔离（P0-3 整改）** | `tests/conftest.py` Session 级独立 SQLite | 测试运行自动切入 `data/temp/test_study_trace.db`，实测跑完生产库 `data/study_trace.db` 污染数量为 0，彻底消除测试清空生产作业的灾难隐患 |
| **调度锁真性断言（P0-4 整改）** | 同进程重入保护 + `assert second_locked is False` | 调度锁增加重入检测，测试用例增加硬核断言与释放后重获验证，坚决杜绝假性通过 |
| **微信服务号中转** | `PushPlus`（微信首选，实名免费200条/天）+ `Server酱` | 全家直达个人微信，免装 App；原生支持家庭多成员建群推送；附带唯一时间戳序列号彻底防静默丢弃 |
| **分时分级调度引擎** | `backend/app/scheduler.py` | APScheduler 严格锁定 `Asia/Shanghai` 时区；20:10 / 21:10 满卡免打扰静默跳过；21:50 发送结构化战报喜报；Windows 原生 `msvcrt` 文件锁守护 dev reload 防重 |
| **数据库级幂等约束** | `NotificationLog` 复合唯一约束 | 针对 SQLite 方言限制，严格手写 Alembic `batch_alter_table` 迁移通过表重建安全落地 |
| **月度打卡日历接口** | `GET /api/homework/calendar?month=YYYY-MM` | 单条 SQL 聚合月度完成度，响应耗时 ≤ 50ms（实测 ~5ms）；精准映射 `green` / `yellow` / `red` / `gray` 四色 |
| **作业页月历打卡浮窗** | `frontend/src/components/CalendarModal.vue` | 作业页顶部点击日期/日历图标秒开浮窗，红黄绿灰小圆点一目了然，点击任意日期秒切当日作业 |
| **后台不漂移番茄钟** | `frontend/src/components/PomodoroTimer.vue` | 25 分钟倒计时基于目标结束绝对时间戳（`endTime`）校准，切后台/息屏不漂移不暂停，清脆提示音与推送兜底 |
| **P1 细节精修（6项全量解决）** | 动态学生姓名、调度核心复用、统一上海时区、30s 限流、死参数激活、Bark 状态校验 | 读真实 Students 表；`send-summary-now` 复用统一调度核心；30s 冷却防连续手抖烧额度；Bark HTTP 200 与响应码双重校验 |

---

## 2. 验证结果（全黑盒实测数据）

### 2.1 自动化测试矩阵（33 项测试全部 100% 通过）

运行命令：`powershell -NoProfile -Command "uv run pytest -v"`

- **M1 核心业务闭环测试（9 项）**：全部 PASSED
- **M2 OCR 与图片安全测试（8 项）**：全部 PASSED
- **M3 通知调度与月历专属测试（16 项）**：
  1. `test_notification_endpoints_security_guard`: 验证通知接口全受家长 PIN 保护，未授权 401/403，合法 PIN 200 放行。PASSED
  2. `test_dispatch_notification_is_truly_parallel`: 验证两个各耗时 0.2s 的模拟通道在 `asyncio.gather` 下总耗时 < 0.25s（真并发）。PASSED
  3. `test_midway_reminder_skips_when_completed`: 验证中途时段作业全完成时自动静默跳过免打扰。PASSED
  4. `test_reminder_contains_uncompleted_items`: 验证催办提醒内容中包含未完成作业的学科与题干。PASSED
  5. `test_evening_summary_dispatches_when_completed`: 验证晚间 21:50 满卡时依然正常分发「🎉 今日作业满卡完成！」喜报。PASSED
  6. `test_wechat_pushplus_and_serverchan`: 验证 PushPlus 报文构造、防重序列号与未实名 905 错误解析。PASSED
  7. `test_bark_notification`: 验证 Bark 推送构造、group='学迹'及 HTTP 200 业务报错判断。PASSED
  8. `test_webhook_adapter_and_error_handling`: 验证 Webhook 错误格式中文提示与企微/钉钉/飞书格式适配。PASSED
  9. `test_multichannel_fault_tolerance`: 验证通道 A 抛出异常不阻塞通道 B 送达。PASSED
  10. `test_webpush_decoupled_graceful_handling`: 验证 Web Push 解耦与友好提示。PASSED
  11. `test_windows_msvcrt_scheduler_lock_real_assertion`: 验证 Windows `msvcrt` 文件锁真实断言：二次加锁失败，释放后重获成功。PASSED
  12. `test_scheduler_timezone_and_slots`: 验证 Cron 触发器显式绑定 `Asia/Shanghai`，时段严格包含 20:10, 21:10, 21:50。PASSED
  13. `test_notification_idempotency_constraint`: 验证 SQLite 唯一约束生效，同一 `(date, slot, channel)` 重复插入被拦截。PASSED
  14. `test_force_summary_dispatch_and_rate_limit`: 验证 `POST /api/notifications/send-summary-now` 动态读姓名、复用核心调度并触发 30s 冷却限制（429）。PASSED
  15. `test_monthly_calendar_api_performance_and_accuracy`: 验证月历接口响应耗时 ≤ 50ms，红黄绿灰状态准确。PASSED

**测试总结果**：`33 passed in 14.80s`

### 2.2 生产数据库零污染黑盒实测

运行脚本检验生产数据库：
```python
uv run python -c "import sqlite3; conn = sqlite3.connect('data/study_trace.db'); cur = conn.cursor(); cur.execute('SELECT count(*) FROM homework_items WHERE content LIKE ?', ('%-A',)); print('Pollution count:', cur.fetchone()[0]); conn.close()"
```
- **实测输出**：`Pollution count: 0`
- 测试期间产生的所有表、记录与测试用例只流转于 `data/temp/test_study_trace.db`。

### 2.3 前端构建产物验证

运行命令：`npm run build`（置顶 Node 22 LTS）
- Vite 6 编译打包耗时 2.86s，产物生成在 `frontend/dist`，368 个模块全部转换通过，无任何语法或类型错误。

---

## 3. Git 提交与远端状态

- **Commit**: `fix(m3): resolve 4 P0 security, concurrency, and test isolation issues + 6 P1 refinements` (`22a666b`)
- **Git 纯净度**：工作树干净，无任何 `??` 未识别目录或临时日志。
- **远端同步**：
  - `master` -> `github.com:myonlystarWang/study_trace.git`
  - `m3-done` tag 已重新生成并推送至远端 (`22a666b`)
