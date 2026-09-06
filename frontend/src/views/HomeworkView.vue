<template>
  <div class="homework-view">
    <!-- 顶栏：品牌门面 (Logo + 智学迹) + 打卡连击胶囊 + 日历微纽 -->
    <div class="top-nav-bar">
      <div class="brand-header">
        <div class="brand-logo-badge">
          <van-icon name="bookmark" />
        </div>
        <div class="brand-text-wrap">
          <span class="brand-title">智学迹</span>
          <span class="brand-subtitle">StudyTrace</span>
        </div>
      </div>

      <div class="header-right-tools">
        <div class="streak-pill" v-if="streak > 0" title="当前连续打卡天数">
          <van-icon name="fire" color="#f97316" size="13" />
          <span>连打 <b>{{ streak }}</b> 天</span>
        </div>
        <div v-else class="streak-pill streak-pill--idle">
          <van-icon name="passed" color="#2563eb" size="13" />
          <span>今日打卡</span>
        </div>

        <button class="calendar-pill-btn" @click="showCalendar = true">
          <van-icon name="calendar-o" size="13" />
          <span>日期</span>
        </button>
      </div>
    </div>

    <!-- 顶部 7 日横向胶囊日历条 (带上周/下周微纽与触屏切周手势) -->
    <div class="week-strip-container">
      <button class="week-nav-arrow" @click="changeWeek(-1)" title="上一周">
        <van-icon name="arrow-left" size="13" />
      </button>

      <div 
        class="week-strip-box"
        @touchstart="handleTouchStart"
        @touchend="handleTouchEnd"
      >
        <div
          v-for="day in weekDays"
          :key="day.dateStr"
          class="week-day-pill"
          :class="{ active: day.isSelected, today: day.isToday }"
          @click="selectDay(day.dateStr)"
        >
          <span class="day-label">{{ day.label }}</span>
          <span class="day-number">{{ day.dateNumber }}</span>
          <span 
            class="day-dot" 
            :class="{ completed: day.isSelected ? (rate === 100 && totalCount > 0) : false }"
          ></span>
        </div>
      </div>

      <button class="week-nav-arrow" @click="changeWeek(1)" title="下一周">
        <van-icon name="arrow" size="13" />
      </button>
    </div>

    <!-- 今日进度概览卡片 (含 100% 达成微反馈) -->
    <div class="st-card progress-summary-card">
      <div class="progress-header">
        <div class="st-section-header" style="margin-bottom: 0;">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="chart-trending-o" />
          </span>
          <span class="section-title">{{ isToday ? '今日' : currentDate }} 作业进度</span>
        </div>
        <span class="progress-stat-text">
          <b>{{ completedCount }}</b> / {{ totalCount }} 已完成
        </span>
      </div>

      <div class="progress-bar-wrapper">
        <van-progress
          :percentage="rate"
          :color="rate === 100 && totalCount > 0 ? 'var(--st-success, #10b981)' : 'var(--st-primary, #2563eb)'"
          :show-pivot="false"
          stroke-width="8"
        />
      </div>

      <!-- 100% 全部完成成就微反馈 -->
      <transition name="van-fade">
        <div v-if="rate === 100 && totalCount > 0" class="all-done-banner">
          <div class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px;">
            <van-icon name="passed" />
          </div>
          <span>太棒了！今日全部作业均已如期完成</span>
        </div>
      </transition>
    </div>

    <!-- 学科快捷筛选胶囊栏 (Chips - 强制单行滑动) -->
    <div class="subject-chips-bar st-scroll-x" v-if="subjects.length > 0">
      <span
        class="st-chip"
        :class="{ active: selectedSubject === null }"
        @click="selectedSubject = null"
      >
        全部 ({{ totalCount }})
      </span>
      <span
        v-for="sub in subjects"
        :key="sub.id"
        class="st-chip"
        :class="{ active: selectedSubject === sub.id }"
        @click="selectedSubject = sub.id"
      >
        {{ sub.name }}
      </span>
    </div>

    <!-- 作业列表区 (左滑抽屉、手势解耦、无 Emoji) -->
    <van-pull-refresh v-model="refreshing" @refresh="fetchHomework">
      <div class="homework-list-wrapper" v-if="filteredItems.length > 0">
        <div class="list-section-header">
          <span class="list-title">待办作业 ({{ filteredItems.length }} 项)</span>
          <span class="swipe-hint">
            <van-icon name="exchange" /> 左滑卡片呼出操作
          </span>
        </div>

        <div class="homework-cards">
          <van-swipe-cell
            v-for="item in filteredItems"
            :key="item.id"
            class="hw-swipe-cell"
          >
            <!-- 卡片正面：克制扁平、无多余平铺按钮 -->
            <div
              class="st-card hw-card-face"
              :class="{ 'is-done': item.is_completed }"
              @click="toggleComplete(item)"
            >
              <!-- 大号圆形打勾微动效 -->
              <div
                class="hw-check-circle"
                :class="{ checked: item.is_completed, 'st-animate-check': item.justToggled }"
                @click.stop="toggleComplete(item)"
              >
                <van-icon v-if="item.is_completed" name="success" size="14" color="#ffffff" />
              </div>

              <!-- 标题与学科信息 -->
              <div class="hw-content">
                <div class="hw-meta-row">
                  <span class="st-subject-tag" :class="getSubjectTagClass(item.subject_name)">
                    {{ item.subject_name }}
                  </span>
                  <span class="hw-due-time" v-if="item.completed_at">
                    <van-icon name="clock-o" /> 已于 {{ item.completed_at.substring(11, 16) }} 打卡
                  </span>
                </div>
                <div class="hw-title" :class="{ strike: item.is_completed }">
                  {{ item.content }}
                </div>
              </div>

              <!-- 状态微指示 -->
              <div class="hw-status-tag" :class="{ done: item.is_completed }">
                {{ item.is_completed ? '已打卡' : '待完成' }}
              </div>
            </div>

            <!-- 左滑展开的抽屉操作按钮 (转错题 + 删除) -->
            <template #right>
              <div class="swipe-actions-box">
                <button class="swipe-action-btn btn-mistake" @click.stop="handleToMistake(item)">
                  <van-icon name="plus" size="16" />
                  <span>转错题</span>
                </button>
                <button class="swipe-action-btn btn-delete" @click.stop="handleDelete(item)">
                  <van-icon name="delete-o" size="16" />
                  <span>删除</span>
                </button>
              </div>
            </template>
          </van-swipe-cell>
        </div>
      </div>

      <!-- 清爽空状态 -->
      <div class="empty-box" v-else>
        <van-empty description="今天暂无作业，点击下方添加吧" />
      </div>
    </van-pull-refresh>

    <!-- 底部常驻磨砂悬浮录入栏 (录入新作业 + 专注计时并列排布，彻底消除重叠) -->
    <div class="floating-bottom-bar st-frosted-bar">
      <van-button
        type="primary"
        round
        icon="plus"
        class="add-hw-btn"
        @click="showAddModal = true"
      >
        录入新作业
      </van-button>
      <van-button
        round
        plain
        :type="pomodoroRef?.isRunning ? 'danger' : 'default'"
        class="pomodoro-entry-btn"
        :class="{ 'is-running': pomodoroRef?.isRunning }"
        @click="pomodoroRef?.open()"
      >
        <van-icon name="underway-o" :color="pomodoroRef?.isRunning ? '#ef4444' : '#475569'" size="16" />
        <span class="pomodoro-btn-text">
          {{ pomodoroRef?.isRunning ? pomodoroRef?.formattedTime : '专注' }}
        </span>
      </van-button>
    </div>

    <!-- 录入作业底部半屏抽屉 (支持手动 / 拍照 OCR 识别批量录入) -->
    <QuickAddModal
      v-model:show="showAddModal"
      :subjects="subjects"
      :date-str="currentDate"
      @added="fetchHomework"
    />

    <!-- 月历打卡浮窗组件 -->
    <CalendarModal
      v-model:show="showCalendar"
      :selected-date="currentDate"
      @select-date="handleDateSelect"
    />

    <!-- 25分钟专注番茄钟 (hideFloatingBall=true，由底部并列入口驱动) -->
    <PomodoroTimer ref="pomodoroRef" :hide-floating-ball="true" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { showToast, showConfirmDialog } from 'vant';
import { homeworkApi, settingsApi } from '../api';
import QuickAddModal from '../components/QuickAddModal.vue';
import CalendarModal from '../components/CalendarModal.vue';
import PomodoroTimer from '../components/PomodoroTimer.vue';

const pomodoroRef = ref(null);
const currentDate = ref(new Date().toISOString().split('T')[0]);
const streak = ref(0);
const totalCount = ref(0);
const completedCount = ref(0);
const rate = ref(0);
const items = ref([]);
const subjects = ref([]);
const selectedSubject = ref(null);
const refreshing = ref(false);
const showAddModal = ref(false);
const showCalendar = ref(false);

const isToday = computed(() => {
  return currentDate.value === new Date().toISOString().split('T')[0];
});

// 计算以当前选中日期为锚点的周历条 (Mon ~ Sun)
const weekDays = computed(() => {
  const curr = new Date(currentDate.value);
  const dayOfWeek = curr.getDay(); // 0 是周日, 1~6 是周一~周六
  const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(curr);
  monday.setDate(curr.getDate() + diffToMonday);

  const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  const todayStr = new Date().toISOString().split('T')[0];
  const list = [];

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const dateStr = d.toISOString().split('T')[0];
    list.push({
      dateStr,
      label: labels[i],
      dateNumber: d.getDate().toString(),
      isToday: dateStr === todayStr,
      isSelected: dateStr === currentDate.value
    });
  }
  return list;
});

const filteredItems = computed(() => {
  if (!selectedSubject.value) return items.value;
  return items.value.filter((i) => i.subject_id === selectedSubject.value);
});

// 学科标签颜色映射
const getSubjectTagClass = (name) => {
  if (!name) return 'st-subject-tag--neutral';
  switch (name) {
    case '数学': return 'st-subject-tag--primary';
    case '英语': return 'st-subject-tag--purple';
    case '语文': return 'st-subject-tag--success';
    case '物理':
    case '化学': return 'st-subject-tag--info';
    case '生物':
    case '地理': return 'st-subject-tag--warning';
    case '历史':
    case '道德与法治':
    case '道法': return 'st-subject-tag--danger';
    default: return 'st-subject-tag--neutral';
  }
};

const selectDay = (dateStr) => {
  currentDate.value = dateStr;
  fetchHomework();
};

const changeWeek = (offset) => {
  const d = new Date(currentDate.value);
  d.setDate(d.getDate() + offset * 7);
  currentDate.value = d.toISOString().split('T')[0];
  fetchHomework();
  showToast({ message: `${d.getMonth() + 1}月${d.getDate()}日所在周`, position: 'top', duration: 800 });
};

// 仅在顶部周历条监听左右滑动手势翻周
let touchStartX = 0;
const handleTouchStart = (e) => {
  touchStartX = e.touches[0].clientX;
};

const handleTouchEnd = (e) => {
  const diffX = e.changedTouches[0].clientX - touchStartX;
  if (diffX > 50) {
    changeWeek(-1); // 右滑：上一周
  } else if (diffX < -50) {
    changeWeek(1); // 左滑：下一周
  }
};

const handleDateSelect = (dateStr) => {
  currentDate.value = dateStr;
  fetchHomework();
};

const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data;
  } catch (e) {
    console.error(e);
  }
};

const fetchHomework = async () => {
  refreshing.value = true;
  try {
    const res = await homeworkApi.getList(currentDate.value);
    totalCount.value = res.data.total;
    completedCount.value = res.data.completed;
    rate.value = res.data.rate;
    streak.value = res.data.streak;
    items.value = res.data.items;
  } catch (e) {
    showToast('加载作业失败');
  } finally {
    refreshing.value = false;
  }
};

const toggleComplete = async (item) => {
  const targetStatus = !item.is_completed;
  item.justToggled = true;
  setTimeout(() => {
    item.justToggled = false;
  }, 250);

  try {
    await homeworkApi.update(item.id, { is_completed: targetStatus });
    item.is_completed = targetStatus;
    if (targetStatus) {
      showToast({ message: '太棒了！又完成一项', icon: 'passed', duration: 1200 });
    }
    fetchHomework();
  } catch (e) {
    showToast('更新失败');
  }
};

const handleToMistake = async (item) => {
  try {
    await homeworkApi.toMistake(item.id);
    showToast({ message: '已成功归档到错题本！', icon: 'records-o' });
  } catch (e) {
    showToast('转错题失败');
  }
};

const handleDelete = (item) => {
  showConfirmDialog({
    title: '确认删除',
    message: '确定要删除这条作业记录吗？'
  }).then(async () => {
    try {
      await homeworkApi.delete(item.id);
      showToast({ message: '已删除', position: 'bottom' });
      fetchHomework();
    } catch (e) {
      showToast('删除失败');
    }
  });
};

onMounted(async () => {
  await fetchSubjects();
  await fetchHomework();
});
</script>

<style scoped>
.homework-view {
  flex: 1;
  background-color: var(--st-bg-page, #f8fafc);
  padding: 12px 14px 16px;
}

/* 顶栏信息 */
.top-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.brand-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-logo-badge {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 16px;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
  flex-shrink: 0;
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--st-text-primary, #0f172a);
  line-height: 1.15;
  letter-spacing: -0.2px;
}

.brand-subtitle {
  font-size: 10px;
  font-weight: 600;
  color: var(--st-primary, #2563eb);
  letter-spacing: 0.5px;
  line-height: 1;
  margin-top: 1px;
}

.streak-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  font-size: 12px;
  font-weight: 600;
  color: #c2410c;
  background: #fff7ed;
  padding: 0 9px;
  border-radius: var(--st-radius-full, 9999px);
  border: 1px solid #fed7aa;
  white-space: nowrap;
}

.streak-pill--idle {
  color: var(--st-primary, #2563eb);
  background: var(--st-primary-light, #eff6ff);
  border-color: rgba(37, 99, 235, 0.15);
}

.header-right-tools {
  display: flex;
  align-items: center;
  gap: 6px;
}

.calendar-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--st-radius-full, 9999px);
  background: var(--st-bg-card, #ffffff);
  border: 1px solid var(--st-border-bold, #e2e8f0);
  color: var(--st-text-secondary, #475569);
  font-size: 12px;
  font-weight: 500;
  box-shadow: var(--st-shadow-card, 0 1px 3px rgba(15, 23, 42, 0.04));
  cursor: pointer;
  transition: all 0.15s ease;
}

.calendar-pill-btn:hover {
  border-color: var(--st-primary, #2563eb);
  color: var(--st-primary, #2563eb);
}

/* 顶部 7 日横向胶囊日历条 */
.week-strip-box {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  margin-bottom: 14px;
}

.week-day-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 2px;
  background-color: var(--st-bg-card, #ffffff);
  border: 1px solid var(--st-border, #f1f5f9);
  border-radius: var(--st-radius-md, 10px);
  box-shadow: var(--st-shadow-card, 0 1px 3px rgba(15, 23, 42, 0.04));
  cursor: pointer;
  transition: all 0.15s ease;
}

.week-day-pill.active {
  background-color: var(--st-primary, #2563eb);
  border-color: var(--st-primary, #2563eb);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
}

.week-day-pill .day-label {
  font-size: 11px;
  color: var(--st-text-muted, #94a3b8);
  margin-bottom: 2px;
}

.week-day-pill.active .day-label {
  color: rgba(255, 255, 255, 0.8);
}

.week-day-pill .day-number {
  font-size: 14px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.week-day-pill.active .day-number {
  color: #ffffff;
}

.week-day-pill .day-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  margin-top: 4px;
  background-color: transparent;
}

.week-day-pill .day-dot.completed {
  background-color: var(--st-success, #10b981);
}

.week-day-pill.active .day-dot.completed {
  background-color: #ffffff;
}

/* 进度概览卡片 */
.progress-summary-card {
  margin-bottom: 14px;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.progress-stat-text {
  font-size: 12px;
  color: var(--st-text-secondary, #64748b);
}

.progress-bar-wrapper {
  margin-bottom: 6px;
}

.all-done-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background-color: var(--st-success-light, #ecfdf5);
  border-radius: var(--st-radius-sm, 6px);
  font-size: 12px;
  font-weight: 500;
  color: var(--st-success-dark, #059669);
}

/* 学科快捷筛选胶囊栏 */
.subject-chips-bar {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
  margin-bottom: 4px;
  scrollbar-width: none;
}

.subject-chips-bar::-webkit-scrollbar {
  display: none;
}

/* 作业列表区 */
.list-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding: 0 4px;
}

.list-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--st-text-primary, #0f172a);
}

.swipe-hint {
  font-size: 11px;
  color: var(--st-text-muted, #94a3b8);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.homework-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hw-swipe-cell {
  border-radius: var(--st-radius-lg, 14px);
  overflow: hidden;
}

.hw-card-face {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.hw-card-face.is-done {
  background-color: #fafbfc;
  border-color: #f1f5f9;
}

/* 圆形打勾交互区 */
.hw-check-circle {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--st-border-bold, #cbd5e1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
  background-color: #ffffff;
}

.hw-check-circle.checked {
  background-color: var(--st-success, #10b981);
  border-color: var(--st-success, #10b981);
}

.hw-content {
  flex: 1;
  min-width: 0;
}

.hw-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.hw-due-time {
  font-size: 11px;
  color: var(--st-text-muted, #94a3b8);
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.hw-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--st-text-primary, #0f172a);
  line-height: 1.4;
  word-break: break-all;
}

.hw-title.strike {
  color: var(--st-text-muted, #94a3b8);
  text-decoration: line-through;
}

.hw-status-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--st-warning-dark, #d97706);
  background-color: var(--st-warning-light, #fffbeb);
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
  flex-shrink: 0;
}

.hw-status-tag.done {
  color: var(--st-success-dark, #059669);
  background-color: var(--st-success-light, #ecfdf5);
}

/* 左滑呼出的操作抽屉 */
.swipe-actions-box {
  display: flex;
  height: 100%;
}

.swipe-action-btn {
  border: none;
  height: 100%;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.swipe-action-btn.btn-mistake {
  background-color: var(--st-primary, #2563eb);
}

.swipe-action-btn.btn-delete {
  background-color: var(--st-danger, #ef4444);
}

.empty-box {
  padding: 30px 0;
}

/* 顶部周历条容器 */
.week-strip-container {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
}

.week-nav-arrow {
  width: 24px;
  height: 50px;
  border: none;
  background: transparent;
  color: var(--st-text-muted, #94a3b8);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: var(--st-radius-sm, 6px);
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.week-nav-arrow:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--st-primary, #2563eb);
}

.week-nav-arrow:active {
  transform: scale(0.92);
}

.week-strip-box {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  user-select: none;
}

/* 底部常驻悬浮栏 */
.floating-bottom-bar {
  position: fixed;
  bottom: 50px;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 40;
}

.add-hw-btn {
  flex: 1;
  font-weight: 600;
  height: 42px;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

.pomodoro-entry-btn {
  flex-shrink: 0;
  padding: 0 14px;
  height: 42px;
  font-weight: 600;
  border-color: var(--st-border-bold, #cbd5e1);
  background: #ffffff;
  color: var(--st-text-regular, #334155);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.pomodoro-entry-btn.is-running {
  border-color: var(--st-danger, #ef4444);
  color: var(--st-danger, #ef4444);
  background: var(--st-danger-light, #fef2f2);
}
</style>
