<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    closeable
    :style="{ maxHeight: '80%' }"
    @update:show="$emit('update:show', $event)"
  >
    <div class="calendar-modal">
      <div class="calendar-header">
        <van-button size="small" icon="arrow-left" plain round @click="prevMonth" />
        <span class="current-month">{{ currentYear }}年 {{ currentMonth }}月</span>
        <van-button size="small" icon="arrow" plain round @click="nextMonth" />
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
        <div
          v-for="d in daysData"
          :key="d.date"
          class="day-cell"
          :class="{
            'is-today': d.date === todayStr,
            'is-selected': d.date === selectedDate
          }"
          @click="selectDay(d.date)"
        >
          <span class="day-number">{{ parseInt(d.date.split('-')[2]) }}</span>
          <div class="status-dot-container">
            <span class="status-dot" :class="'dot-' + d.status"></span>
          </div>
        </div>
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
  padding: 16px 12px 24px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 8px;
}

.current-month {
  font-size: 16px;
  font-weight: bold;
  color: #1a1a1a;
}

.weekdays-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
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
  gap: 4px;
  margin-bottom: 16px;
}

.day-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  background: #f9f9fb;
  transition: all 0.2s ease;
}

.day-cell:active {
  background: #eef2ff;
  transform: scale(0.96);
}

.day-cell.is-today {
  border: 1.5px solid #3b82f6;
  background: #eff6ff;
}

.day-cell.is-selected {
  background: #2563eb;
  color: #fff;
}

.day-cell.is-selected .day-number {
  color: #fff;
}

.day-number {
  font-size: 14px;
  font-weight: 500;
  color: #333;
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
  background-color: #10b981;
}

.dot-yellow {
  background-color: #f59e0b;
}

.dot-red {
  background-color: #ef4444;
}

.dot-gray {
  background-color: #d1d5db;
}

.legend-bar {
  display: flex;
  justify-content: space-around;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 11px;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
