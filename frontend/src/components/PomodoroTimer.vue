<template>
  <div class="pomodoro-container">
    <!-- 悬浮小番茄/专注计时触发球 (当 hideFloatingBall 为 true 时不显示独立浮球，由外部并列入口调用) -->
    <div
      v-if="!hideFloatingBall && !showModal"
      class="floating-pomodoro-ball"
      :class="{ 'is-running': isRunning }"
      @click="showModal = true"
    >
      <van-icon name="underway-o" size="18" />
      <span class="ball-timer" v-if="isRunning">{{ formattedTime }}</span>
    </div>

    <!-- 专注计时器全屏/底部半屏抽屉 -->
    <van-popup
      v-model:show="showModal"
      round
      position="bottom"
      class="bottom-sheet-modal"
      :style="{ maxHeight: '85%' }"
      closeable
    >
      <div class="pomodoro-modal-content">
        <div class="sheet-grabber"></div>
        <div class="st-section-header pomodoro-title-row">
          <span class="st-icon-badge st-icon-badge--danger">
            <van-icon name="underway-o" />
          </span>
          <span class="section-title">专注计时器</span>
        </div>
        <p class="pomodoro-subtitle">25 分钟高效专注，后台自动校准不漂移</p>

        <!-- 环形倒计时大表盘 -->
        <div class="timer-dial-wrapper">
          <div class="timer-circle" :class="{ running: isRunning }">
            <span class="time-display">{{ formattedTime }}</span>
            <span class="status-tip">{{ isRunning ? '专注进行中...' : isPaused ? '已暂停' : '准备开始' }}</span>
          </div>
        </div>

        <!-- 快捷时段选择 -->
        <div class="duration-selector" v-if="!isRunning && !isPaused">
          <button
            v-for="min in [15, 25, 45]"
            :key="min"
            class="duration-btn"
            :class="{ active: selectedMinutes === min }"
            @click="setDuration(min)"
          >
            {{ min }} 分钟
          </button>
        </div>

        <!-- 控制操作按钮 -->
        <div class="actions-row">
          <button
            v-if="!isRunning"
            class="control-btn primary-btn"
            @click="startTimer"
          >
            {{ isPaused ? '继续专注' : '开始专注' }}
          </button>
          <button
            v-else
            class="control-btn warning-btn"
            @click="pauseTimer"
          >
            暂停
          </button>
          <button
            class="control-btn secondary-btn"
            @click="resetTimer"
          >
            重置
          </button>
        </div>

        <div class="ios-audio-note">
          <van-icon name="info-o" />
          <span>提示：熄屏或切后台倒计时精准不暂停；iOS 锁屏受系统沙箱限制可能挂起网页声音，点亮屏幕即弹出完成提示。</span>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';
import { showDialog, showToast } from 'vant';

const props = defineProps({
  hideFloatingBall: {
    type: Boolean,
    default: false
  }
});

const showModal = ref(false);
const selectedMinutes = ref(25);
const remainingSeconds = ref(25 * 60);
const isRunning = ref(false);
const isPaused = ref(false);

let timerId = null;
let targetEndTime = 0; // 核心：目标结束绝对时间戳，切后台不漂移

defineExpose({
  open: () => { showModal.value = true; },
  close: () => { showModal.value = false; },
  isRunning,
  formattedTime: computed(() => {
    const m = Math.floor(remainingSeconds.value / 60);
    const s = remainingSeconds.value % 60;
    return `${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
  })
});

const formattedTime = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60);
  const s = remainingSeconds.value % 60;
  return `${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
});

const playDingSound = () => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.1);

    gain.gain.setValueAtTime(0.6, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.2);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 1.2);
  } catch (e) {
    console.log('Audio play ignored:', e);
  }
};

const tick = () => {
  const now = Date.now();
  const diff = Math.max(0, Math.round((targetEndTime - now) / 1000));
  remainingSeconds.value = diff;

  if (diff <= 0) {
    stopTimerInterval();
    isRunning.value = false;
    isPaused.value = false;
    remainingSeconds.value = selectedMinutes.value * 60;
    playDingSound();

    try {
      const d = new Date();
      const todayStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      const storageKey = `study_trace_pomodoro_${todayStr}`;
      const curr = parseInt(localStorage.getItem(storageKey) || '0', 10);
      localStorage.setItem(storageKey, String(curr + selectedMinutes.value));
      window.dispatchEvent(new CustomEvent('study_trace_pomodoro_completed', { detail: selectedMinutes.value }));
    } catch (e) {
      console.warn('Failed to save pomodoro focus minutes:', e);
    }

    showDialog({
      title: '专注时段达成',
      message: '太棒了！已完成本次高效专注阶段，休息 5 分钟活动一下眼睛吧！',
      confirmButtonText: '收到'
    });
  }
};

const startTimer = () => {
  if (isRunning.value) return;

  targetEndTime = Date.now() + remainingSeconds.value * 1000;
  isRunning.value = true;
  isPaused.value = false;

  timerId = setInterval(tick, 1000);
};

const pauseTimer = () => {
  if (!isRunning.value) return;
  stopTimerInterval();
  isRunning.value = false;
  isPaused.value = true;
};

const resetTimer = () => {
  stopTimerInterval();
  isRunning.value = false;
  isPaused.value = false;
  remainingSeconds.value = selectedMinutes.value * 60;
};

const setDuration = (min) => {
  selectedMinutes.value = min;
  resetTimer();
};

const stopTimerInterval = () => {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
};

onUnmounted(() => {
  stopTimerInterval();
});
</script>

<style scoped>
.pomodoro-container {
  position: relative;
}

/* 悬浮小番茄球 */
.floating-pomodoro-ball {
  position: fixed;
  right: var(--st-space-5);
  bottom: calc(50px + var(--st-space-6) + env(safe-area-inset-bottom, 0px));
  z-index: 99;
  min-width: 42px;
  min-height: 42px;
  background: var(--st-danger);
  color: #fff;
  padding: 0 var(--st-space-4);
  border-radius: var(--st-radius-full);
  box-shadow: var(--st-shadow-float);
  display: flex;
  align-items: center;
  gap: var(--st-space-2);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.floating-pomodoro-ball:active {
  transform: scale(0.92);
}

.floating-pomodoro-ball.is-running {
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.28); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.pomodoro-icon {
  font-size: 20px;
}

.ball-timer {
  font-size: var(--st-font-md);
  font-weight: bold;
  font-variant-numeric: tabular-nums;
}

/* 弹窗内容 */
.pomodoro-modal-content {
  padding: var(--st-space-3) var(--st-space-5) calc(var(--st-space-6) + env(safe-area-inset-bottom, 0px));
  text-align: center;
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  margin: 0 auto var(--st-space-4);
  border-radius: var(--st-radius-full);
  background: var(--st-border-bold);
}

.pomodoro-title-row {
  justify-content: center;
  margin-bottom: var(--st-space-1);
}

.pomodoro-subtitle {
  margin: 0 0 var(--st-space-6);
  font-size: var(--st-font-sm);
  color: var(--st-text-secondary);
  line-height: var(--st-leading-normal);
}

.timer-dial-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: var(--st-space-6);
}

.timer-circle {
  width: 200px;
  height: 200px;
  border-radius: var(--st-radius-full);
  border: 6px solid var(--st-danger-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--st-bg-card);
  box-shadow: var(--st-shadow-card);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.timer-circle.running {
  border-color: var(--st-danger);
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.15);
}

.time-display {
  font-size: 44px;
  font-weight: 800;
  color: var(--st-text-primary);
  font-variant-numeric: tabular-nums;
  letter-spacing: -1px;
}

.status-tip {
  font-size: var(--st-font-sm);
  color: var(--st-danger-dark);
  margin-top: var(--st-space-1);
}

.duration-selector {
  display: flex;
  justify-content: center;
  gap: var(--st-space-3);
  margin-bottom: var(--st-space-6);
}

.duration-btn {
  min-height: 34px;
  border: 1px solid var(--st-border);
  background: var(--st-bg-subtle);
  padding: var(--st-space-2) var(--st-space-4);
  border-radius: var(--st-radius-full);
  font-size: var(--st-font-sm);
  color: var(--st-text-regular);
  cursor: pointer;
}

.duration-btn.active {
  background: var(--st-danger-light);
  color: var(--st-danger-dark);
  border-color: var(--st-danger);
  font-weight: 600;
}

.actions-row {
  display: flex;
  justify-content: center;
  gap: var(--st-space-3);
  margin-bottom: var(--st-space-5);
}

.control-btn {
  flex: 1;
  max-width: 140px;
  min-height: 42px;
  padding: 0 var(--st-space-4);
  border-radius: var(--st-radius-full);
  font-size: var(--st-font-md);
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.primary-btn {
  background: var(--st-danger);
  color: #fff;
  box-shadow: var(--st-shadow-achievement);
}

.warning-btn {
  background: var(--st-warning);
  color: #fff;
  box-shadow: var(--st-shadow-achievement);
}

.secondary-btn {
  background: var(--st-bg-subtle);
  color: var(--st-text-regular);
  border: 1px solid var(--st-border);
}

.ios-audio-note {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  line-height: var(--st-leading-normal);
  text-align: left;
  background: var(--st-bg-subtle);
  padding: var(--st-space-3) var(--st-space-4);
  border-radius: var(--st-radius-md);
  display: flex;
  align-items: flex-start;
  gap: var(--st-space-2);
}
</style>
