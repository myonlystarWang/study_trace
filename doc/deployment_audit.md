# StudyTrace 部署与迁移隐患审计报告

> 审计对象：`doc/change_log.md` 全量 17 个版本 + `implementation_plan.md` + `development_plan.md` + `README.md` + 实际代码
> 审计目标：找出**换机器部署**、**公网上线**、**数据长期维护与迁移**三类场景下的隐藏问题
> 审计时间：2026-09-07
> 审计方式：文档与源码交叉比对（不采信文档自述，逐条读源码验证）

---

## 结论速览

| 级别 | 数量 | 一句话概括 |
| :--- | :--- | :--- |
| **P0** | 2 | 隧道凭据不可复现 + 无开机自启守护 → 换机器后外网入口直接断 |
| **P1** | 3 | `.env` 不进备份、还原未校验迁移版本且需重启、备份包无限增长 |
| **P2** | 4 | WAL 文档与实现不符、无鉴权暴露面、前端自愈死角、版本锁定待验证 |

**总体判断**：M0–M5 的代码质量很高（Alembic 迁移链完整、52/52 真绿、新机启动自愈已做），
但 **M6「部署上线」几乎是一片空白**——代码能跑起来，却**没有一个可复现的外网入口和一个不会掉线的守护**。
这正好是本次审计要补的缺口。

---

## P0 — 换机器后服务必然中断

### P0-1 外网入口完全不可复现（Cloudflare 隧道凭据全部在仓库外）

**证据**
- `implementation_plan.md:20` 承诺：「Cloudflare Named Tunnel 映射单一端口 8000 绑定固定域名」
- `development_plan.md:306-316` M6 任务 1：`cloudflared tunnel create study-trace` + `config.yml` → `127.0.0.1:8000`，固定域名 `study.<你的域名>`
- **但**：`README.md` 的「快速开始」(146-198 行) 只写到 `http://localhost:8000`，**全文 0 字提及外网访问 / 穿透 / 域名**
- **且**：`doc/` 下只有 `m3/m4/m5_walkthrough.md`，**没有任何 `m6` 计划或实施文档**（已核实）
- **且**：`.gitignore` 未涉及 `cloudflared` 相关文件，隧道凭据天然不在版本控制内

**影响**
换机器 / 重装系统后必须重新执行 `cloudflared tunnel create`，会生成**新的 Tunnel ID 与凭据**：
1. 旧隧道残留在 Cloudflare 后台，成为僵尸配置
2. 固定域名需重新做 CNAME 指向，孩子手机上的 PWA 书签在切换窗口期失效
3. 若公司笔记本突发故障（该机器有长期蓝屏史），**恢复时间完全取决于人是否记得完整步骤**——而步骤从未被写下来

**修复建议**
```
1. 新建 doc/m6_deployment.md，固化：
   - cloudflared 安装版本与下载源
   - tunnel create / route dns / config.yml 完整命令与文件内容
   - 凭据文件绝对路径（Windows: %USERPROFILE%\.cloudflared\）
   - 如何备份/迁移这组凭据到新机器（整目录拷贝 + 改 config.yml 里的路径）
   - 旧隧道清理步骤
2. README.md 增加「## 外网访问（Cloudflare 固定域名）」章节，或直接链接到 m6_deployment.md
3. 把 %USERPROFILE%\.cloudflared\ 纳入手动备份清单（不能进 git，含私钥）
```

---

### P0-2 无开机自启与进程守护，服务掉线无任何告警

**证据**
- `development_plan.md:318-320` M6 任务 2：「公司笔记本常开配置（用户已确认可保障，**需落地**）」
- 当前启动方式仅有：手动双击 `start.bat` 或 `uv run python run.py`（`README.md:180-186`）
- 全库无计划任务、无服务包装、无崩溃重启、无健康检查告警

**影响**
「公司笔记本常开」是**部署模型的前提**，但目前是纯人工承诺，没有任何工程保障：
1. 笔记本重启 / 蓝屏 / Windows 更新后自动重启 → 服务永久下线
2. 断电恢复后不会自动拉起
3. 休眠或合盖后隧道断开
4. **家里 iPhone 侧表现为「打不开」，且无任何告警通知**——孩子只会以为系统坏了

**修复建议**
```
1. Windows 计划任务（推荐，无需额外依赖）：
   schtasks /create /tn "StudyTrace" /tr "wscript.exe <path>\start.vbs" /sc onlogon /rl highest /f
   （用 .vbs 静默启动，避免弹出黑框被误关）
2. 或 NSSM 包装为 Windows 服务，配置 failure 自动重启
3. 电源策略：powercfg 关闭休眠与合盖睡眠
4. 外部存活探测：用 UptimeRobot / Cloudflare Health Check 盯 /api/health
   （main.py:69 已提供该端点，直接可用）
```

---

## P1 — 数据迁移与长期维护

### P1-3 `data/.env` 不在备份包内，换机器后密钥静默丢失

**证据**
- `config.py:23` — `env_file=str(DATA_DIR / ".env")`，敏感配置（云端视觉模型 API Key 等）从此处读取
- `backup.py:36-56` — 导出清单只包含 `study_trace.db` + `uploads/{originals,thumbnails}` + `manifest.json`，**无 `.env`**
- `implementation_plan.md:120` — 明确设计「敏感 API Key 存 `data/.env`」
- 实测当前 `data/` 下**不存在 `.env`**（尚未配置，故问题暂未暴露）

**影响**
一旦配置了云端 OCR 兜底 Key（智谱 `glm-4v-flash` / 硅基流动）：
- 换机器用备份包还原 → Key 丢失
- `ocr_service` 的三引擎 `auto` 降级逻辑会**静默退到 RapidOCR**——不报错、不告警
- 用户完全无感，只在识别准确率下降时才会发现，且难以归因

**修复建议**
```
1. export 时若 data/.env 存在，一并打入并在 manifest 标记（内容加密或至少导出时二次确认）
   注意：.env 属敏感信息，建议导出时弹窗告知"本包含密钥，请妥善保管"
2. 或更稳妥：把可迁移的配置改为存 Settings 表（已在 DB 内，随备份走），
   仅真正的密钥留 .env，并在 README 明确"换机器需手动重建 .env"
3. manifest.json 增加 env_included 字段，还原时若缺失给出明确提示
```

---

### P1-4 还原备份未校验迁移版本，且服务运行中覆盖 DB 存在风险

**证据**
- `backup.py:92` — `zipf.extract("study_trace.db", path=str(DATA_DIR))` **直接覆盖**运行中的数据库文件
- `backup.py:71-110` — 全程**未读取/校验** 备份包内 DB 的 `alembic_version`
- `run.py:81` — `ensure_database_migrated()` 只在**启动时**执行，还原后不会重跑
- `database.py:5-8` — 引擎为默认连接池，无 `pool_dispose` 处理

**影响**
三个递进风险：
1. **Windows 文件锁**：SQLite 持有 db 句柄时覆盖，可能抛 `PermissionError`，导致还原半途失败、留下损坏的 db
2. **连接池读到旧数据**：即使覆盖成功，SQLAlchemy 连接池中的连接仍指向旧文件句柄 → 前端看到的还是还原**前**的数据，**必须重启服务才生效**（文档与 UI 均未提示）
3. **跨版本回滚崩溃**：若还原的 DB 版本**新于**当前代码的迁移链，`ensure_database_migrated()` 无法降级 → 启动时报错

**修复建议**
```
1. 还原接口返回中明确提示 "请重启服务后生效"，前端弹窗展示
2. 还原前先读取包内 alembic_version 与当前代码 head 比对：
   - 落后 → 提示"将自动升级迁移"
   - 领先 → 直接拒绝并提示版本不兼容
3. 还原后调用 engine.dispose() 释放连接池
4. 覆盖 DB 前先关闭所有连接 / 或改为写入临时文件后原子替换
5. 记录一条还原操作日志（时间、来源包、迁移前后版本）
```

---

### P1-5 备份快照无限增长，无保留策略

**证据**
- `backup.py:82` — **每次 import 都会先 `create_backup_archive()`** 建一份恢复前快照
- 实测 `data/backups/` 已累积 **168 个 zip、9.3 MB**
- 全库无清理逻辑、无保留上限

**影响**
- 每次还原都新增一个包，误操作频繁时增长很快
- `data/uploads` 图片会持续增大 → 每个新包都是全量快照，磁盘占用**线性叠加**
- `export` 接口每次打包遍历全部图片，备份越多、图片越多，接口越慢
- 长期运行（一年）后可能出现数千个文件，且都在同一个目录

**修复建议**
```
1. 增加保留策略：保留最近 N=30 份，超出按时间删除最旧的
2. 或按代际保留：每日首份保留 30 天、每周首份保留 12 周、每月首份永久
3. import 产生的"恢复前快照"单独加前缀 pre_restore_ 并采用更短的保留期（如 10 份）
4. 家长管理页展示备份占用总量，提供手动清理入口
```

---

## P2 — 值得现在就改的小隐患

### P2-6 README 声称 WAL 模式，代码未开启（好心办坏事的伏笔）

**证据**
- `README.md:79` — 「本地数据库 | **SQLite 3 + WAL 模式**」
- `database.py:5-8` — `create_engine` 无任何 `PRAGMA journal_mode=WAL`
- 全 backend 目录 grep `journal_mode|WAL` **零匹配**

**影响**
- 文档与实现不符（当前实际是默认 rollback journal 模式）
- **反直觉的一点**：正因为没开 WAL，直接拷贝 db 文件才是安全的，备份不会丢 WAL 数据
- 若将来有人"照着 README 优化"把 WAL 打开 → 数据会先写进 `study_trace.db-wal`，
  而 `backup.py` 只拷贝 `.db` 主文件 → **最近未 checkpoint 的数据会静默丢失**
- 这是典型的"现在没问题是靠运气，改了就出事"

**修复建议**
```
二选一：
A. 改 README，删除"WAL 模式"表述（保持现状，最简单）
B. 若要开 WAL：必须同步把 backup.py 改为使用 sqlite3 backup API
   （conn.backup(dest) 或先执行 PRAGMA wal_checkpoint(TRUNCATE)），
   否则备份不可信
```

---

### P2-7 无鉴权暴露面：公网化会激活的风险

**证据**
- `main.py:28-34` — CORS `allow_origins=["*"]`、`allow_methods=["*"]`
- 除家长端 `require_parent_pin` 外，孩子端全部 API（作业增删改、错题、成绩）**无鉴权**
- `config.py:40-41` — `SECRET_KEY = "study-trace-secure-local-key-2026"`、`DEFAULT_PIN = "888888"` **硬编码且已进 git**
- `main.py:37` — `/uploads` 静态目录直接挂载，图片 URL 可枚举

**影响**
现状（家庭局域网自用）风险可控。但 M6 挂上 Cloudflare 固定域名后，**任何拿到域名的人**可以：
1. 直接调用 `/api/backup/export` **拖走全量数据**（含孩子作业照片）
2. 直接增删改作业与错题
3. 家长 PIN 默认 `888888`，等于没有门禁

**修复建议**
```
M6 上线前必须完成：
1. 强制首次启动修改默认 PIN（未修改则家长端强制弹修改框）
2. SECRET_KEY 改为启动时随机生成并落 data/.env，不再硬编码
3. CORS 收紧为实际域名（至少生产模式）
4. 公网入口加一层基础防护（Cloudflare Access 或简单 HTTP Basic）
5. /api/backup/export 强制 require_parent_pin（当前未加！）
```

> 注：第 5 条为**当前即可利用的越权**，建议优先修。

---

### P2-8 `run.py` 前端自愈存在死角

**证据**
- `run.py:82-88`：
  ```
  if not FRONTEND_DIST.exists():
      ... npm install ... npm run build
  ```

**影响**
- 新克隆仓库（`dist/` 不存在）→ 会正确触发构建 ✅
- 但从旧机器**整个目录拷贝**过来（`dist/` 存在但内容过时）→ **不会重建**，会托管旧前端
- 表现为「后端接口是新的，页面是旧的」，排查成本极高

**修复建议**
增加 `--rebuild` 参数，或在构建产物中写入源码 hash，启动时比对决定是否重建。

---

### P2-9 环境复现前置项待确认

**已确认存在**（换机器可复现的基础）：
- `.python-version`（4 字节）、`.node-version`（3 字节）、`uv.lock`（99 KB）、`pyproject.toml`
- 根 `alembic.ini:8` — `script_location = %(here)s/backend/alembic`（路径正确，`uv run alembic upgrade head` 可用）

**仍需在新机器实测一次完整流程**：
```
git clone → uv sync → cd frontend && npm install && npm run build → 双击 start.bat
```
建议把这次实测结果写成 `doc/m6_deployment.md` 的「新机迁移检查清单」。

---

## 建议的处理顺序与完成状态

| 顺序 | 事项 | 状态 | 说明 / 修复落地 |
| :--- | :--- | :--- | :--- |
| 1 | `/api/backup/export` 加 `require_parent_pin` | ✅ **已完成 (v1.7.0)** | export 与 import 均已接入家长 PIN 门禁，前端升级为安全 Blob 下载 |
| 2 | 写 `doc/m6_deployment.md`（隧道 + 凭据迁移 + 新机检查清单） | ✅ **已完成 (v1.7.0)** | 完整落地并回填实施记录（UUID、版本、端口与迁移预案） |
| 3 | Windows 开机自启 + 电源策略 | ✅ **已完成 (v1.7.0)** | `powercfg` 关闭接电休眠与合盖睡眠；`start-silent.vbs` 后台静默自启 |
| 4 | 备份还原：版本校验 + 重启提示 + 连接池释放 | 待后续迭代 (v1.7.1) | 数据长期迁移优化 |
| 5 | 备份保留策略（保留最近 30 份） | 待后续迭代 (v1.7.1) | 长期数据维护，防止快照无限堆积 |
| 6 | `.env` 纳入备份或明确迁移说明 | 待后续迭代 (v1.7.1) | 避免敏感配置迁移丢失 |
| 7 | 公网化前：默认 PIN 强制修改 + SECRET_KEY 随机化 + CORS 收紧 | ✅ **已完成 (v1.7.0)** | 强制改密弹窗、SECRET_KEY 随机落 `data/.env`、生产 CORS 限制实际域名 |

---

## 附：已确认**没有问题**的点（避免重复排查）

- ✅ Alembic 迁移链完整：5 个版本脚本，`1d0567bc331b` 初始迁移已补齐 DDL（v1.6.3 修复）
- ✅ `run.py:81` 启动自动 `upgrade head`，新机不会因漏敲迁移崩溃
- ✅ 测试套件走真实 Alembic 迁移（不再 `create_all` 伪绿）
- ✅ 根 `alembic.ini` 指向正确，`sqlalchemy.url` 已注释（v1.6.3）
- ✅ 时区全链路 Python 侧处理，无 `func.now()` / `datetime('now')` / `utcnow()`（换时区机器安全）
- ✅ 未开 WAL，当前备份拷贝是安全的（但见 P2-6）
- ✅ 前端 dist 与 node_modules 有基础自愈（见 P2-8 死角）
