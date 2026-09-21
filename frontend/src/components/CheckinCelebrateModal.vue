<template>
  <van-popup
    :show="modelValue"
    round
    :close-on-click-overlay="true"
    class="celebrate-popup"
    @update:show="val => emit('update:modelValue', val)"
  >
    <div class="celebrate-card">
      <button class="close-btn" @click="close" aria-label="关闭">
        <van-icon name="cross" size="18" />
      </button>

      <!-- 成功弹跳微动效勾选图标 -->
      <div class="icon-bubble">
        <div class="success-circle">
          <svg class="checkmark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      </div>

      <h3 class="celebrate-title">{{ customTitle || (isAllDone ? '今日全部满卡！' : '打卡成功！') }}</h3>
      <p class="celebrate-desc">
        {{ customMessage || (isAllDone ? '太棒了！今天的所有任务均已搞定，享受自由时光吧！' : '又迈出了坚实的一步，继续保持这份专注！') }}
      </p>

      <!-- 连续学习光晕胶囊 -->
      <div v-if="streak && streak > 0" class="streak-badge">
        <span class="fire-emoji">🔥</span>
        <span class="streak-text">连续学习 <strong>{{ streak }}</strong> 天</span>
      </div>

      <!-- 操作按钮 -->
      <button class="continue-btn" @click="handleConfirm">
        {{ confirmText || '继续查看作业' }}
      </button>

      <!-- 底部精致庆祝彩带与星光插画 -->
      <div class="bottom-celebration-graphic">
        <div class="deco-star deco-star-1">★</div>
        <div class="deco-star deco-star-2">✦</div>
        <div class="deco-star deco-star-3">★</div>
        <div class="deco-sprout">🌱</div>
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

const emit = defineEmits(['update:modelValue', 'confirm']);

const close = () => {
  emit('update:modelValue', false);
};

const handleConfirm = () => {
  emit('confirm');
  close();
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
  background: #ffffff;
  border-radius: 20px;
  padding: 32px 24px 20px;
  text-align: center;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.15);
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-bubble {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.success-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35);
  animation: popBounce 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
}

.checkmark-svg {
  width: 32px;
  height: 32px;
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
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.celebrate-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 18px;
}

.streak-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #fff7ed 0%, #fef3c7 100%);
  border: 1px solid #fed7aa;
  padding: 6px 16px;
  border-radius: 9999px;
  margin-bottom: 22px;
  box-shadow: var(--st-shadow-achievement, 0 4px 14px rgba(245, 158, 11, 0.15));
}

.fire-emoji {
  font-size: 16px;
}

.streak-text {
  font-size: 13px;
  color: #c2410c;
}

.streak-text strong {
  font-weight: 800;
  font-size: 15px;
}

.continue-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 12px;
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
  gap: 12px;
  user-select: none;
}

.deco-star {
  font-size: 14px;
  color: #facc15;
  animation: twinkle 1.5s infinite ease-in-out alternate;
}

.deco-star-1 {
  animation-delay: 0.2s;
}

.deco-star-2 {
  font-size: 18px;
  color: #38bdf8;
  animation-delay: 0.5s;
}

.deco-star-3 {
  animation-delay: 0.8s;
}

.deco-sprout {
  font-size: 16px;
}

@keyframes twinkle {
  0% { transform: scale(0.85); opacity: 0.6; }
  100% { transform: scale(1.15); opacity: 1; }
}
</style>
