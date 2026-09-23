<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    class="bottom-sheet-modal calendar-popup"
    :style="{ maxHeight: '80%' }"
    @update:show="$emit('update:show', $event)"
  >
    <div class="calendar-modal">
      <div class="sheet-grabber"></div>
      <div class="st-section-header calendar-title-row">
        <span class="st-icon-badge st-icon-badge--primary">
          <van-icon name="calendar-o" />
        </span>
        <span class="section-title">学习日历</span>
      </div>
      <div class="calendar-header">
        <van-button class="calendar-nav-btn" size="small" icon="arrow-left" plain round @click="prevMonth" />
        <span class="current-month">{{ currentYear }}年 {{ currentMonth }}月</span>
        <van-button class="calendar-nav-btn" size="small" icon="arrow" plain round @click="nextMonth" />
      </div>

      <!-- 星期表头 -->
      <div class="weekdays-grid">
        <span v-for="w in weekdays" :key="w" class="weekday-item">{{ w }}</span>
      </div>

      <!-- 日历网格 -->
      <div v-if="loading" class="calendar-loading">
        <van-loading size="24px" vertical>加载月度打卡中...</van-loading>
      </div>
      <div v-else class="days-grid">
        <!-- 空白占位符 -->
        <div v-for="blank in blankDays" :key="'blank-' + blank" class="day-cell blank"></div>

        <!-- 真实天数 -->
        <button
          v-for="d in daysData"
          :key="d.date"
          class="day-cell"
          :class="{
            'is-today': d.date === todayStr,
            'is-selected': d.date === selectedDate
          }"
          type="button"
          :aria-label="`${d.date}，${d.status === 'green' ? '全部完成' : d.status === 'yellow' ? '部分完成' : d.status === 'red' ? '未开始' : '无作业'}`"
          @click="selectDay(d.date)"
        >
          <span class="day-number">{{ parseInt(d.date.split('-')[2]) }}</span>
          <div class="status-dot-container">
            <span class="status-dot" :class="'dot-' + d.status"></span>
          </div>
        </button>
      </div>

      <!-- 图例说明 -->
      <div class="legend-bar">
        <div class="legend-item"><span class="status-dot dot-green"></span> 全部完成</div>
        <div class="legend-item"><span class="status-dot dot-yellow"></span> 部分完成</div>
        <div class="legend-item"><span class="status-dot dot-red"></span> 未开始</div>
        <div class="legend-item"><span class="status-dot dot-gray"></span> 无作业</div>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { homeworkApi } from '../api';
import { showToast } from 'vant';

const props = defineProps({
  show: { type: Boolean, default: false },
  selectedDate: { type: String, default: '' }
});

const emit = defineEmits(['update:show', 'select-date']);

const weekdays = ['一', '二', '三', '四', '五', '六', '日'];
const todayStr = new Date().toISOString().split('T')[0];

const currentYear = ref(new Date().getFullYear());
const currentMonth = ref(new Date().getMonth() + 1);
const daysData = ref([]);
const loading = ref(false);

const monthStr = computed(() => {
  const m = currentMonth.value < 10 ? `0${currentMonth.value}` : `${currentMonth.value}`;
  return `${currentYear.value}-${m}`;
});

// 计算当月 1 号是周几 (0 为周日，1-6 为周一至周六)
const blankDays = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value - 1, 1).getDay();
  // 转换为周一为 0，周日为 6
  return (firstDay + 6) % 7;
});

const fetchMonthData = async () => {
  loading.value = true;
  try {
    const res = await homeworkApi.getCalendar(monthStr.value);
    daysData.value = res.data.days || [];
  } catch (err) {
    showToast('加载月历失败');
  } finally {
    loading.value = false;
  }
};

const prevMonth = () => {
  if (currentMonth.value === 1) {
    currentYear.value -= 1;
    currentMonth.value = 12;
  } else {
    currentMonth.value -= 1;
  }
  fetchMonthData();
};

const nextMonth = () => {
  if (currentMonth.value === 12) {
    currentYear.value += 1;
    currentMonth.value = 1;
  } else {
    currentMonth.value += 1;
  }
  fetchMonthData();
};

const selectDay = (dateStr) => {
  emit('select-date', dateStr);
  emit('update:show', false);
};

// 监听弹窗打开，若有 selectedDate 则同步年月
watch(
  () => props.show,
  (newVal) => {
    if (newVal) {
      if (props.selectedDate) {
        const [y, m] = props.selectedDate.split('-');
        if (y && m) {
          currentYear.value = parseInt(y);
          currentMonth.value = parseInt(m);
        }
      }
      fetchMonthData();
    }
  }
);
</script>

<style scoped>
.calendar-modal {
  padding: var(--st-space-3) var(--st-space-4) calc(var(--st-space-6) + env(safe-area-inset-bottom, 0px));
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  margin: 0 auto var(--st-space-4);
  border-radius: var(--st-radius-full);
  background: var(--st-border-bold);
}

.calendar-title-row {
  margin-bottom: var(--st-space-5);
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--st-space-5);
  padding: 0 var(--st-space-1);
}

.current-month {
  font-size: var(--st-font-lg);
  font-weight: 600;
  color: var(--st-text-primary);
}

.calendar-nav-btn {
  min-width: 34px;
  border-color: var(--st-border) !important;
  background: var(--st-bg-subtle) !important;
  color: var(--st-text-regular) !important;
}

.weekdays-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-bottom: var(--st-space-3);
}

.calendar-loading {
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--st-space-1);
  margin-bottom: var(--st-space-5);
}

.day-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--st-radius-sm);
  padding: 0;
  font: inherit;
  cursor: pointer;
  background: var(--st-bg-subtle);
  transition: transform 0.15s ease, background-color 0.15s ease, border-color 0.15s ease;
}

.day-cell:active {
  background: var(--st-primary-light);
  transform: scale(0.96);
}

.day-cell.is-today {
  border-color: var(--st-primary);
  background: var(--st-primary-light);
}

.day-cell.is-selected {
  border-color: var(--st-primary);
  background: var(--st-primary);
  color: #fff;
}

.day-cell.is-selected .day-number {
  color: #fff;
}

.day-number {
  font-size: var(--st-font-md);
  font-weight: 500;
  color: var(--st-text-regular);
}

.status-dot-container {
  margin-top: 2px;
  height: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.dot-green {
  background-color: var(--st-success);
}

.dot-yellow {
  background-color: var(--st-warning);
}

.dot-red {
  background-color: var(--st-danger);
}

.dot-gray {
  background-color: var(--st-border-bold);
}

.legend-bar {
  display: flex;
  justify-content: space-around;
  padding-top: var(--st-space-4);
  border-top: 1px solid var(--st-border);
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--st-space-1);
}
</style>
