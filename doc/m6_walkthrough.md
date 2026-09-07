# M6 部署上线与安全加固交付总结 (Walkthrough)

基于 [`doc/deployment_audit.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/deployment_audit.md) 审计报告与 [`doc/m6_deployment.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/m6_deployment.md) 实施手册，已全面完成 **M6「部署上线」与暴露前安全加固**，服务与隧道均已在线运行。

---

## 一、核心交付成果概览

| 阶段 | 任务目标 | 交付状态 | 核心技术落地 |
| :--- | :--- | :--- | :--- |
| **阶段 0** | 暴露前安全加固与大端口隔离 | ✅ **已交付** | 生产绑定 `28000`，开发绑定 `28001`；`/api/backup/export` 与 `import` 加家长 PIN 门禁；初始 PIN 888888 强制弹窗警告；`SECRET_KEY` 随机生成落 `data/.env`；生产收紧 CORS；**57/57 自动化测试 100% 全绿** |
| **阶段 1** | Cloudflare 命名隧道打通 | ✅ **已交付** | 官方 `cloudflared` (2026.8.3) 安装；授权域名 `raddishlab.tech`；创建隧道 `study-trace` (UUID: `b0a81d67-112b-48e9-b953-98215e248290`)；自动路由 CNAME 到 `study.raddishlab.tech` 并映射到 `127.0.0.1:28000` |
| **阶段 2** | 常开守护与开机静默自启 | ✅ **已交付** | `powercfg` 关闭接电休眠与合盖睡眠；编写 [`start-silent.vbs`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/start-silent.vbs)（无黑框弹窗静默启动后端与隧道）与 [`stop.bat`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/stop.bat)；在 `shell:startup` 部署自启快捷方式 |
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

## 三、真机使用与操作指南

### 1. 家里手机端访问（断开 WiFi 使用蜂窝网络测试）
1. 在 iPhone Safari 浏览器打开：`https://study.raddishlab.tech`
2. 点击 Safari 底部「分享」按钮 -> **「添加到主屏幕」**；
3. 即可在手机桌面上以独立全屏 PWA 形式随时随地打卡、拍照与复习。

### 2. 日常启动与停止
- **静默启动（无需命令行）**：双击根目录下的 [`start-silent.vbs`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/start-silent.vbs)，服务与隧道将在后台静默常驻，无 CMD 黑框。
- **一键停止**：双击根目录下的 [`stop.bat`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/stop.bat)，安全关闭 28000 服务进程与隧道。
- **开机自启**：已在系统自启目录配置了快捷方式，电脑重启登录后将自动静默恢复服务与隧道。
