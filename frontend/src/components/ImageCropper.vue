<template>
  <van-popup
    :show="show"
    position="bottom"
    class="cropper-popup"
    :style="{ height: '100%', width: '100%', maxHeight: '100%' }"
    :close-on-click-overlay="false"
    :lock-scroll="false"
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
        <div class="canvas-container" ref="containerRef" :style="containerStyle">
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
            @pointerdown="onBoxPointerDown"
          >
            <!-- 9宫格网格线 -->
            <div class="crop-grid-line line-h-1"></div>
            <div class="crop-grid-line line-h-2"></div>
            <div class="crop-grid-line line-v-1"></div>
            <div class="crop-grid-line line-v-2"></div>

            <!-- 提示标签 -->
            <div class="crop-drag-hint">拖动选区或调整边框</div>

            <!-- 8个调整锚点 (4角 + 4边中点) -->
            <div class="handle handle-tl" @pointerdown="onHandlePointerDown($event, 'tl')"></div>
            <div class="handle handle-tr" @pointerdown="onHandlePointerDown($event, 'tr')"></div>
            <div class="handle handle-bl" @pointerdown="onHandlePointerDown($event, 'bl')"></div>
            <div class="handle handle-br" @pointerdown="onHandlePointerDown($event, 'br')"></div>
            <div class="handle handle-tm" @pointerdown="onHandlePointerDown($event, 'tm')"></div>
            <div class="handle handle-bm" @pointerdown="onHandlePointerDown($event, 'bm')"></div>
            <div class="handle handle-ml" @pointerdown="onHandlePointerDown($event, 'ml')"></div>
            <div class="handle handle-mr" @pointerdown="onHandlePointerDown($event, 'mr')"></div>
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
import { ref, reactive, computed, onBeforeUnmount, onMounted, nextTick, watch } from 'vue';
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

const MIN_SIZE = 50;

/**
 * 计算并对齐图片在可视舞台中的适配尺寸。
 * 舞台尚未完成布局（宽高为 0）时直接返回，等 ResizeObserver / 下次可见时重算，
 * 避免算出负尺寸导致选框被夹成极小值、且拖拽时被永久锁死。
 */
const computeLayout = (resetBox = true) => {
  if (!stageRef.value || !imgMeta.naturalWidth || !imgMeta.naturalHeight) return;
  const stageRect = stageRef.value.getBoundingClientRect();
  const sw = Math.max(0, stageRect.width - 24);
  const sh = Math.max(0, stageRect.height - 24);
  if (sw < 40 || sh < 40) return;

  const aspect = imgMeta.naturalWidth / imgMeta.naturalHeight;
  let dw = sw;
  let dh = dw / aspect;
  if (dh > sh) {
    dh = sh;
    dw = dh * aspect;
  }

  imgMeta.displayWidth = Math.round(dw);
  imgMeta.displayHeight = Math.round(dh);

  if (resetBox) {
    // 初始化裁剪框（默认居中占用宽高的 85% / 60%）
    const initW = Math.round(dw * 0.85);
    const initH = Math.round(dh * 0.6);
    box.w = clamp(initW, MIN_SIZE, Math.round(dw));
    box.h = clamp(initH, MIN_SIZE, Math.round(dh));
    box.x = Math.round((dw - box.w) / 2);
    box.y = Math.round((dh - box.h) / 2);
  } else {
    // 仅重排：把现有选框夹回可视范围，保留用户已拖拽的结果
    box.w = clamp(box.w, MIN_SIZE, imgMeta.displayWidth);
    box.h = clamp(box.h, MIN_SIZE, imgMeta.displayHeight);
    box.x = clamp(box.x, 0, imgMeta.displayWidth - box.w);
    box.y = clamp(box.y, 0, imgMeta.displayHeight - box.h);
  }

  isReady.value = true;
};

const clamp = (v, min, max) => Math.min(Math.max(v, min), Math.max(min, max));

const onImageLoaded = (e) => {
  const img = e.target;
  imgMeta.naturalWidth = img.naturalWidth || 1;
  imgMeta.naturalHeight = img.naturalHeight || 1;
  nextTick(() => {
    computeLayout(true);
  });
};

// ---------------------------------------------------------------------------
// 交互逻辑：移动与缩放
//
// 关键点：这里必须用 Pointer Events，不能再用 touchstart/touchmove。
// Vant Popup 的 useLockScroll 在 document 上挂了 touchmove 监听，当弹层内容
// 不可滚动时会执行 preventDefault(event, true) —— 即 preventDefault + stopPropagation，
// 事件在 document 冒泡阶段就被掐断，window 上的 touchmove 监听永远收不到，
// 表现为「选框无法移动也无法缩小」。pointer 事件不受其影响，配合
// setPointerCapture 可稳定拿到整段手势。
// ---------------------------------------------------------------------------
let dragMode = null; // 'move' | 'tl' | 'tr' | 'bl' | 'br' | 'tm' | 'bm' | 'ml' | 'mr'
let activePointerId = null;
let captureEl = null;
let startPointer = { x: 0, y: 0 };
let startBox = { x: 0, y: 0, w: 0, h: 0 };

const isPrimaryPointer = (e) => e.pointerType !== 'mouse' || e.button === 0;

const onBoxPointerDown = (e) => {
  if (!isPrimaryPointer(e)) return;
  e.preventDefault();
  e.stopPropagation();
  beginDrag(e, 'move');
};

const onHandlePointerDown = (e, handleType) => {
  if (!isPrimaryPointer(e)) return;
  e.preventDefault();
  e.stopPropagation();
  beginDrag(e, handleType);
};

const beginDrag = (e, mode) => {
  dragMode = mode;
  activePointerId = e.pointerId;
  startPointer = { x: e.clientX, y: e.clientY };
  startBox = { x: box.x, y: box.y, w: box.w, h: box.h };

  captureEl = e.currentTarget;
  try {
    captureEl.setPointerCapture?.(e.pointerId);
  } catch (err) {
    captureEl = null;
  }

  window.addEventListener('pointermove', onPointerMove, { passive: false });
  window.addEventListener('pointerup', onPointerEnd);
  window.addEventListener('pointercancel', onPointerEnd);
};

const onPointerMove = (e) => {
  if (!dragMode) return;
  if (activePointerId !== null && e.pointerId !== activePointerId) return;
  if (e.cancelable) e.preventDefault();

  const dx = e.clientX - startPointer.x;
  const dy = e.clientY - startPointer.y;

  const maxW = imgMeta.displayWidth;
  const maxH = imgMeta.displayHeight;

  if (dragMode === 'move') {
    box.x = Math.round(clamp(startBox.x + dx, 0, maxW - startBox.w));
    box.y = Math.round(clamp(startBox.y + dy, 0, maxH - startBox.h));
    return;
  }

  // 8 向缩放
  let newX = startBox.x;
  let newY = startBox.y;
  let newW = startBox.w;
  let newH = startBox.h;

  if (dragMode.includes('r')) {
    newW = clamp(startBox.w + dx, MIN_SIZE, maxW - startBox.x);
  }
  if (dragMode.includes('l')) {
    const clampDx = clamp(dx, -startBox.x, startBox.w - MIN_SIZE);
    newX = startBox.x + clampDx;
    newW = startBox.w - clampDx;
  }
  if (dragMode.includes('b')) {
    newH = clamp(startBox.h + dy, MIN_SIZE, maxH - startBox.y);
  }
  if (dragMode.includes('t')) {
    const clampDy = clamp(dy, -startBox.y, startBox.h - MIN_SIZE);
    newY = startBox.y + clampDy;
    newH = startBox.h - clampDy;
  }

  box.x = Math.round(newX);
  box.y = Math.round(newY);
  box.w = Math.round(newW);
  box.h = Math.round(newH);
};

const onPointerEnd = () => {
  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerEnd);
  window.removeEventListener('pointercancel', onPointerEnd);
  try {
    if (captureEl && activePointerId !== null) {
      captureEl.releasePointerCapture?.(activePointerId);
    }
  } catch (err) {
    /* 指针已释放，忽略 */
  }
  captureEl = null;
  activePointerId = null;
  dragMode = null;
};

// 舞台尺寸变化（弹层入场动画、旋转屏幕、软键盘收起）时重排，避免选框越界
let resizeObserver = null;
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined' && stageRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (isReady.value) computeLayout(false);
      else computeLayout(true);
    });
    resizeObserver.observe(stageRef.value);
  }
});

watch(
  () => props.show,
  (val) => {
    if (val) {
      isReady.value = false;
      nextTick(() => computeLayout(true));
    }
  }
);

onBeforeUnmount(() => {
  onPointerEnd();
  resizeObserver?.disconnect();
  resizeObserver = null;
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
    // 数据 URL / 同源 blob 不需要（也不应）设置 crossOrigin，否则部分 iOS 版本会加载失败
    if (!/^(data:|blob:)/i.test(props.imageUrl)) {
      sourceImg.crossOrigin = 'anonymous';
    }

    await new Promise((resolve, reject) => {
      sourceImg.onload = resolve;
      sourceImg.onerror = () => reject(new Error('图片解码失败'));
      sourceImg.src = props.imageUrl;
    });

    ctx.drawImage(sourceImg, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    isCropping.value = false;
    if (!blob) {
      showToast('生成裁剪图片失败，已改用原图');
      emit('skip');
      emit('update:show', false);
      return;
    }
    const croppedFile = new File([blob], `crop_${Date.now()}.jpg`, {
      type: 'image/jpeg',
      lastModified: Date.now()
    });
    const blobUrl = URL.createObjectURL(blob);
    emit('crop', { file: croppedFile, blobUrl, width: cropW, height: cropH });
    emit('update:show', false);
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
  -webkit-user-select: none;
  -webkit-touch-callout: none;
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
  padding: 8px 10px;
  touch-action: manipulation;
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
  touch-action: none;
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
  touch-action: none;
  z-index: 2;
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

/*
 * 四角与边缘手柄。
 * 手柄盒 36px、外扩仅 8px —— 这样即使选框贴到图片边缘（.canvas-container 是
 * overflow:hidden），仍有 28px 落在选框内侧可点，中间的点也不会被裁掉。
 */
.handle {
  position: absolute;
  width: 36px;
  height: 36px;
  box-sizing: border-box;
  z-index: 5;
  touch-action: none;
}

.handle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  background: #38bdf8;
  border: 2px solid #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}

.handle-tl {
  top: -8px;
  left: -8px;
  cursor: nwse-resize;
}
.handle-tr {
  top: -8px;
  right: -8px;
  cursor: nesw-resize;
}
.handle-bl {
  bottom: -8px;
  left: -8px;
  cursor: nesw-resize;
}
.handle-br {
  bottom: -8px;
  right: -8px;
  cursor: nwse-resize;
}

.handle-tm {
  top: -8px;
  left: calc(50% - 18px);
  cursor: ns-resize;
}
.handle-bm {
  bottom: -8px;
  left: calc(50% - 18px);
  cursor: ns-resize;
}
.handle-ml {
  top: calc(50% - 18px);
  left: -8px;
  cursor: ew-resize;
}
.handle-mr {
  top: calc(50% - 18px);
  right: -8px;
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
