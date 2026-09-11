# M6 — 部署上线实施方案

> 文档定位：M6「部署上线」的执行手册。包含实施方案、**待决策点**、**风险清单**与验收标准。
> 前置文档：[`doc/deployment_audit.md`](deployment_audit.md)（部署与迁移隐患审计，9 项问题）
> 决策时间：2026-09-07（出差期间，plan 模式讨论后定案）
> 状态：**阶段 0 未开工**，本文为待评审方案

---

## 零、背景与目标

**目标**：公司/家中一台常开电脑运行 StudyTrace，家里 iPhone 通过固定域名随时访问。

**当前处境**：用户有两台电脑——

| 机器 | 现状 | 未来定位 |
| :--- | :--- | :--- |
| **公司机** | 长期开机，原定 M6 宿主；老硬盘卡顿 | **准备淘汰** |
| **出差机（当前开发机 `ww-computer`）** | 出差携带，酒店有电有网；`data/` 全量数据与完整工具链都在此 | **未来正式宿主** |

**结论**：M6 直接在出差机上做。在公司机上做等于"做完就淘汰、换机时再迁一遍"，白做一轮。

---

## 一、已确认的决策与前提

| # | 事项 | 结论 | 影响 |
| :--- | :--- | :--- | :--- |
| 1 | 部署方案 | **A — 出差机现在做完** | 一次做完，未来移至公司常驻即为公司机 |
| 2 | Cloudflare 域名 | **raddishlab.tech 已就绪** | 固定二级域名 `study.raddishlab.tech`，命名隧道前置完全满足 |
| 3 | 生产数据 | **老机器实例停用，无数据** | 单一实例对外，换机零迁移风险，杜绝 SQLite 数据分叉 |
| 4 | 端口规划 | **prod 28000 / dev 28001** | dev 与 prod 端口彻底隔离，杜绝默认端口冲突与干扰 |

---

## 二、关键技术判断（决定方案走向）

### 2.1 命名隧道凭据可迁移——机器选择不是一次性绑定

`cloudflared tunnel create` 生成的 Tunnel ID、`credentials-file`（`<UUID>.json`）、`cert.pem`
全部位于 `%USERPROFILE%\.cloudflared\`。

**含义**：整目录拷贝到另一台机器 → 安装同版本 cloudflared → 运行同一 tunnel，**DNS 解析无需改动**。
因此"在哪台机器上做"不构成沉没成本，换机只是拷目录，不是重做。

### 2.2 真正的风险是数据分叉，不是机器选择

应用是单文件 SQLite + 本地上传目录，**没有任何多机同步机制**，数据迁移只有"全量备份 / 覆盖还原"一条路。

```
两台机器同时对外服务
   └─> 孩子在 A 打卡一批、在 B 打卡一批
        └─> 用备份还原 = 覆盖式
             └─> 必丢一半，且无冲突检测、无告警
```

**硬约束（写入运维纪律）**：**任何时刻只有一台机器对外服务。**

### 2.3 公网化会激活当前已存在的越权

审计 P2-7：`/api/backup/export` 与 `/api/backup/import` 均未加 `require_parent_pin`；
`main.py:28-34` CORS 为 `allow_origins=["*"]`；`config.py:40-41` 硬编码
`SECRET_KEY` 与 `DEFAULT_PIN = "888888"`。

局域网内无实质危害；**一旦经 Cloudflare 域名公网可访问，任何拿到 URL 的人都能拖走全量数据**（含孩子作业照片）。

> **因此：阶段 0（安全加固）必须先于阶段 1（建隧道）执行，不可颠倒。**

### 2.4 dev / prod 端口冲突

`run.py --dev` 的后端同样占用 **8000**，与生产实例撞车，无法边对外服务边开发。见「四、待决策点 D1」。

---

## 三、实施方案

### 阶段 0 · 暴露前安全加固（必做，先于隧道）

> 纯代码改动，不碰外网，**任何时候中断都无副作用**。

| # | 任务 | 改动位置 | 说明 |
| :--- | :--- | :--- | :--- |
| 0.1 | `export` 端点加家长门禁 | `backend/app/routers/backup.py` | 加 `Depends(require_parent_pin)` |
| 0.2 | `import` 端点加家长门禁 | 同上 | 还原操作更需守卫 |
| 0.3 | 默认 PIN 强制修改 | `auth.py` / `settings.py` | 增加"PIN 是否仍为默认值"标记，首次进入家长端强制弹修改框 |
| 0.4 | `SECRET_KEY` 随机化 | `config.py:40` | 首次启动生成并落 `data/.env`，不再硬编码进 git |
| 0.5 | 生产模式收紧 CORS | `main.py:28-34` | 至少生产模式限制为实际域名 |
| 0.6 | 全量备份 `data/` 到机器外 | 一次性操作 | 虽有"无生产数据"前提，仍先留存一份 |

**配套测试**：补 2 条用例——未带 PIN 访问 `/api/backup/export` 应 401；带 PIN 应 200。

---

### 阶段 1 · Cloudflare 命名隧道

> 以下命令在**出差机**上执行，路径以 Windows 为准。

**1.1 安装 cloudflared**

```powershell
winget install --id Cloudflare.cloudflared
# 或官网下载：https://developers.cloudflare.com/cloudflared/downloads/
cloudflared --version   # 记录版本号，写入本文 7.1
```

**1.2 授权并选择域名**

```powershell
cloudflared tunnel login
# 浏览器弹出 → 选择 NS 托管在 Cloudflare 的域名 → 授权
# 生成 %USERPROFILE%\.cloudflared\cert.pem
```

**1.3 创建命名隧道**

```powershell
cloudflared tunnel create study-trace
# 输出 Tunnel UUID，并生成 %USERPROFILE%\.cloudflared\<UUID>.json
# ★ 记录此 UUID
```

**1.4 编写 `config.yml`**（项目级隔离路径：`config\cloudflared\config.yml`）

```yaml
tunnel: <Tunnel-UUID>
credentials-file: D:\工作\ww\personal_work\study_trace\config\cloudflared\<Tunnel-UUID>.json
protocol: http2

ingress:
  - hostname: study.raddishlab.tech
    service: http://127.0.0.1:28000
  - service: http_status:404
```

**1.5 绑定 DNS 记录**

```powershell
cloudflared tunnel route dns study-trace study.raddishlab.tech
```

**1.6 注册为 Windows 系统服务（NSSM 方案，项目级独立隔离）**

采用 `C:\tools\nssm\nssm.exe` 统一注册为独立服务，避免多项目冲突：
- `StudyTraceCloudflared`：带 `--config` 参数独立运行本项目的隧道。
- `StudyTrace`：托管 Python 后端。
一键安装脚本：以管理员身份执行 `scripts\install-studytrace-services.ps1`。

**1.7 验证**

```powershell
cloudflared tunnel info study-trace
curl https://study.<你的域名>/api/health
# 期望：{"status":"ok","project":"智学迹 StudyTrace",...}
```

---

### 阶段 2 · 常开与守护

**2.1 关闭休眠与合盖睡眠**（出差期间尤其重要）

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT
```

**2.2 StudyTrace 与 Cloudflared 开机自启（NSSM 服务）**

已全面废弃旧版 VBS/Startup 方案，通过 NSSM 注册为系统级服务：
- 账号：`LocalSystem`（彻底免密，重启后无需登录 Windows 即可自动拉起）
- 启动类型：`SERVICE_DELAYED_AUTO_START`（开机延迟启动，等待网络就绪）
- 守护机制：`AppRestartDelay 5000`（异常崩溃 5 秒自动重启自愈）
- 日志输出：`data\studytrace-*.log` 与 `data\cloudflared-*.log`

**2.3 外部存活探测**

`main.py:69` 已提供 `/api/health`。接入 UptimeRobot 或 Cloudflare Health Check，
服务掉线时主动告警（否则孩子只会看到"打不开"，无人知晓）。

---

### 阶段 3 · 真机验收（酒店实测）

| # | 项目 | 通过标准 |
| :--- | :--- | :--- |
| 3.1 | iPhone Safari 打开固定域名 | 页面正常加载，非 localhost |
| 3.2 | 添加到主屏幕（PWA） | 全屏独立运行、图标正常 |
| 3.3 | 完整业务闭环 | 录入作业 → 打卡 → 拍照错题 → OCR → 周末组卷，全链路通过 |
| 3.4 | 推送渠道实测 | 微信官方测试号 (Sandbox) / iOS Bark / 群机器人 能正常收到原生弹窗提醒与家庭全员广播 |
| 3.5 | HTTPS 与证书 | 地址栏无证书警告（影响 PWA 与 Web Push） |

---

### 阶段 4 · 文档固化

| # | 任务 |
| :--- | :--- |
| 4.1 | 将实际执行的命令、版本号、UUID、config.yml 内容回填本文「7.1 实施记录」 |
| 4.2 | README 增加「外网访问（Cloudflare 固定域名）」章节 |
| 4.3 | `change_log.md` 补 v1.7.0 —— M6 部署上线 |
| 4.4 | 将审计文档中的 P0-1 / P0-2 / P1-3 / P1-4 / P1-5 标记状态更新 |

---

## 四、待决策点

> 以下三点需用户拍板后再进入对应阶段。

### D1 · dev / prod 端口冲突（【已决】采用大端口隔离）

- **决议**：生产服务改用端口 **28000**，开发后端改用端口 **28001**（前端 Vite 5173 代理动态指向 28001）。两者均采用大端口，既杜绝冲突，又互不干扰。

### D2 · 老机器实例处置（【已决】停掉老机器服务）

- **决议**：明确关停老机器上的 StudyTrace 实例，保证全系统任何时刻仅有当前这一台机器对外提供服务，杜绝 SQLite 数据库分叉。

### D3 · 酒店网络容忍度（影响阶段 3 判定）

cloudflared 为纯出站连接，但部分酒店 WiFi 有 **captive portal**，断线后需浏览器重新认证。

- 若断网频繁：阶段 3 的真机验收结果**不作为最终结论**，回公司后需复测
- 无论如何：合盖睡眠必须先关（D 阶段 2.1），否则一合盖必断

---

## 五、风险清单

| ID | 风险 | 等级 | 触发时机 | 缓解措施 |
| :--- | :--- | :--- | :--- | :--- |
| R1 | **越权拖库**：`/api/backup/export` 无门禁，公网暴露后任何人可下载全量数据（含孩子照片） | **P0** | 隧道一开即生效 | 阶段 0.1/0.2 先于隧道执行；未修复则不开隧道 |
| R2 | **默认 PIN 888888**：公网可达时门禁形同虚设 | **P0** | 隧道一开即生效 | 阶段 0.3 强制首次修改 |
| R3 | **数据分叉丢失**：两台机器同时对外服务，还原为覆盖式 | **P0** | 双实例运行 + 还原操作 | 硬约束只留一台对外；D2 明确停业公司机 |
| R4 | **服务静默掉线**：无开机自启与守护，重启/蓝屏后永久下线且无告警 | **P0** | 机器重启后 | 阶段 2 计划任务 + cloudflared 服务 + `/api/health` 外部探测 |
| R5 | **酒店网络中断**：captive portal 重认证 / 合盖睡眠导致隧道断连 | **P1** | 出差期间 | 阶段 2.1 关睡眠；验收结果标注"酒店环境"待复测 |
| R6 | **`.env` 不进备份包**：换机还原后 OCR 云端 Key 静默丢失，降级无告警 | **P1** | 未来换机时 | 见审计 P1-3；本轮无 Key 暂不影响 |
| R7 | **还原需重启且未校验版本**：覆盖运行中 DB 可能 `PermissionError`，连接池读到旧数据 | **P1** | 未来还原操作 | 见审计 P1-4；本轮无生产数据暂不触发 |
| R8 | **凭据丢失**：`%USERPROFILE%\.cloudflared\` 不在 git、不在备份包 | **P1** | 系统重装 / 换机 | 阶段 4.1 记录路径；手动备份该目录到机器外 |
| R9 | **CORS 全开 + SECRET_KEY 硬编码入 git** | **P2** | 公网化后放大 | 阶段 0.4 / 0.5 |
| R10 | **备份包无限增长**（现有 168 个 / 9.3MB，无保留策略） | **P2** | 长期运行 | 审计 P1-5，非 M6 阻塞项，建议纳入 v1.7.1 |

---

## 六、验收标准（M6 完成判据）

- [ ] 阶段 0 全部完成，且新增 2 条门禁测试通过（未带 PIN 401）
- [ ] `https://study.<域名>/api/health` 从**手机蜂窝网络**（非同一 WiFi）可访问且返回 ok
- [ ] iPhone 添加到主屏幕后可全屏独立运行
- [ ] 完整业务闭环在真机上跑通一次
- [ ] 机器重启后 StudyTrace 与 cloudflared **均自动恢复**，无需人工干预
- [ ] 外部存活探测已接入，服务掉线会告警
- [ ] `doc/m6_deployment.md` 实施记录已回填（版本、UUID、config.yml）
- [ ] 公司机实例已确认停止对外服务

---

## 七、换机与迁移预案

### 7.1 实施记录（执行时回填）

| 项 | 值 |
| 项 | 值 |
| :--- | :--- |
| cloudflared 版本 | `2026.8.3` |
| Tunnel UUID | `b0a81d67-112b-48e9-b953-98215e248290` |
| 固定域名 | `study.raddishlab.tech` |
| 映射本地端口 | `127.0.0.1:28000` |
| 凭据目录 | `%USERPROFILE%\.cloudflared\` |
| 实施日期 | `2026-09-07` |

### 7.2 未来换机步骤（无需重建隧道）

1. 新机器安装**相同版本** cloudflared
2. 拷贝整个 `%USERPROFILE%\.cloudflared\` 目录到新机器相同路径
   （若用户名不同，需修改 `config.yml` 中的 `credentials-file` 绝对路径）
3. `cloudflared service install` 装为服务
4. 迁移 `data/`（用 `/api/backup/export` 导出 zip，在新机器 `/api/backup/import` 还原）
5. **还原后必须重启服务**（连接池指向旧句柄，见审计 P1-4）
6. DNS 无需改动——命名隧道是出站连接，新机器起来后自动接管
7. 若旧机器仍在 Cloudflare 后台留有隧道记录，手动清理避免僵尸配置

### 7.3 凭据备份提醒

`%USERPROFILE%\.cloudflared\` 含**私钥**，不得进 git。手动备份到机器外安全位置（密码管理器 / 加密U盘）。
