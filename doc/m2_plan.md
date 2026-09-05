# 里程碑 M2：OCR 识别接入与拍照录题流水线 实施方案

## 1. 目标与范围

在 M1 已交付的核心闭环（作业打卡、连续打卡、艾宾浩斯复习、数据备份）基础上，落地 M2 核心能力：
1. **可插拔三引擎 OCR 抽象层**（默认 `RapidOCR`，备选 `PaddleOCR`，兜底 `CloudVLM`）。
2. **非阻塞异步任务队列**：图片上传即返回 `task_id`，线程池异步推理，前端轮询进度，避免大图推理阻塞移动端交互。
3. **前端骨架屏与可编辑确认交互**：
   - 作业打卡页：支持拍照/相册批量识别，结果填充至多行文本框，支持按行拆分批量创建作业。
   - 错题录入页：错题照片一键 OCR 提取文字题干，支持随时人工修正或放弃，杜绝产生脏数据。
4. **初中试卷样本集与自动化基准测试**：在 `tests/samples/` 预置典型初中题干样本，验证推理速度 ≤ 2s 与印刷体字符识别率 ≥ 95%。
5. **降级与环境守卫**：RapidOCR 无法使用时平滑提示并支持纯手工输入；云端 Key 隔离保护不进前端与 Git。

---

## 2. 详细设计与代码组织

### 2.1 后端模块架构

```
backend/app/
├── utils/
│   ├── ocr_service.py        # [NEW] 可插拔 OCR 引擎抽象类、RapidOCR/PaddleOCR/Cloud 引擎实现与降级探测
│   └── image_handler.py      # [EXISTING] 图片落盘、sha256 去重与缩略图
├── routers/
│   └── ocr.py                # [NEW] 异步任务 API (/api/ocr/tasks, /api/ocr/tasks/{id}, /api/ocr/engines)
├── schemas.py                # [MODIFY] 补充 OCR 任务输出与引擎状态 Pydantic 规范
└── main.py                   # [MODIFY] 挂载 ocr 路由
```

#### A. 抽象引擎接口 `ocr_service.py`
```python
@dataclass
class OcrLine:
    text: str
    confidence: float
    box: list[list[int]]

@dataclass
class OcrResult:
    lines: list[OcrLine]
    text: str
    confidence: float
    engine: str
    cost_ms: int

class BaseOCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: str | Path) -> OcrResult:
        pass
```
* **`RapidOCREngine`（默认）**：
  * 单例惰性初始化 `RapidOCR()`，利用现已装好的 `rapidocr-onnxruntime` + `onnxruntime 1.29`。
  * 纯 CPU 推理，模型已内置包内，**首次运行 100% 零联网**。
* **`PaddleOCREngine`（用户指定可选退路）**：
  * 动态 `import paddleocr`，未安装时抛出可用性检测异常，平滑降级。
* **`CloudVLMEngine`（云端大模型视觉备选）**：
  * 支持智谱 `glm-4v-flash`（永久免费）或通用 OpenAI 兼容视觉 API，读取 `data/.env` 或配置中环境变量。
* **`get_ocr_engine(mode="auto")` 降级工厂**：
  * 模式 `auto`：按 `RapidOCR -> PaddleOCR -> CloudVLM (若配置了Key) -> ManualFallback` 自动探测。

#### B. 异步任务队列 `routers/ocr.py`
* 采用 Python 标准库 `concurrent.futures.ThreadPoolExecutor`，最大并发线程 2（保护宿主机 CPU 占用）。
* 内存任务字典 `TASK_CACHE: dict[str, TaskInfo]`，记录 `status` (`pending` | `processing` | `succeeded` | `failed`)、`progress`、`result` 与 `created_at`（带 1 小时过期清理）。
* 接口定义：
  1. `POST /api/ocr/tasks`：接收上传图片（Form File）或已有图片路径，保存临时/原图，分配 UUID `task_id`，立即返回 `202 Accepted`。
  2. `GET /api/ocr/tasks/{task_id}`：轮询状态，完成后返回结构化识别文本与耗时。
  3. `GET /api/ocr/engines`：返回各引擎可用状态与当前默认引擎。

---

### 2.2 前端交互设计

```
frontend/src/
├── components/
│   └── QuickAddModal.vue     # [NEW] 拍照/文字作业快速录入弹窗（带骨架屏与多行拆分）
├── views/
│   ├── HomeworkView.vue      # [MODIFY] 引入 QuickAddModal，支持一键拍照录入作业
│   └── MistakeView.vue       # [MODIFY] 错题录入弹窗支持选图后“一键识别题干”并回填
└── api/
    └── index.js              # [MODIFY] 补充 ocrApi 接口封装
```

1. **`QuickAddModal.vue`**：
   - 顶部提供“手动输入”与“拍照识别”切换标签。
   - 拍照/选图后立即发起异步任务，展示 Vant `<van-skeleton>` 骨架屏 + “正在识别题干，耗时约 0.5~1.5s” 动效。
   - 识别完成后将结果填入可编辑的 `<van-field type="textarea">`。
   - 提供“按换行拆分作业”实时预览：孩子/家长可微调文字，点击“批量添加”一次性落入作业清单。
   - 支持取消/放弃，放弃时不残留任何临时作业或无用记录。

2. **`MistakeView.vue`**：
   - 在已有的错题录入弹窗中，上传图片后显示 `[🔍 一键提取题干]` 快捷按钮。
   - 点击后异步调用 OCR，将文字自动回填至“题干文字”文本框，保留全量人工微调能力。

---

### 2.3 样本集与自动化测试设计

1. **`tests/samples/` 基准样本**：
   - 编写 `generate_test_samples.py`，使用 PIL 预生成 3 种典型初中题干印刷体样本图片：
     * 语文/英语：纯文本印刷体题干。
     * 数学：一元一次方程、整式运算题干。
     * 综合：包含题号、小题与填空下划线的标准题目。
2. **自动化测试 `tests/test_m2_ocr.py`**：
   - `test_rapid_ocr_direct`：直接测试 RapidOCR 引擎识别准确度（文字召回率与相似度匹配）。
   - `test_ocr_async_pipeline`：测试 `POST /api/ocr/tasks` -> 轮询 `GET /api/ocr/tasks/{id}` 的全链路。
   - `test_ocr_engine_fallback`：测试非法/不可用引擎时的安全捕获与优雅降级。
   - `test_task_cancellation_or_missing`：测试查询不存在的任务 ID 时返回标准 404。
3. **基准报告与安装指引**：
   - `doc/ocr_benchmark.md`：记录 CPU 推理实测耗时、字符正确率、内存占用。
   - `doc/ocr_setup.md`：记录 PaddleOCR 与云端 Key 的可选配置说明。
   - `scripts/install_ocr.py`：环境自检与备用引擎安装检测脚本。

---

## 3. 约束遵守与安全策略

1. **宿主环境纯净度**：
   - 严格在 `study_trace/.venv` 内运行，严禁修改全局 Python 3.9 或 Node 14。
2. **Git 洁癖**：
   - 临时生成的 OCR 缓存图片存放于 `data/uploads/` 或系统级内存流，不产生未受控的本地文件。
3. **零联网隐患**：
   - RapidOCR 模型已本地就绪，推理过程 100% 离线运行。

---

## 4. 实施与验证步骤

1. **第 1 步：后端 OCR 核心服务**
   - 新增 `backend/app/utils/ocr_service.py`。
   - 扩展 `backend/app/schemas.py` 增加 OCR 模式。
   - 新增 `backend/app/routers/ocr.py` 路由并注册进 `main.py`。
2. **第 2 步：测试样本与自动化测试**
   - 创建 `tests/samples/` 并编写测试用例 `tests/test_m2_ocr.py`。
   - 执行 `uv run pytest tests/test_m2_ocr.py` 验证 100% 通过。
3. **第 3 步：前端录入组件与双视图联动**
   - 更新 `frontend/src/api/index.js` 添加 `ocrApi`。
   - 新建 `frontend/src/components/QuickAddModal.vue`。
   - 改造 `frontend/src/views/HomeworkView.vue` 与 `frontend/src/views/MistakeView.vue`。
   - 执行前端生产打包 `npm run build` 确保无编译报错。
4. **第 4 步：文档与基准输出**
   - 编写 `scripts/install_ocr.py`。
   - 输出 `doc/ocr_benchmark.md` 实测数据与 `doc/ocr_setup.md`。
   - 检查 `git status` 确保无未跟踪脏文件，打 `m2-done` 标签并推送到 GitHub。
