# study_trace 服务化改造：从 VBS/Startup 迁移到 nssm Windows 服务

## 背景

study_trace 目前使用 `start-silent.vbs` + `shell:startup` 快捷方式实现开机启动，存在三个核心问题：必须用户登录才触发、没有崩溃自愈、没有启动顺序保障。同时 cloudflared 的 config 和 credentials 放在全局 `%USERPROFILE%\.cloudflared\`，和 fund 项目潜在冲突。

本计划将 study_trace 迁移到 nssm Windows 服务方案，并完成 cloudflared 配置的项目级隔离。

## 前置决策（实测落地调整）

| 决策项 | 结论 |
|---|---|
| config/credentials 位置 | 移到 `study_trace\config\cloudflared\` 项目内（完全隔离） |
| cloudflared 二进制 | 统一使用 `C:\Program Files (x86)\cloudflared\cloudflared.exe` |
| 服务账号 | **LocalSystem**（实测：Windows 服务的 SCM 机制不支持 PIN 码，且配置迁移后已完全不依赖用户 Profile，LocalSystem 彻底免密且开机免登录常驻） |
| 服务注册方式 | nssm（`StudyTraceCloudflared` + `StudyTrace`） |
| wrapper 脚本 | study_trace 不加 wrapper，直接 nssm 起 cloudflared，配置 5s 崩溃自愈 |
| 启动类型 | Automatic (Delayed Start) |
| 执行范围 | study_trace 已全量落地并验证通过 |

---

## fund 项目待办（根据实测结论修正）

> [!IMPORTANT]
> **重要修正**：原第 1 条「改服务账号为 `.\ww`」**已取消/无需修改**！
> **原因**：
> 1. 用户日常登录 Windows 使用的是 **PIN 码**，Windows 服务控制器不支持 PIN 码认证；
> 2. Fund 项目的 `FundManagementLocalServer` 与 `FundManagementCloudflaredTunnel` **原本就是使用 `LocalSystem` 运行的**；
> 3. 实测证明 `LocalSystem` 稳定可靠、免密无维护负担，**继续保持 `LocalSystem` 是最优解**，无需折腾改账号。

修正后的 fund 项目待办：

| # | 改动项 | 必要性 | 正确做法 |
|:--:|---|:---:|---|
| 1 | 服务账号改 `.\ww` | ❌ **取消** | **保持现状 `LocalSystem`**，无需任何操作，避免 PIN 码失效及改密码维护负担 |
| 2 | cloudflared 路径统一 | 可选/低优 | 若想与 study_trace 彻底统一二进制路径，在 fund 目录下跑：<br>`install-cloudflared-service.ps1 -CloudflaredPath 'C:\Program Files (x86)\cloudflared\cloudflared.exe'`<br>（注：跑完后若需要保持按需启动，需再执行 `sc.exe config FundManagementCloudflaredTunnel start= demand`） |
| 3 | 清理旧文件 | ⚠️ 暂缓 | `C:\Users\ww\.local\bin\cloudflared.exe` 暂不清理，等 fund 确认统一路径并无进程引用后再删 |
