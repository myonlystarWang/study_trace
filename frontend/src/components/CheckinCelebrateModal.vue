<template>
  <van-popup
    :show="modelValue"
    round
    :close-on-click-overlay="true"
    class="celebrate-popup"
    @update:show="val => emit('update:modelValue', val)"
    @closed="onClosed"
  >
    <div class="celebrate-card">
      <button class="close-btn" @click="close" aria-label="关闭">
        <van-icon name="cross" size="18" />
      </button>

      <!-- 成功弹跳微动效勾选图标 -->
      <div class="icon-bubble">
        <div class="success-circle">
          <van-icon name="success" class="success-icon" />
        </div>
      </div>

      <h3 class="celebrate-title">{{ customTitle || (isAllDone ? '今日全部满卡！' : '打卡成功！') }}</h3>
      <p class="celebrate-desc">
        {{ customMessage || (isAllDone ? '太棒了！今天的所有任务均已搞定，享受自由时光吧！' : '又迈出了坚实的一步，继续保持这份专注！') }}
      </p>

      <!-- 连续学习光晕胶囊 -->
      <div v-if="streak && streak > 0" class="streak-badge">
        <span class="streak-icon"><van-icon name="fire-o" /></span>
        <span class="streak-text">连续学习 <strong>{{ streak }}</strong> 天</span>
      </div>

      <!-- 操作按钮 -->
      <button class="continue-btn" @click="handleConfirm">
        {{ confirmText || '继续查看作业' }}
      </button>

      <!-- 底部精致庆祝彩带与星光插画 -->
      <div class="bottom-celebration-graphic">
        <van-icon name="star-o" class="deco-star deco-star-1" />
        <van-icon name="gem-o" class="deco-star deco-star-2" />
        <van-icon name="star-o" class="deco-star deco-star-3" />
      </div>
    </div>
  </van-popup>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  streak: {
    type: Number,
    default: 0
  },
  isAllDone: {
    type: Boolean,
    default: false
  },
  customTitle: {
    type: String,
    default: ''
  },
  customMessage: {
    type: String,
    default: ''
  },
  confirmText: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'confirm', 'closeDetail']);

const close = () => {
  emit('update:modelValue', false);
};

const handleConfirm = () => {
  emit('confirm');
  close();
};

const onClosed = () => {
  emit('closeDetail');
};
</script>

<style scoped>
:deep(.van-popup.celebrate-popup) {
  width: 86%;
  max-width: 340px;
  overflow: visible;
  background: transparent;
}

.celebrate-card {
  position: relative;
  background: var(--st-bg-card);
  border-radius: var(--st-radius-xl);
  padding: var(--st-space-6) var(--st-space-6) var(--st-space-5);
  text-align: center;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.15);
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  background: transparent;
  border: none;
  color: var(--st-text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-bubble {
  display: flex;
  justify-content: center;
  margin-bottom: var(--st-space-5);
}

.success-circle {
  width: 64px;
  height: 64px;
  border-radius: var(--st-radius-full);
  background: var(--st-success);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35);
  animation: popBounce 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
}

.success-icon {
  font-size: 32px;
  color: #ffffff;
}

@keyframes popBounce {
  0% {
    transform: scale(0.4);
    opacity: 0;
  }
  70% {
    transform: scale(1.12);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.celebrate-title {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
  margin: 0 0 var(--st-space-2);
}

.celebrate-desc {
  font-size: var(--st-font-sm);
  color: var(--st-text-secondary);
  line-height: var(--st-leading-normal);
  margin: 0 0 var(--st-space-5);
}

.streak-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--st-space-2);
  background: var(--st-warning-light);
  border: 1px solid var(--st-warning);
  padding: var(--st-space-2) var(--st-space-5);
  border-radius: var(--st-radius-full);
  margin-bottom: var(--st-space-5);
  box-shadow: var(--st-shadow-achievement);
}

.streak-icon {
  color: var(--st-warning-dark);
  font-size: var(--st-font-lg);
}

.streak-text {
  font-size: var(--st-font-sm);
  color: var(--st-warning-dark);
}

.streak-text strong {
  font-weight: 800;
  font-size: var(--st-font-lg);
}

.continue-btn {
  width: 100%;
  height: 42px;
  background: var(--st-gradient-primary-btn);
  color: #ffffff;
  font-size: var(--st-font-md);
  font-weight: 600;
  border: none;
  border-radius: var(--st-radius-full);
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.28);
  transition: opacity 0.15s ease, transform 0.1s ease;
}

.continue-btn:active {
  transform: scale(0.98);
  opacity: 0.92;
}

.bottom-celebration-graphic {
  position: relative;
  height: 28px;
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--st-space-4);
  user-select: none;
}

.deco-star {
  font-size: var(--st-font-md);
  color: var(--st-warning);
  animation: twinkle 1.5s infinite ease-in-out alternate;
}

.deco-star-1 {
  animation-delay: 0.2s;
}

.deco-star-2 {
  font-size: var(--st-font-lg);
  color: var(--st-primary);
  animation-delay: 0.5s;
}

.deco-star-3 {
  animation-delay: 0.8s;
}

@keyframes twinkle {
  0% { transform: scale(0.85); opacity: 0.6; }
  100% { transform: scale(1.15); opacity: 1; }
}
</style>
