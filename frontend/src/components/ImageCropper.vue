<template>
  <div class="cropper-container">
    <div class="cropper-box" ref="boxRef">
      <img :src="imageUrl" ref="imgRef" @load="initCropper" alt="待裁剪图" />
      <div
        v-if="isReady"
        class="crop-window"
        :style="windowStyle"
        @mousedown="startDrag"
        @touchstart="startDrag"
      >
        <span class="crop-tip">几何插图保留区</span>
      </div>
    </div>
    <div class="cropper-actions">
      <van-button size="small" @click="$emit('cancel')">取消</van-button>
      <van-button type="primary" size="small" @click="confirmCrop">确认保存配图</van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  imageUrl: { type: String, required: true }
});
const emit = defineEmits(['crop', 'cancel']);

const imgRef = ref(null);
const boxRef = ref(null);
const isReady = ref(false);

// 裁剪窗口坐标（百分比）
const cropBox = ref({
  x: 10,
  y: 20,
  w: 80,
  h: 40
});

const windowStyle = computed(() => ({
  left: `${cropBox.value.x}%`,
  top: `${cropBox.value.y}%`,
  width: `${cropBox.value.w}%`,
  height: `${cropBox.value.h}%`
}));

const initCropper = () => {
  isReady.value = true;
};

const confirmCrop = () => {
  // 生成裁剪区域并回调父组件
  emit('crop', { ...cropBox.value });
};

const startDrag = () => {
  // 简易拖拽占位
};
</script>

<style scoped>
.cropper-container {
  padding: 1rem;
  background: #0f172a;
  border-radius: 12px;
  color: white;
}

.cropper-box {
  position: relative;
  overflow: hidden;
  max-height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: black;
}

.cropper-box img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  display: block;
}

.crop-window {
  position: absolute;
  border: 2px dashed #38bdf8;
  background: rgba(56, 189, 248, 0.2);
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
  cursor: move;
  display: flex;
  align-items: center;
  justify-content: center;
}

.crop-tip {
  font-size: 0.75rem;
  background: rgba(15, 23, 42, 0.8);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.cropper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}
</style>
