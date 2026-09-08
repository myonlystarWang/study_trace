# Walkthrough: StudyTrace 服务化与 Cloudflare 隧道改造完成

## 概述

我们已彻底解决了原有 `start-silent.vbs` + `shell:startup` 方案的三大硬伤（必须用户登录才触发、无崩溃自愈、无法保证隧道与后端顺序），成功将 **StudyTrace** 与 **Cloudflare Tunnel** 注册为原生的 Windows 系统服务（NSSM 托管），并实现了配置的项目级完全隔离。

---

## 改造内容与实施明细

### 1. 配置项目级独立隔离
- **新建配置目录**：[config/cloudflared/config.yml](file:///d:/工作/ww/personal_work/study_trace/config/cloudflared/config.yml)
- **私钥凭据转移**：将 `b0a81d67-112b-48e9-b953-98215e248290.json` 移入项目内部目录管理。
- **Git 安全屏蔽**：在 [.gitignore](file:///d:/工作/ww/personal_work/study_trace/.gitignore) 中添加了 `config/cloudflared/*.json`，确保密钥绝不外泄。
- **运维脚本更新**：更新了 [run-prod-daemon.bat](file:///d:/工作/ww/personal_work/study_trace/run-prod-daemon.bat) 与 [run-tunnel.bat](file:///d:/工作/ww/personal_work/study_trace/run-tunnel.bat)，全面改用 `--config` 参数指向项目内配置。

### 2. 彻底清理旧启动方式
- **删除 Startup 快捷方式**：删除了 `Startup\StudyTrace.lnk`，防止开机双启撞端口。
- **终止残留进程**：释放了原本被手动 Python 进程占用的 28000 端口。

### 3. 注册 NSSM Windows 系统服务
两个服务均采用 `LocalSystem` 账号运行，**无需密码输入，开机无需登录桌面即可常驻，且具备崩溃 5 秒自愈**：

| 服务名称 | 显示名称 | 执行命令与参数 | 启动类型 | 当前状态 |
|---|---|---|---|---|
| `StudyTraceCloudflared` | StudyTrace Cloudflare Tunnel | `cloudflared.exe --config ...\config.yml tunnel run study-trace` | Automatic (Delayed) | **Running** ✅ |
| `StudyTrace` | StudyTrace Backend Server | `...\.venv\Scripts\python.exe run.py` | Automatic (Delayed) | **Running** ✅ |

---

## 验证结果

### 1. Windows 服务状态验证
```powershell
Name                  DisplayName                   Status  StartType
----                  -----------                   ------  ---------
StudyTrace            StudyTrace Backend Server     Running Automatic
StudyTraceCloudflared StudyTrace Cloudflare Tunnel  Running Automatic
```

### 2. 接口健康检查
- **本地回环接口**（`http://127.0.0.1:28000/api/health`）：
  ```json
  {"status":"ok","project":"StudyTrace","version":"0.1.0"}
  ```
- **公网 Cloudflare 域名**（`https://study.raddishlab.tech/api/health`）：
  ```json
  {"status":"ok","project":"StudyTrace","version":"0.1.0"}
  ```

### 3. 交叉隔离验证
- 检查 `FundManagementLocalServer`：状态保持为 **Running**，完全未受干扰。
- 检查 `FundManagementCloudflaredTunnel`：状态保持为 **Stopped / Manual**，符合该项目独立控制的预期。

---

## 运维命令参考

如果后续需要查看日志或手动管理服务：
- **查看后端服务日志**：`D:\工作\ww\personal_work\study_trace\data\studytrace-stdout.log` / `studytrace-stderr.log`
- **查看隧道日志**：`D:\工作\ww\personal_work\study_trace\data\cloudflared-stdout.log` / `cloudflared-stderr.log`
- **重启服务**：`Restart-Service StudyTrace` 或 `Restart-Service StudyTraceCloudflared`
- **一键卸载服务**（如需回滚）：右键以管理员运行 [scripts/uninstall-studytrace-services.ps1](file:///d:/工作/ww/personal_work/study_trace/scripts/uninstall-studytrace-services.ps1)
