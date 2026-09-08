# M6 部署上线与安全加固交付总结 (Walkthrough)

基于 [`doc/deployment_audit.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/deployment_audit.md) 审计报告与 [`doc/m6_deployment.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/m6_deployment.md) 实施手册，已全面完成 **M6「部署上线」与暴露前安全加固**，服务与隧道均已在线运行。

---

## 一、核心交付成果概览

| 阶段 | 任务目标 | 交付状态 | 核心技术落地 |
| :--- | :--- | :--- | :--- |
| **阶段 0** | 暴露前安全加固与大端口隔离 | ✅ **已交付** | 生产绑定 `28000`，开发绑定 `28001`；`/api/backup/export` 与 `import` 加家长 PIN 门禁；初始 PIN 888888 强制弹窗警告；`SECRET_KEY` 随机生成落 `data/.env`；生产收紧 CORS；**57/57 自动化测试 100% 全绿** |
| **阶段 1** | Cloudflare 命名隧道打通 | ✅ **已交付** | 官方 `cloudflared` (2026.8.3) 安装；授权域名 `raddishlab.tech`；创建隧道 `study-trace` (UUID: `b0a81d67-112b-48e9-b953-98215e248290`)；自动路由 CNAME 到 `study.raddishlab.tech` 并映射到 `127.0.0.1:28000` |
| **阶段 2** | 常开守护与开机免登录自启 | ✅ **已升级** | 采用 NSSM 注册系统服务（`StudyTraceCloudflared` 与 `StudyTrace`），运行账号为 `LocalSystem`，无需登录桌面开机自启，配置 5 秒崩溃自愈与独立文件日志；废弃旧版 Startup/VBS 方案 |
| **阶段 3** | 真机外网闭环验证 | ✅ **已验证** | `https://study.raddishlab.tech/api/health` 与前端应用均通过 Cloudflare CDN 正常访问，证书有效 |
| **阶段 4** | 文档更新与 GitHub 同步 | ✅ **已交付** | 更新 `README.md`、`doc/change_log.md` (v1.7.0)、`doc/m6_deployment.md`；代码全量提交，打标 `m6-done` 并推送至 GitHub 远端 |

---

## 二、关键验证实测结果

### 1. 自动化测试套件 (57/57 全绿)
```bash
uv run pytest -v
# 结果：57 passed, 2 warnings in 16.77s
```
包含新增的 `tests/test_m6_security.py`：
- `test_m6_ports_and_origins_config`: PASSED
- `test_m6_children_endpoints_stay_passwordless`: PASSED（保证孩子端日常免密输入）
- `test_m6_backup_export_requires_pin`: PASSED（未带 PIN 严格返回 401）
- `test_m6_backup_import_requires_pin`: PASSED（未带 PIN 严格返回 401）
- `test_m6_pin_status_and_default_detection`: PASSED

### 2. 公网健康检查与安全门禁实测
- **正式公网访问**：
  ```bash
  curl.exe -i https://study.raddishlab.tech/api/health
  # HTTP/1.1 200 OK
  # {"status":"ok","project":"学迹 StudyTrace","version":"0.1.0"}
  ```
- **公网未带 PIN 拖库拦截**：
  ```bash
  curl.exe -i https://study.raddishlab.tech/api/backup/export
  # HTTP/1.1 401 Unauthorized
  # {"detail":"需要家长管理口令 (请在请求头提供 X-Parent-PIN 或在参数中提供 pin)"}
  ```

---

## 三、真机使用与运维指南

### 1. 家里手机端访问（断开 WiFi 使用蜂窝网络测试）
1. 在 iPhone Safari 浏览器打开：`https://study.raddishlab.tech`
2. 点击 Safari 底部「分享」按钮 -> **「添加到主屏幕」**；
3. 即可在手机桌面上以独立全屏 PWA 形式随时随地打卡、拍照与复习。

### 2. 服务管理与日常运维
- **开机免登录自启**：系统服务由 Windows SCM 托管，机器开机/重启无需登录 Windows 桌面即可在后台自启运行。
- **崩溃自动恢复**：后端与隧道如遇异常退出，Windows 会在 5 秒后自动拉起。
- **服务状态查看**：
  ```powershell
  Get-Service StudyTraceCloudflared, StudyTrace
  ```
- **服务重启**：
  ```powershell
  Restart-Service StudyTraceCloudflared
  Restart-Service StudyTrace
  ```
- **一键安装/重新注册**：右键以管理员身份运行 `scripts\install-studytrace-services.ps1`
- **一键卸载回滚**：右键以管理员身份运行 `scripts\uninstall-studytrace-services.ps1`
