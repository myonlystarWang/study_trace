<template>
  <div class="homework-view">
    <!-- 顶栏：标题 + 打卡连击胶囊 + 日历微纽 + 加号录入 -->
    <div class="top-nav-bar">
      <div class="brand-header">
        <h1 class="homework-top-title">作业</h1>
      </div>

      <div class="header-right-tools">
        <!-- 满卡状态：所有作业已完成 -->
        <div class="streak-pill" v-if="rate === 100 && totalCount > 0" title="今日作业已全部打卡完成！">
          <van-icon name="fire" color="#f97316" size="13" />
          <span>连打 <b>{{ streak > 0 ? streak : 1 }}</b> 天</span>
        </div>
        <!-- 进行中状态：有作业但未全部完成 -->
        <div class="streak-pill streak-pill--idle" v-else-if="totalCount > 0" title="今日作业打卡中">
          <van-icon name="underway-o" color="#2563eb" size="13" />
          <span v-if="completedCount > 0">打卡中 <b>{{ completedCount }}/{{ totalCount }}</b></span>
          <span v-else>待打卡 <b>{{ totalCount }}</b> 项</span>
        </div>
        <!-- 无作业状态 -->
        <div class="streak-pill streak-pill--idle" v-else title="今日暂无作业">
          <van-icon name="notes-o" color="#64748b" size="13" />
          <span>暂无作业</span>
        </div>

        <button class="calendar-pill-btn" @click="showCalendar = true">
          <van-icon name="calendar-o" size="13" />
          <span>月历</span>
        </button>

        <button class="add-top-round-btn" @click="showAddModal = true" title="录入作业">
          <van-icon name="plus" size="15" />
        </button>
      </div>
    </div>

    <!-- iOS 风格三段式子标签栏：今日作业 | 全部作业 | 历史记录 (与 chatgpt.jpg 保持一致) -->
    <div class="homework-sub-tabs">
      <button
        class="sub-tab-item"
        :class="{ active: subTab === 'today' }"
        @click="switchSubTab('today')"
      >
        <span>今日作业</span>
        <div class="sub-tab-indicator" v-if="subTab === 'today'"></div>
      </button>
      <button
        class="sub-tab-item"
        :class="{ active: subTab === 'all' }"
        @click="switchSubTab('all')"
      >
        <span>全部作业</span>
        <div class="sub-tab-indicator" v-if="subTab === 'all'"></div>
      </button>
      <button
        class="sub-tab-item"
        :class="{ active: subTab === 'history' }"
        @click="switchSubTab('history')"
      >
        <span>历史记录</span>
        <div class="sub-tab-indicator" v-if="subTab === 'history'"></div>
      </button>
    </div>

    <!-- 顶部 7 日横向胶囊日历条 (仅在「今日作业」视图展示) -->
    <div class="week-strip-container" v-if="subTab === 'today'">
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
            :class="'dot-' + (day.status || 'gray')"
          ></span>
        </div>
      </div>

      <button class="week-nav-arrow" @click="changeWeek(1)" title="下一周">
        <van-icon name="arrow" size="13" />
      </button>
    </div>

    <!-- 今日进度概览卡片 (含 100% 达成微反馈) -->
    <div class="st-card progress-summary-card" v-if="subTab === 'today'">
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
          <span>太棒了！{{ weekendRollover ? '周末大作业与今日任务已全部完成' : '今日全部作业均已如期完成' }}</span>
        </div>
      </transition>
    </div>

    <!-- 全部/历史记录 顶部状态卡片 -->
    <div class="st-card scope-summary-card" v-else>
      <div class="scope-summary-left">
        <span class="st-icon-badge" :class="subTab === 'all' ? 'st-icon-badge--warning' : 'st-icon-badge--success'">
          <van-icon :name="subTab === 'all' ? 'todo-list-o' : 'passed'" />
        </span>
        <span class="section-title">{{ subTab === 'all' ? '全部待完成作业' : '历史打卡记录' }}</span>
      </div>
      <span class="scope-badge-count">共 {{ totalCount }} 项</span>
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
      <div class="homework-list-wrapper" v-if="filteredItems.length > 0 || filteredRolloverItems.length > 0">
        <!-- 分区1：周末顺延大作业（如果存在 filteredRolloverItems） -->
        <div class="rollover-section" v-if="filteredRolloverItems.length > 0">
          <div class="list-section-header rollover-header">
            <div class="rollover-title-box">
              <span class="st-icon-badge st-icon-badge--warning">
                <van-icon name="clock-o" />
              </span>
              <span class="section-title">周末顺延大作业 ({{ filteredRolloverItems.length }} 项)</span>
              <span class="rollover-badge-tag">
                <van-icon name="underway-o" /> 来自周五 · 截止周日晚
              </span>
            </div>
            <span class="swipe-hint">
              <van-icon name="exchange" /> 左滑操作
            </span>
          </div>

          <div class="homework-cards">
            <van-swipe-cell
              v-for="item in filteredRolloverItems"
              :key="'rollover-' + item.id"
              class="hw-swipe-cell hw-swipe-cell--rollover"
            >
              <!-- 卡片正面：iOS 规范三行排版，点击打开详情，右侧胶囊直接打卡 -->
              <div
                class="st-card hw-card-face"
                :class="{ 'is-done': item.is_completed }"
                @click="openDetail(item)"
              >
                <!-- 学科徽标 -->
                <SubjectBadge :name="item.subject_name" size="md" />

                <!-- 标题与学科信息 (三行垂直流) -->
                <div class="hw-content">
                  <div class="hw-meta-row">
                    <span class="hw-subject-text">{{ item.subject_name }}</span>
                    <span class="rollover-origin-tag">周五顺延</span>
                  </div>
                  <div class="hw-title" :class="{ strike: item.is_completed }">
                    {{ item.content }}
                  </div>
                  <div class="hw-time-meta">
                    <span class="hw-time-text">
                      <van-icon name="underway-o" size="11" />
                      布置时间: {{ formatSimpleTime(item.created_at || item.date) }}
                    </span>
                    <span class="hw-done-time" v-if="item.completed_at">
                      · {{ item.completed_at.substring(11, 16) }} 打卡
                    </span>
                  </div>
                </div>

                <!-- 状态指示胶囊 -->
                <div
                  class="hw-status-pill"
                  :class="{ 'is-done': item.is_completed }"
                  @click.stop="toggleComplete(item)"
                  title="点击快捷打卡"
                >
                  <van-icon v-if="item.is_completed" name="success" size="12" />
                  <span>{{ item.is_completed ? '已完成' : '未完成' }}</span>
                </div>
              </div>

              <!-- 左滑展开的抽屉操作按钮 (编辑 + 转错题 + 删除) -->
              <template #right>
                <div class="swipe-actions-box">
                  <button class="swipe-action-btn btn-edit" @click.stop="openEditModal(item)">
                    <van-icon name="edit" size="15" />
                    <span>编辑</span>
                  </button>
                  <button class="swipe-action-btn btn-mistake" @click.stop="handleToMistake(item)">
                    <van-icon name="plus" size="15" />
                    <span>转错题</span>
                  </button>
                  <button class="swipe-action-btn btn-delete" @click.stop="handleDelete(item)">
                    <van-icon name="delete-o" size="15" />
                    <span>删除</span>
                  </button>
                </div>
              </template>
            </van-swipe-cell>
          </div>
        </div>

        <!-- 分区2：今日独立任务/当日作业 -->
        <div class="today-section" v-if="filteredItems.length > 0">
          <div class="list-section-header" :class="{ 'with-top-margin': filteredRolloverItems.length > 0 }">
            <div class="list-title-box">
              <span class="st-icon-badge st-icon-badge--primary">
                <van-icon name="todo-list-o" />
              </span>
              <span class="section-title">
                {{ filteredRolloverItems.length > 0 ? '今日独立任务' : (subTab === 'today' ? '待办作业' : (subTab === 'all' ? '全部任务' : '已完成任务')) }} ({{ filteredItems.length }} 项)
              </span>
            </div>
            <span class="swipe-hint" v-if="filteredRolloverItems.length === 0">
              <van-icon name="exchange" /> 左滑卡片呼出操作
            </span>
          </div>

          <div class="homework-cards">
            <van-swipe-cell
              v-for="item in filteredItems"
              :key="item.id"
              class="hw-swipe-cell"
            >
              <!-- 卡片正面：iOS 规范三行排版，点击打开详情，右侧胶囊直接打卡 -->
              <div
                class="st-card hw-card-face"
                :class="{ 'is-done': item.is_completed }"
                @click="openDetail(item)"
              >
                <!-- 学科徽标 -->
                <SubjectBadge :name="item.subject_name" size="md" />

                <!-- 标题与学科信息 (三行垂直流) -->
                <div class="hw-content">
                  <div class="hw-meta-row">
                    <span class="hw-subject-text">{{ item.subject_name }}</span>
                    <span class="rollover-origin-tag" v-if="item.is_weekend_rollover">周五顺延</span>
                  </div>
                  <div class="hw-title" :class="{ strike: item.is_completed }">
                    {{ item.content }}
                  </div>
                  <div class="hw-time-meta">
                    <span class="hw-time-text">
                      <van-icon name="underway-o" size="11" />
                      布置时间: {{ formatSimpleTime(item.created_at || item.date) }}
                    </span>
                    <span class="hw-done-time" v-if="item.completed_at">
                      · {{ item.completed_at.substring(11, 16) }} 打卡
                    </span>
                  </div>
                </div>

                <!-- 状态指示胶囊 -->
                <div
                  class="hw-status-pill"
                  :class="{ 'is-done': item.is_completed }"
                  @click.stop="toggleComplete(item)"
                  title="点击快捷打卡"
                >
                  <van-icon v-if="item.is_completed" name="success" size="12" />
                  <span>{{ item.is_completed ? '已完成' : '未完成' }}</span>
                </div>
              </div>

              <!-- 左滑展开的抽屉操作按钮 (编辑 + 转错题 + 删除) -->
              <template #right>
                <div class="swipe-actions-box">
                  <button class="swipe-action-btn btn-edit" @click.stop="openEditModal(item)">
                    <van-icon name="edit" size="15" />
                    <span>编辑</span>
                  </button>
                  <button class="swipe-action-btn btn-mistake" @click.stop="handleToMistake(item)">
                    <van-icon name="plus" size="15" />
                    <span>转错题</span>
                  </button>
                  <button class="swipe-action-btn btn-delete" @click.stop="handleDelete(item)">
                    <van-icon name="delete-o" size="15" />
                    <span>删除</span>
                  </button>
                </div>
              </template>
            </van-swipe-cell>
          </div>
        </div>
      </div>

      <!-- 清爽空状态 -->
      <div class="empty-box" v-else>
        <van-empty :description="subTab === 'today' ? '今天没有待办作业，享受一下自由时光吧 ☀️' : (subTab === 'all' ? '太棒了，当前没有未完成的作业！' : '暂无历史打卡记录')" />
      </div>
    </van-pull-refresh>

    <!-- 底部常驻磨砂悬浮录入栏 (居中大胶囊录入 + 专注计时) -->
    <div class="floating-bottom-bar st-frosted-bar">
      <button class="big-add-hw-btn" @click="showAddModal = true">
        <van-icon name="plus" size="16" />
        <span>录入作业</span>
      </button>
      <button
        class="pomodoro-mini-btn"
        :class="{ 'is-running': pomodoroRef?.isRunning }"
        @click="pomodoroRef?.open()"
        title="专注计时"
      >
        <van-icon name="underway-o" size="16" />
        <span v-if="pomodoroRef?.isRunning">{{ pomodoroRef?.formattedTime }}</span>
      </button>
    </div>

    <!-- iOS 规范作业详情底抽屉 -->
    <HomeworkDetailSheet
      v-model="showDetailSheet"
      :homework="selectedHomework"
      @toggle-complete="toggleComplete"
      @edit="openEditModal"
      @to-mistake="handleToMistake"
      @delete="handleDelete"
    />

    <!-- 录入作业底部半屏抽屉 (支持手动 / 拍照 OCR 识别批量录入) -->
    <QuickAddModal
      v-model:show="showAddModal"
      :subjects="subjects"
      :date-str="currentDate"
      @added="handleHomeworkAdded"
    />

    <!-- 月历打卡浮窗组件 -->
    <CalendarModal
      v-model:show="showCalendar"
      :selected-date="currentDate"
      @select-date="handleDateSelect"
    />

    <!-- 25分钟专注番茄钟 (hideFloatingBall=true，由底部并列入口驱动) -->
    <PomodoroTimer ref="pomodoroRef" :hide-floating-ball="true" />

    <!-- 打卡仪式感祝贺弹窗 -->
    <CheckinCelebrateModal
      v-model="showCelebrateModal"
      :streak="streak"
      :is-all-done="isAllDone"
    />

    <!-- 作业编辑弹窗 -->
    <van-dialog
      v-model:show="showEditModal"
      title="修改作业内容"
      show-cancel-button
      confirm-button-text="保存修改"
      @confirm="submitEditHomework"
    >
      <div style="padding: 1rem 1rem 0.5rem;">
        <div style="margin-bottom: 8px; font-size: var(--st-font-xs); color: var(--st-text-secondary);">
          所属学科：<span class="st-subject-tag" :class="getSubjectTagClass(editingItem?.subject_name)">{{ editingItem?.subject_name }}</span>
        </div>
        <van-field
          v-model="editContent"
          type="textarea"
          rows="3"
          autosize
          placeholder="请输入修改后的作业内容"
          class="homework-input-field"
        />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { showToast, showConfirmDialog } from 'vant';
import { homeworkApi, settingsApi } from '../api';
import QuickAddModal from '../components/QuickAddModal.vue';
import CalendarModal from '../components/CalendarModal.vue';
import PomodoroTimer from '../components/PomodoroTimer.vue';
import SubjectBadge from '../components/SubjectBadge.vue';
import CheckinCelebrateModal from '../components/CheckinCelebrateModal.vue';
import HomeworkDetailSheet from '../components/HomeworkDetailSheet.vue';

const pomodoroRef = ref(null);
const currentDate = ref(new Date().toISOString().split('T')[0]);
const streak = ref(0);
const totalCount = ref(0);
const completedCount = ref(0);
const rate = ref(0);
const items = ref([]);
const weekendRollover = ref(null);
const subjects = ref([]);
const selectedSubject = ref(null);
const refreshing = ref(false);
const showAddModal = ref(false);
const showCalendar = ref(false);
const showEditModal = ref(false);
const showCelebrateModal = ref(false);
const isAllDone = ref(false);
const editingItem = ref(null);
const editContent = ref('');
const calendarStatusMap = ref({});

// 专属详情抽屉与子标签状态
const subTab = ref('today'); // 'today' | 'all' | 'history'
const selectedHomework = ref(null);
const showDetailSheet = ref(false);

const openDetail = (item) => {
  selectedHomework.value = item;
  showDetailSheet.value = true;
};

const formatSimpleTime = (t) => {
  if (!t) return '--:--';
  try {
    const d = new Date(t);
    if (isNaN(d.getTime())) return t;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  } catch (e) {
    return t;
  }
};

const switchSubTab = (tab) => {
  subTab.value = tab;
  if (tab === 'today') {
    fetchHomework();
  } else if (tab === 'all') {
    fetchAllHomework();
  } else if (tab === 'history') {
    fetchHistoryHomework();
  }
};

const fetchAllHomework = async () => {
  refreshing.value = true;
  try {
    const res = await homeworkApi.getList({ scope: 'all' });
    items.value = res.data.items || [];
    totalCount.value = res.data.total || 0;
    completedCount.value = 0;
    rate.value = 0;
    weekendRollover.value = null;
  } catch (err) {
    showToast('获取全部作业失败');
  } finally {
    refreshing.value = false;
  }
};

const fetchHistoryHomework = async () => {
  refreshing.value = true;
  try {
    const res = await homeworkApi.getList({ scope: 'history' });
    items.value = res.data.items || [];
    totalCount.value = res.data.total || 0;
    completedCount.value = res.data.completed || 0;
    rate.value = 100;
    weekendRollover.value = null;
  } catch (err) {
    showToast('获取历史记录失败');
  } finally {
    refreshing.value = false;
  }
};

const isToday = computed(() => {
  return currentDate.value === new Date().toISOString().split('T')[0];
});

// 计算以当前选中日期为锚点的周历条 (Mon ~ Sun)，格式如 9/20 对齐 chatgpt.jpg
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
      dateNumber: `${d.getMonth() + 1}/${d.getDate()}`,
      isToday: dateStr === todayStr,
      isSelected: dateStr === currentDate.value,
      status: calendarStatusMap.value[dateStr] || 'gray'
    });
  }
  return list;
});

// 批量抓取周历涉及月份的打卡状态点
const fetchWeekStatus = async () => {
  const months = new Set();
  weekDays.value.forEach((day) => {
    months.add(day.dateStr.substring(0, 7));
  });

  try {
    for (const m of months) {
      const res = await homeworkApi.getCalendar(m);
      if (res.data?.days) {
        res.data.days.forEach((d) => {
          calendarStatusMap.value[d.date] = d.status;
        });
      }
    }
  } catch (err) {
    console.error('Failed to fetch week status:', err);
  }
};

// 学科展示优先级权重（语文 -> 数学 -> 英语 -> 道法 -> 历史 -> 地理 -> 生物 -> 物理 -> 化学）
const getSubjectSortOrder = (subjectId, subjectName) => {
  if (subjects.value && subjects.value.length > 0) {
    const found = subjects.value.find((s) => s.id === subjectId || s.name === subjectName);
    if (found && found.sort_order !== undefined) {
      return found.sort_order;
    }
  }
  const defaultOrder = ['语文', '数学', '英语', '道德与法治', '道法', '政治', '历史', '地理', '生物', '物理', '化学'];
  const idx = defaultOrder.indexOf(subjectName);
  return idx !== -1 ? idx : 999;
};

// 排序函数：优先按学科归类排序，学科内部按创建录入先后 (id) 正序排列
const sortHomeworkItems = (itemList) => {
  if (!itemList || itemList.length === 0) return [];
  return [...itemList].sort((a, b) => {
    const orderA = getSubjectSortOrder(a.subject_id, a.subject_name);
    const orderB = getSubjectSortOrder(b.subject_id, b.subject_name);
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    return a.id - b.id;
  });
};

const filteredItems = computed(() => {
  const base = !selectedSubject.value 
    ? items.value 
    : items.value.filter((i) => i.subject_id === selectedSubject.value);
  return sortHomeworkItems(base);
});

const filteredRolloverItems = computed(() => {
  if (!weekendRollover.value || !weekendRollover.value.items) return [];
  const base = !selectedSubject.value 
    ? weekendRollover.value.items 
    : weekendRollover.value.items.filter((i) => i.subject_id === selectedSubject.value);
  return sortHomeworkItems(base);
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
    case '道法':
    case '政治': return 'st-subject-tag--danger';
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
  fetchWeekStatus();
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
  fetchWeekStatus();
};

const handleHomeworkAdded = async () => {
  await fetchHomework();
  await fetchWeekStatus();
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
  if (subTab.value === 'all') return fetchAllHomework();
  if (subTab.value === 'history') return fetchHistoryHomework();

  refreshing.value = true;
  try {
    const res = await homeworkApi.getList(currentDate.value);
    totalCount.value = res.data.total;
    completedCount.value = res.data.completed;
    rate.value = res.data.rate;
    streak.value = res.data.streak;
    items.value = res.data.items;
    weekendRollover.value = res.data.weekend_rollover || null;

    // 实时更新当前日期的打卡状态点
    let currentStatus = 'gray';
    if (totalCount.value > 0) {
      if (completedCount.value === totalCount.value) {
        currentStatus = 'green';
      } else if (completedCount.value > 0) {
        currentStatus = 'yellow';
      } else {
        currentStatus = 'red';
      }
    }
    calendarStatusMap.value[currentDate.value] = currentStatus;
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
      item.completed_at = new Date().toISOString();
      isAllDone.value = (completedCount.value + 1 >= totalCount.value && totalCount.value > 0);
      showCelebrateModal.value = true;
    } else {
      item.completed_at = null;
    }

    // 联动详情抽屉内部状态
    if (selectedHomework.value && selectedHomework.value.id === item.id) {
      selectedHomework.value.is_completed = targetStatus;
      selectedHomework.value.completed_at = item.completed_at;
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

const openEditModal = (item) => {
  editingItem.value = item;
  editContent.value = item.content;
  showEditModal.value = true;
};

const submitEditHomework = async () => {
  if (!editContent.value || !editContent.value.trim()) {
    showToast('作业内容不可为空');
    return;
  }
  try {
    await homeworkApi.update(editingItem.value.id, { content: editContent.value.trim() });
    showToast({ message: '作业已修改', icon: 'success' });
    showEditModal.value = false;
    fetchHomework();
  } catch (e) {
    showToast('修改失败');
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
  await fetchWeekStatus();
});
</script>

<style scoped>
.homework-view {
  flex: 1;
  background-color: var(--st-bg-page, #f8fafc);
  padding: 12px 14px 100px;
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
  font-size: var(--st-font-xl);
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
  flex-shrink: 0;
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-title {
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
  line-height: var(--st-leading-tight);
  letter-spacing: -0.2px;
}

.brand-subtitle {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: var(--st-primary, #2563eb);
  letter-spacing: 0.5px;
  line-height: 1;
  margin-top: 1px;
}

.homework-top-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--st-text-primary, #0f172a);
  margin: 0;
  letter-spacing: -0.5px;
}

/* iOS 规范子标签栏 */
.homework-sub-tabs {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 0 4px 10px;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 12px;
}

.sub-tab-item {
  position: relative;
  background: transparent;
  border: none;
  font-size: 15px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  padding: 4px 0 8px;
  transition: all 0.2s ease;
}

.sub-tab-item.active {
  font-weight: 700;
  color: #0f172a;
}

.sub-tab-indicator {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 22px;
  height: 3px;
  border-radius: 9999px;
  background: #2563eb;
}

/* 全部/历史统计条 */
.scope-summary-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 14px;
}

.scope-summary-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scope-badge-count {
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  padding: 3px 10px;
  border-radius: 9999px;
}

.add-top-round-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  transition: transform 0.15s ease;
  flex-shrink: 0;
}

.add-top-round-btn:active {
  transform: scale(0.92);
}

.hw-subject-text {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.streak-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  font-size: var(--st-font-xs);
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
  color: var(--st-text-secondary);
  font-size: var(--st-font-xs);
  font-weight: 500;
  box-shadow: var(--st-shadow-card, 0 1px 3px rgba(15, 23, 42, 0.04));
  cursor: pointer;
  transition: all 0.15s ease;
}

.calendar-pill-btn:hover {
  border-color: var(--st-primary, #2563eb);
  color: var(--st-primary, #2563eb);
}

/* 顶部 7 日横向胶囊日历条 (纯蓝实心白字胶囊，对齐 chatgpt.jpg) */
.week-strip-box {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
  margin-bottom: 12px;
}

.week-day-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 2px 5px;
  min-height: 52px;
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.week-day-pill.active {
  background-color: #2563eb;
  border-color: #2563eb;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
}

.week-day-pill .day-label {
  font-size: 11px;
  line-height: 1;
  color: #64748b;
  margin-bottom: 4px;
}

.week-day-pill.active .day-label {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
}

.week-day-pill .day-number {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.1;
  color: #1e293b;
}

.week-day-pill.active .day-number {
  color: #ffffff;
  font-weight: 700;
}

.week-day-pill .day-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  margin-top: 3px;
  display: inline-block;
  flex-shrink: 0;
}

.week-day-pill .day-dot.dot-green {
  background-color: #10b981;
}

.week-day-pill .day-dot.dot-yellow {
  background-color: #f59e0b;
}

.week-day-pill .day-dot.dot-red {
  background-color: #ef4444;
}

.week-day-pill .day-dot.dot-gray {
  background-color: #cbd5e1;
}

/* 选中高亮状态下的状态指示点 */
.week-day-pill.active .day-dot {
  background-color: #ffffff !important;
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
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
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
  font-size: var(--st-font-xs);
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
  flex-wrap: wrap;
  gap: 2px 8px;
  margin-bottom: 10px;
  padding: 0 4px;
}

.list-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-title {
  font-size: var(--st-font-lg);
  font-weight: 600;
  color: var(--st-text-primary);
}

.swipe-hint {
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  /* 窄屏下不许被标题挤到换行（「左滑操作」竖排很难看），放不下就整行下移 */
  white-space: nowrap;
  flex-shrink: 0;
}

.homework-list-wrapper {
  padding-bottom: 12px;
}

.rollover-section {
  margin-bottom: 16px;
}

.rollover-header {
  margin-bottom: 8px;
}

.rollover-title-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.rollover-badge-tag {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: #7c3aed;
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
  padding: 2px 8px;
  border-radius: var(--st-radius-full, 9999px);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.rollover-origin-tag {
  font-size: var(--st-font-xs);
  font-weight: 600;
  color: #7c3aed;
  background: #ede9fe;
  padding: 1px 6px;
  border-radius: 4px;
  line-height: var(--st-leading-tight);
}

.hw-swipe-cell--rollover .hw-card-face {
  border-left: 3.5px solid #8b5cf6;
}

.list-section-header.with-top-margin {
  margin-top: 14px;
}

.homework-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hw-swipe-cell {
  border-radius: 16px;
  overflow: hidden;
}

.hw-card-face {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.7);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
  transition: transform 0.15s ease, background 0.15s ease;
  background-color: #ffffff;
}

.hw-card-face:active {
  transform: scale(0.985);
  background-color: #f8fafc;
}

.hw-card-face.is-done {
  background-color: #fafbfc;
  opacity: 0.88;
}

.hw-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hw-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hw-subject-text {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.hw-title {
  font-size: 13.5px;
  font-weight: 500;
  color: #334155;
  line-height: 1.4;
  word-break: break-all;
}

.hw-title.strike {
  color: #94a3b8;
  text-decoration: line-through;
}

.hw-time-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
}

.hw-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  background: #f1f5f9;
  color: #64748b;
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.hw-status-pill:active {
  transform: scale(0.95);
}

.hw-status-pill.is-done {
  background: #ecfdf5;
  color: #10b981;
  font-weight: 600;
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
  font-size: var(--st-font-xs);
  font-weight: 500;
  cursor: pointer;
}

.swipe-action-btn.btn-edit {
  background-color: var(--st-warning, #f59e0b);
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
  width: 20px;
  height: 44px;
  border: none;
  background: transparent;
  color: var(--st-text-muted);
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

/* 底部常驻悬浮栏 (居中大胶囊录入 + 专注圆钮，与 chatgpt.jpg 保持一致) */
.floating-bottom-bar {
  position: fixed;
  bottom: calc(52px + env(safe-area-inset-bottom, 0px));
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 8px 16px;
  background: linear-gradient(to top, rgba(248, 250, 252, 0.96) 80%, rgba(248, 250, 252, 0));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 40;
}

.big-add-hw-btn {
  flex: 1;
  height: 46px;
  border-radius: 9999px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.32);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.big-add-hw-btn:active {
  transform: scale(0.98);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
}

.pomodoro-mini-btn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.pomodoro-mini-btn:active {
  transform: scale(0.94);
  background: #f1f5f9;
}

.pomodoro-mini-btn.is-running {
  width: auto;
  padding: 0 14px;
  border-radius: 9999px;
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}
</style>
