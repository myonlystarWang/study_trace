# 智学迹 StudyTrace 灾备与换机快速重建手册 (Disaster Recovery Guide)

> **适用场景**：电脑故障崩溃、重装 Windows 系统、迁移至全新开发/家庭服务器主机。  
> 本手册指导如何在全新环境中快速拉起并还原 StudyTrace 的全部服务与数据。

---

## 1. 资产与数据备份说明

在发生电脑崩溃或迁移前，请明确系统核心数据的物理存放位置：

| 资产类型 | 物理路径 | 是否在 Git 仓库内 | 备份与还原策略 |
| :--- | :--- | :---: | :--- |
| **全量源代码与文档** | 整个仓库（含前端、后端、脚本） | **是** | `git clone` 或 `git pull` 即可 100% 还原 |
| **孩子错题核心数据库** | `data/study_trace.db` | **是** | 包含所有文字错题、标签、答题记录、艾宾浩斯掌握度与组卷历史，已纳入 Git |
| **错题原图与切片** | `data/uploads/` (约 46MB+) | **否 (不进 Git)** | **需冷备**：定期将该文件夹压缩或同步至百度网盘 / OneDrive / 移动硬盘 |
| **环境与接入密钥** | `data/.env` | **否 (敏感密钥)** | 换机时参考根目录 `.env.example` 重新填入，或密码管理器中留存备份 |
| **Cloudflare 隧道凭证** | `config/cloudflared/*.json` | **否 (敏感证书)** | 若丢失，在 Cloudflare 控制台重新生成或重新绑定 `cloudflared tunnel login` |

---

## 2. 全新机器环境基础依赖准备

在全新 Windows 电脑上，请依次安装以下运行时与基础工具：

1. **Python 3.11**：
   - 官方指定必须使用 **Python 3.11.x**（严禁盲目安装 3.12 或 3.13，避免 Paddle/RapidOCR 兼容性问题）。
   - 建议安装并配置独立的 `uv` 工具进行快速虚拟环境管理。
2. **Node.js 22 LTS**：
   - 推荐使用 `fnm` 安装管理：`fnm install 22`、`fnm use 22`。
3. **NSSM (Non-Sucking Service Manager)**：
   - Windows 后台服务托管工具，建议解压放置于 `C:\tools\nssm\nssm.exe`。
4. **Cloudflared (若需公网隧道访问)**：
   - 下载 `cloudflared.exe` 放置于系统 PATH 或 `C:\Program Files (x86)\cloudflared\`。

---

## 3. 从零拉取与初始化构建

### 步骤 3.1：克隆代码仓库
```bash
git clone git@github.com:myonlystarWang/study_trace.git
cd study_trace
```

### 步骤 3.2：还原环境变量配置
复制模版并填入个人真实密钥：
```bash
copy .env.example data\.env
# 使用文本编辑器编辑 data\.env，填入微信、大模型等 API 凭据
```

### 步骤 3.3：还原错题图片（若有备份）
将冷备份保存的 `uploads` 文件夹完整拷贝至 `data/uploads/`：
```
data/
  ├── uploads/
  │    ├── originals/
  │    └── thumbnails/
  └── study_trace.db  (已随 Git 仓库自动带齐)
```

### 步骤 3.4：初始化 Python 虚拟环境与依赖
```powershell
# 创建 Python 3.11 虚拟环境
uv venv .venv --python 3.11
# 安装后端运行时与所有依赖
uv pip install -e .
```

### 步骤 3.5：构建前端静态页面
```powershell
cd frontend
npm install
npm run build
cd ..
```

### 步骤 3.6：验证数据库与执行迁移
系统在启动时会自动校验 Alembic，但亦可手动执行黑盒验证：
```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

### 步骤 3.7：运行自动化测试套件
确保新主机上所有单元与集成测试均通过：
```powershell
.venv\Scripts\python.exe -m pytest
```

---

## 4. 后台守护服务（NSSM）一键注册

当测试通过后，即可一键注册 Windows 后台自启服务：

1. 右键以管理员身份运行项目根目录下的 **`fix_service.bat`**。
2. 脚本将自动完成以下流程：
   - 自检 `.venv\Scripts\python.exe` 与 `C:\tools\nssm\nssm.exe`；
   - 释放 28000 端口旧占用；
   - 注册 `StudyTrace` 为开机自启动服务（指向 `run.py` 生产模式）；
   - 配置标准输出和错误日志流（`data/studytrace-stdout.log` / `data/studytrace-stderr.log`）；
   - 自动启动服务并输出当前状态。
3. 若显示 `SERVICE_RUNNING`，即可在浏览器或手机内网访问：`http://127.0.0.1:28000`。

---

## 5. 日常冷备份建议脚本（用于保护 uploads/ 图片）

为了保护不入 Git 的原图，可每月或每季度执行以下 PowerShell 单行命令，将数据整体打包备份：

```powershell
# 压缩打包 data 目录（包含图片和数据库快照）
$date = Get-Date -Format "yyyyMMdd"
Compress-Archive -Path "data\study_trace.db", "data\uploads" -DestinationPath "D:\StudyTrace_Data_Backup_$date.zip"
```
生成 zip 后直接拷入 U 盘或拖入网盘，即可确保数据绝对零丢失。
