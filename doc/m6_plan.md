# M6 部署上线技术实施方案

基于 [`doc/deployment_audit.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/deployment_audit.md) 审计报告与 [`doc/m6_deployment.md`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/doc/m6_deployment.md) 执行手册，以及双方在 `/grill-me` 讨论中确定的关键决策，开展 M6 部署上线。

## 核心决议汇总

| 项 | 确认决议 | 说明 |
| :--- | :--- | :--- |
| **宿主机器** | **当前出差笔记本（未来常驻公司机）** | 在此机器完整落地；文案保留「公司机/公司笔记本」；老公司机服务停掉防数据分叉 |
| **端口规划** | **生产 28000 / 开发 28001** | 替换原 8000 端口，避开常见端口；前后端 Vite 与代理同步适配，支持边服务边开发 |
| **安全加固** | **阶段 0 必做先于公网暴露** | 保护 `/api/backup/export` 与 `import`（401门禁）；保持孩子端免密打卡；强制修改初始 PIN 888888；SECRET_KEY 随机化写入 `data/.env`；生产模式收紧 CORS |
| **隧道域名** | **`study.raddishlab.tech`** | Cloudflare 托管域名 `raddishlab.tech`；映射 `http://127.0.0.1:28000` |
| **守护模式** | **Windows 任务计划程序 + `start-silent.vbs`** | 原生免第三方依赖，后台静默启动无黑框；`powercfg` 彻底关闭接电休眠与合盖睡眠 |

---

## 实施阶段与变更范围

### 阶段 0 · 安全加固与大端口隔离（纯代码与本地验证）

#### 1. 端口与跨域收紧
- [MODIFY] [`backend/app/config.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/backend/app/config.py)
  - 默认生产端口由 `8000` 改为 `28000`
  - `SECRET_KEY` 检测逻辑：启动时若 `data/.env` 中未定义 `SECRET_KEY`，动态生成 32 字节高强度随机密钥并写入 `data/.env`，不再写死进 Git
  - 增加生产允许域名配置：`ALLOWED_ORIGINS = ["https://study.raddishlab.tech", "http://127.0.0.1:28000", "http://localhost:28000"]`
- [MODIFY] [`backend/app/main.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/backend/app/main.py)
  - CORS 中间件在生产环境采用受限的 `ALLOWED_ORIGINS`，开发环境保持宽松调试
- [MODIFY] [`run.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/run.py)
  - 生产模式 `run_prod()` 绑定 `port=28000`
  - 开发模式 `run_dev()` 后端绑定 `port=28001`，同时环境变量或传参通知 Vite
- [MODIFY] [`frontend/vite.config.js`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/frontend/vite.config.js)
  - 开发代理目标端口改为 `http://127.0.0.1:28001`

#### 2. 敏感备份接口安全门禁
- [MODIFY] [`backend/app/routers/backup.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/backend/app/routers/backup.py)
  - 为 `/api/backup/export` 加上 `Depends(require_parent_pin)`
  - 为 `/api/backup/import` 加上 `Depends(require_parent_pin)`
  - 防止公网暴露后任意匿名人员直接 GET 下载全量数据库与作业图片，或 POST 恶意覆盖系统

#### 3. 初始 PIN 888888 强制修改防线
- [MODIFY] [`backend/app/routers/settings.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/backend/app/routers/settings.py) 与 [`backend/app/auth.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/backend/app/auth.py)
  - 增加对家长端当前 PIN 是否为默认 `888888` 的检查逻辑
- [MODIFY] 前端家长入口与设置组件
  - 进入家长空间时，若检测到仍是默认 PIN，强制弹出修改密码对话框，未修改前拦截敏感操作

#### 4. 自动化测试补全
- [NEW] [`tests/test_m6_security.py`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/tests/test_m6_security.py)
  - 验证未带 PIN / 错误 PIN 请求 `/api/backup/export` 严格返回 401
  - 验证携带正确 PIN 请求 `/api/backup/export` 返回 200 且数据完整
  - 验证孩子端日常 `/api/homework` 与 `/api/mistakes` 仍支持免密打卡输入

---

### 阶段 1 · Cloudflare 命名隧道部署

1. **环境安装与登录**
   - 检查或通过 `winget install --id Cloudflare.cloudflared` 安装 `cloudflared`
   - 执行 `cloudflared tunnel login`，在浏览器弹出授权页面中选择 `raddishlab.tech`
2. **创建隧道与配置**
   - 执行 `cloudflared tunnel create study-trace`，获取 Tunnel UUID
   - 在 `%USERPROFILE%\.cloudflared\config.yml` 写入映射规则：
     ```yaml
     tunnel: <Tunnel-UUID>
     credentials-file: C:\Users\<用户名>\.cloudflared\<Tunnel-UUID>.json

     ingress:
       - hostname: study.raddishlab.tech
         service: http://127.0.0.1:28000
       - service: http_status:404
     ```
3. **路由 DNS 与服务常驻**
   - 执行 `cloudflared tunnel route dns study-trace study.raddishlab.tech`
   - 执行 `cloudflared service install` 注册为 Windows 系统后台服务，实现开机自启与断网自愈

---

### 阶段 2 · 常开电源配置与静默守护

1. **电源策略固化**
   - 执行 `powercfg` 命令彻底关闭接电状态下的待机、休眠和合盖睡眠：
     ```powershell
     powercfg /change standby-timeout-ac 0
     powercfg /change hibernate-timeout-ac 0
     powercfg /change monitor-timeout-ac 0
     powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
     powercfg /setactive SCHEME_CURRENT
     ```
2. **后台静默启动器与任务计划**
   - [NEW] [`start-silent.vbs`](file:///d:/%E5%B7%A5%E4%BD%9C/ww/personal_work/study_trace/start-silent.vbs)：使用 `WScript.Shell.Run` 隐藏窗口启动 `uv run python run.py`
   - 通过 `schtasks` 创建最高权限开机登录计划任务：
     ```powershell
     schtasks /create /tn "StudyTrace" /tr "wscript.exe D:\工作\ww\personal_work\study_trace\start-silent.vbs" /sc onlogon /rl highest /f
     ```
3. **健康检查端点验证**
   - 验证 `http://127.0.0.1:28000/api/health` 正常返回，并供外部存活探针（UptimeRobot 或 Cloudflare Health Check）接入

---

### 阶段 3 · 真机验收（iPhone 手机全闭环）

1. **外网与安全**：iPhone 断开 WiFi，使用蜂窝网络访问 `https://study.raddishlab.tech`，验证 2s 内首屏加载无证书警告
2. **PWA 体验**：添加到 Safari 主屏幕，验证全屏独立 App 模式运行
3. **业务全闭环**：在手机上执行一次「录入作业 -> 打卡 -> 拍照错题 -> OCR -> 组卷」完整链路
4. **断网重连**：模拟断网 5 分钟，恢复网络后验证隧道自动重连，无需人工干预

---

### 阶段 4 · 文档与交付固化

1. 回填 `doc/m6_deployment.md` 中的「7.1 实施记录」（版本号、Tunnel UUID、日期）
2. 更新 `README.md`，补充「外网固定域名访问（Cloudflare Tunnel）」部署与迁移说明
3. 登记 `doc/change_log.md` 发布 v1.7.0（M6 部署上线）
4. 通过 SSH 协议推送至 GitHub 远端仓库：`git push origin master`

---

## 验证与验收方案

### 自动化测试
```powershell
uv run pytest tests/test_m6_security.py -v
uv run pytest -v
```
确保全量测试套件 100% 通过（新增门禁测试且无回归）。

### 手动与真机验证
1. 启动生产服务，验证本机访问 `http://127.0.0.1:28000` 正常，`run.py --dev` 访问 `28001` 正常。
2. 未带 PIN 访问 `http://127.0.0.1:28000/api/backup/export`，实测返回 HTTP 401 Unauthorized。
3. 蜂窝网络访问 `https://study.raddishlab.tech/api/health`，验证返回 `{"status":"ok",...}`。
