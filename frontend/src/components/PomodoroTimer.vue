<template>
  <div class="pomodoro-container">
    <!-- 悬浮小番茄触发球 -->
    <div
      v-if="!showModal"
      class="floating-pomodoro-ball"
      :class="{ 'is-running': isRunning }"
      @click="showModal = true"
    >
      <span class="pomodoro-icon">🍅</span>
      <span class="ball-timer" v-if="isRunning">{{ formattedTime }}</span>
    </div>

    <!-- 专注番茄钟全屏/弹窗卡片 -->
    <van-popup
      v-model:show="showModal"
      round
      position="bottom"
      :style="{ maxHeight: '85%' }"
      closeable
    >
      <div class="pomodoro-modal-content">
        <h3 class="pomodoro-title">🍅 专注番茄钟</h3>
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
          <span>💡 提示：熄屏或切后台倒计时精准不暂停；iOS 锁屏受系统沙箱限制可能挂起网页声音，点亮屏幕即弹出完成提示。</span>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';
import { showDialog, showToast } from 'vant';

const showModal = ref(false);
const selectedMinutes = ref(25);
const remainingSeconds = ref(25 * 60);
const isRunning = ref(false);
const isPaused = ref(false);

let timerId = null;
let targetEndTime = 0; // 核心：目标结束绝对时间戳，切后台不漂移

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

    showDialog({
      title: '🎉 番茄钟专注完成！',
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
  right: 16px;
  bottom: 84px;
  z-index: 99;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #fff;
  padding: 8px 14px;
  border-radius: 24px;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.floating-pomodoro-ball:active {
  transform: scale(0.92);
}

.floating-pomodoro-ball.is-running {
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.pomodoro-icon {
  font-size: 20px;
}

.ball-timer {
  font-size: 14px;
  font-weight: bold;
  font-variant-numeric: tabular-nums;
}

/* 弹窗内容 */
.pomodoro-modal-content {
  padding: 24px 20px 30px;
  text-align: center;
}

.pomodoro-title {
  margin: 0 0 4px;
  font-size: 20px;
  color: #1a1a1a;
}

.pomodoro-subtitle {
  margin: 0 0 24px;
  font-size: 13px;
  color: #888;
}

.timer-dial-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.timer-circle {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 6px solid #fee2e2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fff;
  transition: all 0.3s ease;
}

.timer-circle.running {
  border-color: #ef4444;
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.15);
}

.time-display {
  font-size: 44px;
  font-weight: 800;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
  letter-spacing: -1px;
}

.status-tip {
  font-size: 13px;
  color: #ef4444;
  margin-top: 4px;
}

.duration-selector {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}

.duration-btn {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
}

.duration-btn.active {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
  font-weight: bold;
}

.actions-row {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 20px;
}

.control-btn {
  flex: 1;
  max-width: 140px;
  padding: 12px 0;
  border-radius: 24px;
  font-size: 16px;
  font-weight: bold;
  border: none;
  cursor: pointer;
}

.primary-btn {
  background: #ef4444;
  color: #fff;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.warning-btn {
  background: #f59e0b;
  color: #fff;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.secondary-btn {
  background: #f3f4f6;
  color: #4b5563;
}

.ios-audio-note {
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.5;
  text-align: left;
  background: #f9fafb;
  padding: 10px 14px;
  border-radius: 8px;
}
</style>
