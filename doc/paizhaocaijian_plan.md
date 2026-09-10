# 拍照后框选裁剪功能实现方案

## 背景

用户拍照录入作业或错题时，照片中往往包含整页试卷，但实际只需识别其中某一道题。需要在拍照/选择图片后、上传/OCR 之前，增加一个**可拖拽矩形框选裁剪**步骤，让用户精准选定识别区域，提高 OCR 识别准确率。

## 涉及的两个入口

| 入口 | 文件 | 当前流程 |
|------|------|----------|
| 错题录入 | [`MistakeView.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/MistakeView.vue) | `van-uploader` → `handleUpload()` → 压缩 → 直接上传后端 → 点击"智能提取题干"做 OCR |
| 作业拍照识别 | [`QuickAddModal.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/components/QuickAddModal.vue) | `van-uploader` → `onOcrUpload()` → 压缩 → 直接提交 OCR 任务 |

## Proposed Changes

### 核心裁剪组件

#### [MODIFY] [`ImageCropper.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/components/ImageCropper.vue)

完全重写现有骨架组件，实现完整的移动端图片裁剪功能：

**功能要素：**
- **全屏遮罩弹窗**：使用 `van-popup` 全屏覆盖，深色背景，沉浸式裁剪体验
- **图片展示**：居中展示原图，支持 pinch-to-zoom（双指缩放）
- **可拖拽裁剪框**：
  - 半透明蓝色边框矩形，外部区域暗化遮罩（`box-shadow: 0 0 0 9999px rgba(0,0,0,0.5)`）
  - **移动**：触摸裁剪框内部可拖动位置
  - **缩放**：四角 + 四边各一个拖拽手柄，触摸可调整裁剪区域大小
  - 最小裁剪尺寸限制（50×50px），防止误操作
- **底部操作栏**：
  - "取消"按钮（关闭弹窗，不裁剪）
  - "跳过裁剪"按钮（使用原图）
  - "确认裁剪"按钮（Canvas 导出裁剪区域为 Blob）
- **Canvas 裁剪**：使用 `drawImage(img, sx, sy, sw, sh, 0, 0, dw, dh)` 精确切取选定区域，输出 JPEG Blob

**技术细节：**
- 纯 Canvas + 触摸事件实现，**零第三方依赖**，保持项目轻量
- 支持 mouse 事件（桌面调试）和 touch 事件（移动端真机）
- Props：`imageUrl`（base64/blob URL）、`show`（控制弹窗显隐）
- Emits：`confirm(croppedBlob, croppedUrl)` / `skip(originalFile)` / `cancel()`

---

### 错题录入集成

#### [MODIFY] [`MistakeView.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/views/MistakeView.vue)

修改 `handleUpload` 流程：

```
原流程：选择图片 → 压缩 → 直接上传
新流程：选择图片 → 弹出裁剪弹窗 → 用户裁剪/跳过 → 压缩 → 上传
```

具体改动：
1. 引入 `ImageCropper` 组件
2. 新增 `showCropper` / `cropperImageUrl` / `pendingUploadFile` 响应式变量
3. `handleUpload` 改为：读取图片 → 设置 `cropperImageUrl` → 打开裁剪弹窗
4. 新增 `onCropConfirm(blob)` 回调：接收裁剪后的 Blob → 压缩 → 上传后端
5. 新增 `onCropSkip()` 回调：使用原图继续上传流程

---

### 作业拍照识别集成

#### [MODIFY] [`QuickAddModal.vue`](file:///d:/工作/ww/personal_work/study_trace/frontend/src/components/QuickAddModal.vue)

修改 `onOcrUpload` 流程：

```
原流程：拍照/选图 → 压缩 → 直接提交 OCR
新流程：拍照/选图 → 弹出裁剪弹窗 → 用户裁剪/跳过 → 压缩 → 提交 OCR
```

具体改动：
1. 引入 `ImageCropper` 组件
2. 新增裁剪相关状态变量
3. `onOcrUpload` 改为：读取图片 → 打开裁剪弹窗
4. 新增 `onCropConfirm` / `onCropSkip` 回调，在裁剪完成后继续原有 OCR 流程

## 不需要改动的地方

- **后端完全不需要改动**：裁剪在前端 Canvas 完成，后端收到的仍然是标准图片文件
- **`imageCompress.js`**：裁剪输出的 Blob 可直接转为 File 对象传入现有压缩函数
- **OCR 路由**：无影响

## Verification Plan

### 构建验证
```bash
cd frontend && npm run build
```

### 手动验证
1. 错题录入：点击上传图片 → 验证裁剪弹窗弹出 → 拖拽裁剪框 → 确认裁剪 → 验证裁剪后图片正确上传
2. 作业拍照：切换到拍照识别 → 选择图片 → 裁剪 → 验证 OCR 识别结果准确
3. 跳过裁剪：验证"跳过裁剪"按钮正确使用原图
4. 取消裁剪：验证取消后回到上传前状态
