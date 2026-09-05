# M2 OCR 配置与可选引擎接入指南

默认引擎 **RapidOCR** 已随项目依赖（`pyproject.toml` 中 `rapidocr-onnxruntime>=1.3.24`）安装，**零配置、零联网**即可使用。本文件仅说明两个可选引擎的启用方式。

---

## 一、PaddleOCR（可选退路，本地）

仅在 RapidOCR 不满足需求时启用。注意：paddlepaddle 依赖约 1GB，安装失败率较高，且首次运行需联网下载模型。

```bash
# 在 .venv 内安装（不影响系统 Python 3.9）
uv pip install paddleocr

# 自检
python scripts/install_ocr.py
```

启用后无需改代码：`get_ocr_engine("auto")` 会在 RapidOCR 不可用时自动探测 PaddleOCR。
如需强制使用：`POST /api/ocr/tasks` 时传 `mode=paddle`。

> ⚠️ 当前本机**未安装** PaddleOCR，`/api/ocr/engines` 会将其标记为 `not_installed`，属正常。

---

## 二、CloudVLM（云端大模型兜底，需联网 + Key）

用于 RapidOCR 识别不准的复杂公式/手写场景。支持智谱 `glm-4v-flash`（永久免费档）或任意 OpenAI 兼容视觉接口。

### 1. 配置 Key（绝不进 Git / 绝不下发前端）

在 `data/.env` 中配置（该文件已被 `.gitignore` 忽略）：

```env
# 智谱 GLM-4V-Flash（默认，永久免费）
OCR_CLOUD_API_KEY=你的_zhipu_api_key
OCR_CLOUD_BASE_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
OCR_CLOUD_MODEL=glm-4v-flash

# 或改用其他 OpenAI 兼容视觉模型（如硅基流动 PaddleOCR-VL）
# OCR_CLOUD_API_KEY=xxx
# OCR_CLOUD_BASE_URL=https://api.siliconflow.cn/v1/chat/completions
# OCR_CLOUD_MODEL=PAI-PaddleOCR-VL
```

也可改用环境变量（同等优先级）：
```bash
export OCR_CLOUD_API_KEY=你的_key
```

### 2. 验证

```bash
python scripts/install_ocr.py   # CloudVLM 应显示「✅ 已配置 Key」
```

### 3. 使用

- 自动模式：`mode=auto` 下，仅当 RapidOCR 可用时默认走本地；若希望优先/强制云端，传 `mode=cloud`。
- 前端目前默认 `mode=auto`（本地优先），云端作为兜底在本地失败时自动尝试（需已配置 Key）。

> 安全说明：Key 仅存于服务端 `data/.env`，CloudVLM 调用发生在后端，前端与 Git 均不接触。

---

## 三、自检脚本

```bash
python scripts/install_ocr.py
```

退出码 `0` = RapidOCR 可用（满足 M2 最低要求）；`1` = 全部不可用（应用仍可运行，识别功能引导手动输入）。
