<template>
  <van-popup
    :show="show"
    position="bottom"
    class="cropper-popup"
    :style="{ height: '100%', width: '100%', maxHeight: '100%' }"
    :close-on-click-overlay="false"
    teleport="body"
  >
    <div class="cropper-wrapper">
      <!-- 顶部操作栏 -->
      <div class="cropper-header">
        <button class="header-action-btn" @click="handleCancel">
          <van-icon name="cross" /> 取消
        </button>
        <span class="header-title">框选裁剪题目</span>
        <button class="header-action-btn text-btn" @click="handleSkip">
          跳过裁剪
        </button>
      </div>

      <!-- 裁剪核心可视区 -->
      <div class="cropper-stage" ref="stageRef">
        <div
          class="canvas-container"
          ref="containerRef"
          :style="containerStyle"
          @mousedown.self="onBgStart"
          @touchstart.self="onBgStart"
        >
          <!-- 真实渲染的底层图片 -->
          <img
            ref="imageRef"
            :src="imageUrl"
            alt="待裁剪图像"
            class="source-image"
            @load="onImageLoaded"
            draggable="false"
          />

          <!-- 裁剪选框 (只有在图片准备好后显示) -->
          <div
            v-if="isReady"
            class="crop-box"
            :style="cropBoxStyle"
            @mousedown.stop="startDragMove"
            @touchstart.stop="startDragMove"
          >
            <!-- 9宫格网格线 -->
            <div class="crop-grid-line line-h-1"></div>
            <div class="crop-grid-line line-h-2"></div>
            <div class="crop-grid-line line-v-1"></div>
            <div class="crop-grid-line line-v-2"></div>

            <!-- 提示标签 -->
            <div class="crop-drag-hint">拖动选区或调整边框</div>

            <!-- 8个调整锚点 (4角 + 4边中点) -->
            <div class="handle handle-tl" @mousedown.stop="startResize($event, 'tl')" @touchstart.stop="startResize($event, 'tl')"></div>
            <div class="handle handle-tr" @mousedown.stop="startResize($event, 'tr')" @touchstart.stop="startResize($event, 'tr')"></div>
            <div class="handle handle-bl" @mousedown.stop="startResize($event, 'bl')" @touchstart.stop="startResize($event, 'bl')"></div>
            <div class="handle handle-br" @mousedown.stop="startResize($event, 'br')" @touchstart.stop="startResize($event, 'br')"></div>
            <div class="handle handle-tm" @mousedown.stop="startResize($event, 'tm')" @touchstart.stop="startResize($event, 'tm')"></div>
            <div class="handle handle-bm" @mousedown.stop="startResize($event, 'bm')" @touchstart.stop="startResize($event, 'bm')"></div>
            <div class="handle handle-ml" @mousedown.stop="startResize($event, 'ml')" @touchstart.stop="startResize($event, 'ml')"></div>
            <div class="handle handle-mr" @mousedown.stop="startResize($event, 'mr')" @touchstart.stop="startResize($event, 'mr')"></div>
          </div>
        </div>
      </div>

      <!-- 底部操作提示与确定按钮 -->
      <div class="cropper-footer">
        <div class="footer-tip">
          <van-icon name="info-o" />
          <span>拖拽四周手柄框选要识别的题目，排除试卷其余无关干扰</span>
        </div>
        <div class="footer-actions">
          <van-button
            type="primary"
            round
            block
            icon="success"
            :loading="isCropping"
            loading-text="正在剪裁..."
            @click="confirmCrop"
            class="crop-confirm-btn"
          >
            确认框选区域并识别
          </van-button>
        </div>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount, nextTick } from 'vue';
import { showToast } from 'vant';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  imageUrl: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:show', 'crop', 'skip', 'cancel']);

const stageRef = ref(null);
const containerRef = ref(null);
const imageRef = ref(null);
const isReady = ref(false);
const isCropping = ref(false);

// 图片在舞台中的渲染尺寸与自然尺寸
const imgMeta = reactive({
  naturalWidth: 0,
  naturalHeight: 0,
  displayLeft: 0,
  displayTop: 0,
  displayWidth: 0,
  displayHeight: 0
});

// 选框相对于 container 的像素位置及大小
const box = reactive({
  x: 20,
  y: 20,
  w: 200,
  h: 200
});

const containerStyle = computed(() => ({
  width: `${imgMeta.displayWidth}px`,
  height: `${imgMeta.displayHeight}px`
}));

const cropBoxStyle = computed(() => ({
  left: `${box.x}px`,
  top: `${box.y}px`,
  width: `${box.w}px`,
  height: `${box.h}px`
}));

// 计算并对齐图片在可视舞台中的适配尺寸
const computeLayout = () => {
  if (!stageRef.value || !imgMeta.naturalWidth || !imgMeta.naturalHeight) return;
  const stageRect = stageRef.value.getBoundingClientRect();
  const sw = stageRect.width - 24; // 留适当边距
  const sh = stageRect.height - 24;

  const aspect = imgMeta.naturalWidth / imgMeta.naturalHeight;
  let dw = sw;
  let dh = dw / aspect;

  if (dh > sh) {
    dh = sh;
    dw = dh * aspect;
  }

  imgMeta.displayWidth = Math.round(dw);
  imgMeta.displayHeight = Math.round(dh);

  // 初始化裁剪框（默认居中占用宽高的 80%）
  const initW = Math.round(dw * 0.85);
  const initH = Math.round(dh * 0.6);
  box.w = Math.max(80, Math.min(initW, dw));
  box.h = Math.max(80, Math.min(initH, dh));
  box.x = Math.round((dw - box.w) / 2);
  box.y = Math.round((dh - box.h) / 2);

  isReady.value = true;
};

const onImageLoaded = (e) => {
  const img = e.target;
  imgMeta.naturalWidth = img.naturalWidth || 1;
  imgMeta.naturalHeight = img.naturalHeight || 1;
  nextTick(() => {
    computeLayout();
  });
};

// 交互逻辑：移动与缩放
let dragMode = null; // 'move' | 'tl' | 'tr' | 'bl' | 'br' | 'tm' | 'bm' | 'ml' | 'mr'
let startPointer = { x: 0, y: 0 };
let startBox = { x: 0, y: 0, w: 0, h: 0 };

const getPointerPos = (e) => {
  if (e.touches && e.touches.length > 0) {
    return { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }
  return { x: e.clientX, y: e.clientY };
};

const startDragMove = (e) => {
  dragMode = 'move';
  initDragState(e);
};

const startResize = (e, handleType) => {
  dragMode = handleType;
  initDragState(e);
};

const onBgStart = () => {
  // 点击空白不做动作
};

const initDragState = (e) => {
  const pos = getPointerPos(e);
  startPointer = { x: pos.x, y: pos.y };
  startBox = { x: box.x, y: box.y, w: box.w, h: box.h };

  window.addEventListener('mousemove', onPointerMove, { passive: false });
  window.addEventListener('mouseup', onPointerEnd);
  window.addEventListener('touchmove', onPointerMove, { passive: false });
  window.addEventListener('touchend', onPointerEnd);
};

const MIN_SIZE = 50;

const onPointerMove = (e) => {
  if (!dragMode) return;
  e.preventDefault?.(); // 阻止移动端橡皮筋滚动

  const pos = getPointerPos(e);
  const dx = pos.x - startPointer.x;
  const dy = pos.y - startPointer.y;

  const maxW = imgMeta.displayWidth;
  const maxH = imgMeta.displayHeight;

  if (dragMode === 'move') {
    let nx = startBox.x + dx;
    let ny = startBox.y + dy;
    nx = Math.max(0, Math.min(nx, maxW - startBox.w));
    ny = Math.max(0, Math.min(ny, maxH - startBox.h));
    box.x = nx;
    box.y = ny;
    return;
  }

  // 8向缩放计算
  let newX = startBox.x;
  let newY = startBox.y;
  let newW = startBox.w;
  let newH = startBox.h;

  if (dragMode.includes('r')) {
    newW = Math.max(MIN_SIZE, Math.min(startBox.w + dx, maxW - startBox.x));
  }
  if (dragMode.includes('l')) {
    const clampDx = Math.max(-startBox.x, Math.min(dx, startBox.w - MIN_SIZE));
    newX = startBox.x + clampDx;
    newW = startBox.w - clampDx;
  }
  if (dragMode.includes('b')) {
    newH = Math.max(MIN_SIZE, Math.min(startBox.h + dy, maxH - startBox.y));
  }
  if (dragMode.includes('t')) {
    const clampDy = Math.max(-startBox.y, Math.min(dy, startBox.h - MIN_SIZE));
    newY = startBox.y + clampDy;
    newH = startBox.h - clampDy;
  }

  box.x = Math.round(newX);
  box.y = Math.round(newY);
  box.w = Math.round(newW);
  box.h = Math.round(newH);
};

const onPointerEnd = () => {
  dragMode = null;
  window.removeEventListener('mousemove', onPointerMove);
  window.removeEventListener('mouseup', onPointerEnd);
  window.removeEventListener('touchmove', onPointerMove);
  window.removeEventListener('touchend', onPointerEnd);
};

onBeforeUnmount(() => {
  onPointerEnd();
});

// 执行裁剪
const confirmCrop = async () => {
  if (!imageRef.value || !isReady.value) return;

  isCropping.value = true;
  try {
    const scaleX = imgMeta.naturalWidth / imgMeta.displayWidth;
    const scaleY = imgMeta.naturalHeight / imgMeta.displayHeight;

    const cropX = Math.max(0, Math.round(box.x * scaleX));
    const cropY = Math.max(0, Math.round(box.y * scaleY));
    const cropW = Math.min(imgMeta.naturalWidth - cropX, Math.round(box.w * scaleX));
    const cropH = Math.min(imgMeta.naturalHeight - cropY, Math.round(box.h * scaleY));

    if (cropW <= 10 || cropH <= 10) {
      showToast('选框太小，请重新框选');
      isCropping.value = false;
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = cropW;
    canvas.height = cropH;
    const ctx = canvas.getContext('2d');

    const sourceImg = new Image();
    sourceImg.crossOrigin = 'anonymous';

    await new Promise((resolve, reject) => {
      sourceImg.onload = resolve;
      sourceImg.onerror = reject;
      sourceImg.src = props.imageUrl;
    });

    ctx.drawImage(sourceImg, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);

    canvas.toBlob(
      (blob) => {
        isCropping.value = false;
        if (!blob) {
          showToast('生成裁剪图片失败');
          return;
        }
        const croppedFile = new File([blob], `crop_${Date.now()}.jpg`, {
          type: 'image/jpeg',
          lastModified: Date.now()
        });
        const blobUrl = URL.createObjectURL(blob);
        emit('crop', { file: croppedFile, blobUrl, width: cropW, height: cropH });
        emit('update:show', false);
      },
      'image/jpeg',
      0.9
    );
  } catch (err) {
    isCropping.value = false;
    showToast('裁剪出错，已恢复使用原图');
    handleSkip();
  }
};

const handleSkip = () => {
  emit('skip');
  emit('update:show', false);
};

const handleCancel = () => {
  emit('cancel');
  emit('update:show', false);
};
</script>

<style scoped>
.cropper-popup {
  background-color: #0b0f19 !important;
}

.cropper-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #090d16;
  color: #fff;
  user-select: none;
  touch-action: none;
}

/* 顶部操作条 */
.cropper-header {
  height: 52px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  z-index: 10;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.header-action-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
}

.header-action-btn:active {
  opacity: 0.7;
}

.header-action-btn.text-btn {
  color: #38bdf8;
  font-weight: 500;
}

/* 舞台区 */
.cropper-stage {
  flex: 1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: radial-gradient(circle at center, #172033 0%, #090d16 100%);
  padding: 12px;
}

.canvas-container {
  position: relative;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  overflow: hidden;
}

.source-image {
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
  object-fit: fill;
}

/* 裁剪框与外围暗化遮罩 */
.crop-box {
  position: absolute;
  cursor: move;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.62);
  border: 2px solid #38bdf8;
  box-sizing: border-box;
}

/* 选框内的居中轻微提示 */
.crop-drag-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
  background: rgba(0, 0, 0, 0.45);
  padding: 2px 8px;
  border-radius: 10px;
  pointer-events: none;
  white-space: nowrap;
}

/* 9宫格网格线 */
.crop-grid-line {
  position: absolute;
  background: rgba(255, 255, 255, 0.25);
  pointer-events: none;
}
.line-h-1 {
  top: 33.33%;
  left: 0;
  width: 100%;
  height: 1px;
}
.line-h-2 {
  top: 66.66%;
  left: 0;
  width: 100%;
  height: 1px;
}
.line-v-1 {
  left: 33.33%;
  top: 0;
  width: 1px;
  height: 100%;
}
.line-v-2 {
  left: 66.66%;
  top: 0;
  width: 1px;
  height: 100%;
}

/* 四角与边缘手柄 */
.handle {
  position: absolute;
  width: 24px;
  height: 24px;
  box-sizing: border-box;
  z-index: 5;
}

/* 增加触摸手柄的命中面积 (伪元素) */
.handle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: #38bdf8;
  border: 2px solid #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}

.handle-tl {
  top: -12px;
  left: -12px;
  cursor: nwse-resize;
}
.handle-tr {
  top: -12px;
  right: -12px;
  cursor: nesw-resize;
}
.handle-bl {
  bottom: -12px;
  left: -12px;
  cursor: nesw-resize;
}
.handle-br {
  bottom: -12px;
  right: -12px;
  cursor: nwse-resize;
}

.handle-tm {
  top: -12px;
  left: calc(50% - 12px);
  cursor: ns-resize;
}
.handle-bm {
  bottom: -12px;
  left: calc(50% - 12px);
  cursor: ns-resize;
}
.handle-ml {
  top: calc(50% - 12px);
  left: -12px;
  cursor: ew-resize;
}
.handle-mr {
  top: calc(50% - 12px);
  right: -12px;
  cursor: ew-resize;
}

/* 底部操作区 */
.cropper-footer {
  flex-shrink: 0;
  background: #0f172a;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
}

.footer-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
  line-height: 1.4;
}

.footer-tip .van-icon {
  font-size: 14px;
  color: #38bdf8;
  flex-shrink: 0;
}

.crop-confirm-btn {
  font-weight: 600;
  font-size: 15px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
}
</style>
