<template>
  <div class="today-view">
    <!-- 1. 顶部温和生活感问候区 (像素级复刻 Image 2) -->
    <header class="greeting-header">
      <div class="greeting-text">
        <h1 class="greeting-title">{{ timeGreeting }}，同学</h1>
        <p class="greeting-date">{{ formattedDate }}</p>
      </div>
      <button class="greeting-illustration" type="button" aria-label="进入我的页面" @click="$router.push('/settings')">
        <!-- 伏案学习男孩矢量插图 (高度复刻 Image 2 绿植、课桌、书本、写字学生) -->
        <svg viewBox="0 0 160 110" fill="none" class="student-study-illustration">
          <!-- 绿植与陶盆 (右侧后景) -->
          <g class="plant-group">
            <path d="M138 68 L152 68 L149 84 L141 84 Z" fill="#f97316" />
            <rect x="136" y="65" width="18" height="3" rx="1.5" fill="#ea580c" />
            <path d="M144 65 C140 50, 126 52, 132 40 C138 48, 146 54, 145 65 Z" fill="#22c55e" />
            <path d="M147 65 C152 48, 162 48, 158 38 C150 45, 147 55, 147 65 Z" fill="#16a34a" />
            <path d="M145 55 C143 38, 148 28, 145 22 C141 30, 142 42, 145 55 Z" fill="#4ade80" />
          </g>

          <!-- 木质暖色书桌 -->
          <ellipse cx="115" cy="88" rx="45" ry="8" fill="#fde68a" />
          <rect x="70" y="85" width="90" height="7" rx="3.5" fill="#fed7aa" />

          <!-- 左侧立式蓝色收纳书立 -->
          <path d="M78 85 L85 64 L93 67 L88 85 Z" fill="#60a5fa" />
          <path d="M84 85 L88 66 L93 67 L88 85 Z" fill="#93c5fd" />

          <!-- 桌面开敞笔记本 -->
          <polygon points="98,82 128,82 125,87 95,87" fill="#ffffff" stroke="#e2e8f0" stroke-width="1" />
          <line x1="102" y1="84" x2="122" y2="84" stroke="#93c5fd" stroke-width="0.8" />

          <!-- 男孩身体 (蓝毛衣) -->
          <path d="M96 90 C96 74, 134 74, 134 90 Z" fill="#2563eb" />
          <!-- 白色衬衫领 -->
          <path d="M111 73 L115 79 L119 73 Z" fill="#ffffff" />

          <!-- 伏案写字手臂与铅笔 -->
          <path d="M100 86 C105 82, 114 83, 118 84" stroke="#2563eb" stroke-width="5" stroke-linecap="round" />
          <circle cx="119" cy="84" r="3" fill="#fed7aa" />
          <line x1="117" y1="85" x2="114" y2="78" stroke="#1e293b" stroke-width="1.8" stroke-linecap="round" />

          <!-- 颈部与脸蛋 -->
          <rect x="112" y="65" width="6" height="8" fill="#fed7aa" />
          <circle cx="115" cy="55" r="14" fill="#fed7aa" />

          <!-- 腮红 -->
          <ellipse cx="106" cy="59" rx="2.5" ry="1.5" fill="#fca5a5" opacity="0.8" />
          <ellipse cx="124" cy="59" rx="2.5" ry="1.5" fill="#fca5a5" opacity="0.8" />

          <!-- 弯弯黑眼与清澈高光 -->
          <circle cx="108" cy="54" r="1.6" fill="#1e293b" />
          <circle cx="122" cy="54" r="1.6" fill="#1e293b" />
          <circle cx="108.6" cy="53.4" r="0.6" fill="#ffffff" />
          <circle cx="122.6" cy="53.4" r="0.6" fill="#ffffff" />
          <!-- 亲切微笑 -->
          <path d="M112 60 Q115 63 118 60" stroke="#1e293b" stroke-width="1.2" stroke-linecap="round" fill="none" />

          <!-- 柔和蓬松黑发 -->
          <path d="M100 50 C98 38, 110 32, 122 34 C132 36, 132 46, 128 53 C126 46, 122 43, 116 43 C110 43, 106 46, 104 53 Z" fill="#1e293b" />
          <path d="M102 46 C98 42, 97 34, 106 36 Z" fill="#1e293b" />
          <path d="M125 40 C131 38, 134 44, 129 48 Z" fill="#1e293b" />
        </svg>
      </button>
    </header>

    <main class="today-content">
      <!-- 2. 数据概览 2 列网格 (严格复刻 Image 3 文字、数字比例、图标) -->
      <section class="overview-grid">
        <!-- 左侧：今日完成率 Donut 环形图卡片 -->
        <button class="st-card donut-card" type="button" aria-label="查看今日作业进度" @click="$router.push('/homework')">
          <div class="progress-copy">
            <span class="card-label">今天的进度</span>
            <span class="progress-caption">{{ totalCount > 0 ? `已完成 ${completedCount} 项作业` : '还没有安排作业' }}</span>
          </div>
          <div class="donut-container">
            <svg class="donut-svg" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="donut-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="var(--st-primary)" />
                  <stop offset="100%" stop-color="var(--st-primary-dark)" />
                </linearGradient>
              </defs>
              <circle
                class="donut-bg"
                cx="50"
                cy="50"
                r="42"
                stroke-width="10"
              />
              <circle
                class="donut-fill"
                cx="50"
                cy="50"
                r="42"
                stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="progressOffset"
              />
            </svg>
            <div class="donut-inner-text">
              <span class="donut-percent">{{ completionRate }}%</span>
              <span class="donut-fraction">{{ completedCount }}/{{ totalCount }} 项</span>
            </div>
          </div>
        </button>

        <!-- 右侧：双层微型统计卡片 -->
        <div class="stats-column">
          <!-- 连续学习卡片 -->
          <button class="st-card mini-stat-card" type="button" aria-label="查看连续学习记录" @click="$router.push('/homework')">
            <div class="stat-card-inner">
              <div class="stat-icon-box stat-icon-fire">
                <svg viewBox="0 0 24 24" class="stat-svg-icon" fill="none">
                  <path d="M12 2C10 5.5 12 8 10 11C8.5 9 8 7 8 7C5 10.5 4 14 6 18C8 22 16 22 18 18C20 14 17 8 12 2Z" fill="url(#fire-grad)" />
                  <path d="M12 20C10.5 20 8.5 18.5 9 16C9.5 13.5 12 13 12 11C13 13 15 14.5 15 16C15 18.5 13.5 20 12 20Z" fill="#fed7aa" />
                  <defs>
                    <linearGradient id="fire-grad" x1="12" y1="2" x2="12" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#f97316"/>
                      <stop offset="1" stop-color="#ea580c"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div class="stat-content">
                <div class="stat-label-row">
                  <span class="stat-label">连续学习</span>
                  <van-icon name="arrow" class="stat-chevron" />
                </div>
                <div class="stat-value-row">
                  <span class="stat-num">{{ streakDays }}</span>
                  <span class="stat-unit">天</span>
                </div>
              </div>
            </div>
          </button>

          <!-- 今日学习时长卡片 -->
          <button class="st-card mini-stat-card" type="button" aria-label="打开专注计时器" @click="openPomodoro">
            <div class="stat-card-inner">
              <div class="stat-icon-box stat-icon-time">
                <svg viewBox="0 0 24 24" class="stat-svg-icon" fill="none">
                  <circle cx="12" cy="12" r="10" fill="#3b82f6"/>
                  <path d="M12 7V12L15 14" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div class="stat-content">
                <div class="stat-label-row">
                  <span class="stat-label">今日学习时长</span>
                  <van-icon name="arrow" class="stat-chevron" />
                </div>
                <div class="stat-value-row">
                  <template v-if="studyDurationParts.isZero">
                    <span class="stat-num">0</span>
                    <span class="stat-unit">分钟</span>
                  </template>
                  <template v-else>
                    <template v-if="studyDurationParts.hasHours">
                      <span class="stat-num">{{ studyDurationParts.hours }}</span>
                      <span class="stat-unit">小时</span>
                    </template>
                    <span class="stat-num">{{ studyDurationParts.mins }}</span>
                    <span class="stat-unit">分钟</span>
                  </template>
                </div>
              </div>
            </div>
          </button>
        </div>
      </section>

      <!-- 3. 今日任务整体卡片容器 (严格复刻 Image 4 单一白底卡片 + 14px/12px 小巧精致字号) -->
      <section class="today-tasks-section">
        <div class="section-top-bar">
          <h2 class="section-title">今日任务</h2>
          <button class="view-all-btn" @click="$router.push('/homework')">
            查看全部 <van-icon name="arrow" />
          </button>
        </div>

        <!-- 整合到统一白底大卡片中 -->
        <div class="st-card tasks-grouped-card">
          <!-- 任务列表为空状态 -->
          <div v-if="loading" class="tasks-loading-box" aria-label="正在加载今日作业">
            <van-skeleton title :row="2" />
          </div>
          <div v-else-if="todayLoadError" class="tasks-state-box" role="status">
            <van-icon name="warning-o" class="tasks-state-icon" />
            <p class="empty-title">今日作业暂时未能加载</p>
            <p class="empty-subtitle">请检查网络后重新加载。</p>
            <button class="empty-focus-button" type="button" @click="fetchTodayHomework">重新加载</button>
          </div>
          <div v-else-if="tasks.length === 0" class="empty-tasks-box">
            <van-icon name="underway-o" class="empty-focus-icon" />
            <p class="empty-title">今天安排得很从容</p>
            <p class="empty-subtitle">留出 25 分钟，做一次安静的专注吧。</p>
            <button class="empty-focus-button" type="button" @click="openPomodoro">开始专注</button>
          </div>

          <!-- 任务列表行 -->
          <div v-else class="tasks-rows-list">
            <div
              v-for="(task, index) in displayedTasks"
              :key="task.id"
              class="task-row-item"
              :class="{ 'is-completed': task.is_completed, 'is-last': index === displayedTasks.length - 1 }"
            >
              <button class="task-left" type="button" :aria-label="`查看${task.subject_name}作业详情`" @click="openTaskDetail(task)">
                <SubjectBadge :name="task.subject_name" size="sm" />
                <div class="task-details">
                  <div class="task-subject-title">{{ task.subject_name }}</div>
                  <div class="task-content-text" :class="{ 'is-done': task.is_completed }">
                    {{ task.content }}
                  </div>
                </div>
              </button>

              <!-- 右侧打卡勾选按钮 (阻止冒泡) -->
              <button
                class="checkin-toggle-btn"
                :class="{ 'checked': task.is_completed }"
                :disabled="taskToggling === task.id"
                @click.stop="toggleTaskCheck(task)"
                :aria-label="task.is_completed ? '已完成' : '打卡'"
              >
                <template v-if="task.is_completed">
                  <!-- 复刻 Image 4 绿色圆点勾勾 + 已完成文字 -->
                  <span class="completed-pill">
                    <svg viewBox="0 0 16 16" class="completed-check-dot" fill="none">
                      <circle cx="8" cy="8" r="7" fill="#10b981" />
                      <path d="M5 8.2L7 10.2L11 6" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <span>已完成</span>
                  </span>
                </template>
                <template v-else>
                  <!-- 18px 浅灰细圈 -->
                  <span class="uncompleted-circle"></span>
                </template>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 4. 今日错题复习入口横幅 -->
      <button class="mistake-review-banner st-card" type="button" aria-label="进入今日错题复习" @click="goToMistakesReview">
        <div class="banner-left">
          <div class="banner-target-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="6" />
              <circle cx="12" cy="12" r="2" fill="currentColor" />
            </svg>
          </div>
          <div class="banner-text">
            <h3 class="banner-title">今日错题复习</h3>
            <p class="banner-subtitle">
              {{ reviewQueueCount > 0 ? `还有 ${reviewQueueCount} 道题需要复习` : '今日错题已全部清空，太棒了！' }}
            </p>
          </div>
        </div>
        <span class="banner-action-btn">
          {{ reviewQueueCount > 0 ? '开始复习' : '去错题本' }} <van-icon name="arrow" />
        </span>
      </button>

      <!-- 5. 学习时长分布卡片 (动态联动) -->
      <section class="study-distribution-card st-card">
        <div class="dist-header">
          <h3 class="dist-title">学习时长分布</h3>
          <span class="dist-total">{{ formattedStudyDuration }}</span>
        </div>

        <div class="dist-bars-list">
          <div
            v-for="item in subjectDistribution"
            :key="item.name"
            class="dist-row"
          >
            <div class="dist-subject">
              <span class="dist-color-dot" :style="{ backgroundColor: item.color }"></span>
              <span class="dist-subject-name">{{ item.name }}</span>
            </div>
            <div class="dist-bar-track">
              <div
                class="dist-bar-fill"
                :style="{ width: `${item.percentage}%`, backgroundColor: item.color }"
              ></div>
            </div>
            <span class="dist-duration">{{ item.durationText }}</span>
          </div>
        </div>
      </section>
    </main>

    <!-- 6. 底部双悬浮快速录入操作胶囊 (精细复刻配图蓝色微质感胶囊与防漂移定位) -->
    <aside class="floating-quick-actions">
      <button class="quick-fab-btn" @click="showAddModal = true">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" class="fab-svg-icon">
          <path d="M4 8C4 6.89543 4.89543 6 6 6H7.58579C8.11622 6 8.62493 5.78929 9 5.41421L9.58579 4.82843C9.96086 4.45336 10.4696 4.24264 11 4.24264H13C13.5304 4.24264 14.0391 4.45336 14.4142 4.82843L15 5.41421C15.3751 5.78929 15.8838 6 16.4142 6H18C19.1046 6 20 6.89543 20 8V17C20 18.1046 19.1046 19 18 19H6C4.89543 19 4 18.1046 4 17V8Z" fill="#2563eb" />
          <circle cx="12" cy="12.5" r="3.2" fill="#ffffff" />
          <circle cx="12" cy="12.5" r="1.6" fill="#2563eb" />
        </svg>
        <span>录入作业</span>
      </button>
      <button class="quick-fab-btn" @click="$router.push('/mistakes?action=add')">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" class="fab-svg-icon">
          <path d="M6 3C4.89543 3 4 3.89543 4 5V19C4 20.1046 4.89543 21 6 21H18C19.1046 21 20 20.1046 20 19V9L14 3H6Z" fill="#2563eb" />
          <path d="M14 3V8C14 8.55228 14.4477 9 15 9H20" fill="#93c5fd" />
          <line x1="8" y1="13" x2="16" y2="13" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" />
          <line x1="8" y1="16.5" x2="13" y2="16.5" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <span>录入错题</span>
      </button>
    </aside>

    <!-- 7. 全局复用抽屉与弹窗组件 -->
    <QuickAddModal
      v-model:show="showAddModal"
      :subjects="subjects"
      :date-str="todayStr"
      @added="handleHomeworkAdded"
    />

    <PomodoroTimer ref="pomodoroRef" :hide-floating-ball="true" />

    <CheckinCelebrateModal
      v-model="showCelebrateModal"
      :streak="streakDays"
      :is-all-done="isAllDone"
      @confirm="onCelebrateConfirm"
    />

    <!-- iOS 规范作业详情半屏抽屉 -->
    <HomeworkDetailSheet
      v-model="showDetailSheet"
      :homework="selectedTask"
      @toggle-complete="handleDetailToggle"
      @edit="handleDetailEdit"
      @to-mistake="handleDetailToMistake"
      @delete="handleDetailDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { homeworkApi, mistakeApi, settingsApi } from '../api';
import SubjectBadge from '../components/SubjectBadge.vue';
import QuickAddModal from '../components/QuickAddModal.vue';
import PomodoroTimer from '../components/PomodoroTimer.vue';
import CheckinCelebrateModal from '../components/CheckinCelebrateModal.vue';
import HomeworkDetailSheet from '../components/HomeworkDetailSheet.vue';

const router = useRouter();

// 基础数据状态
const loading = ref(false);
const todayLoadError = ref(false);
const tasks = ref([]);
const subjects = ref([]);
const totalCount = ref(0);
const completedCount = ref(0);
const completionRate = ref(0);
const streakDays = ref(0);
const reviewQueueCount = ref(0);
const taskToggling = ref(null);

// 弹窗与详情状态
const showAddModal = ref(false);
const showCelebrateModal = ref(false);
const isAllDone = ref(false);
const pomodoroRef = ref(null);
const selectedTask = ref(null);
const showDetailSheet = ref(false);

const openTaskDetail = (task) => {
  selectedTask.value = task;
  showDetailSheet.value = true;
};

const handleDetailToggle = async (task) => {
  await toggleTaskCheck(task);
  if (selectedTask.value && selectedTask.value.id === task.id) {
    selectedTask.value.is_completed = task.is_completed;
    selectedTask.value.completed_at = task.completed_at;
  }
};

const handleDetailEdit = () => {
  showDetailSheet.value = false;
  router.push('/homework');
};

const handleDetailToMistake = async (task) => {
  try {
    await homeworkApi.toMistake(task.id);
    showToast({ message: '已归档至错题本草稿', icon: 'records-o' });
  } catch (e) {
    showToast('转错题失败');
  }
};

const handleDetailDelete = async (task) => {
  try {
    await homeworkApi.delete(task.id);
    showToast({ message: '作业已删除', position: 'bottom' });
    showDetailSheet.value = false;
    fetchTodayHomework();
  } catch (e) {
    showToast('删除失败');
  }
};

// 日期处理
const today = new Date();
const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

// 动态时间段问候 (Image 2)
const timeGreeting = computed(() => {
  const hour = today.getHours();
  if (hour >= 5 && hour < 12) return '早上好';
  if (hour >= 12 && hour < 14) return '中午好';
  if (hour >= 14 && hour < 18) return '下午好';
  return '晚上好';
});

// 中文日期格式化 (Image 2)
const formattedDate = computed(() => {
  const month = today.getMonth() + 1;
  const date = today.getDate();
  const dayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const dayName = dayNames[today.getDay()];
  return `今天是 ${month}月${date}日 ${dayName}`;
});

// SVG 环形进度条计算
const radius = 42;
const circumference = 2 * Math.PI * radius; // ~263.89
const progressOffset = computed(() => {
  const rate = Math.min(Math.max(completionRate.value, 0), 100);
  return circumference - (rate / 100) * circumference;
});

// 任务智能排序：未完成在前、已完成在后
const sortedTasks = computed(() => {
  return [...tasks.value].sort((a, b) => {
    if (Boolean(a.is_completed) === Boolean(b.is_completed)) return 0;
    return a.is_completed ? 1 : -1;
  });
});

// 全部任务直接呈现在可滚动的紧凑容器中
const displayedTasks = computed(() => sortedTasks.value);

// ==========================================
// 学习时长与学科分布科学动态统计
// ==========================================
const SUBJECT_BASELINE_MINUTES = {
  math: 35,      // 数学
  chinese: 30,   // 语文
  english: 25,   // 英语
  physics: 25,   // 物理
  chemistry: 25, // 化学
  biology: 20,   // 生物
  history: 20,   // 历史
  geography: 20, // 地理
  politics: 20,  // 道德与法治
  daofa: 20,
  other: 15      // 其他
};

const SUBJECT_COLORS = {
  math: '#3b82f6',     // 蓝
  chinese: '#10b981',  // 绿
  english: '#8b5cf6',  // 紫
  physics: '#f97316',  // 橙
  chemistry: '#06b6d4',// 青
  biology: '#84cc16',  // 黄绿
  history: '#d97706',  // 琥珀
  geography: '#0ea5e9',// 天蓝
  politics: '#ef4444', // 红
  daofa: '#ef4444',
  other: '#94a3b8'     // 灰
};

const getSubjectKey = (name) => {
  const n = (name || '').trim();
  if (n.includes('数')) return 'math';
  if (n.includes('语')) return 'chinese';
  if (n.includes('英')) return 'english';
  if (n.includes('物')) return 'physics';
  if (n.includes('化')) return 'chemistry';
  if (n.includes('生')) return 'biology';
  if (n.includes('地')) return 'geography';
  if (n.includes('历')) return 'history';
  if (n.includes('道') || n.includes('法') || n.includes('政')) return 'politics';
  return 'other';
};

// 本地番茄钟专注累计增量 (分钟)
const pomodoroMinutes = ref(0);

const loadPomodoroMinutes = () => {
  try {
    const key = `study_trace_pomodoro_${todayStr}`;
    pomodoroMinutes.value = parseInt(localStorage.getItem(key) || '0', 10);
  } catch (e) {
    pomodoroMinutes.value = 0;
  }
};

// 动态学习时长计算：打卡完成的作业学科基准用时 + 真实番茄专注用时
const totalStudyMinutes = computed(() => {
  let minutes = pomodoroMinutes.value;
  tasks.value.forEach(t => {
    if (t.is_completed) {
      const key = getSubjectKey(t.subject_name);
      minutes += (SUBJECT_BASELINE_MINUTES[key] || 15);
    }
  });
  return minutes;
});

// 用于 Image 3 样式的突出大数字与小单位解构
const studyDurationParts = computed(() => {
  const m = totalStudyMinutes.value;
  if (m <= 0) {
    return { hasHours: false, hours: 0, mins: 0, isZero: true };
  }
  const hours = Math.floor(m / 60);
  const mins = m % 60;
  return {
    hasHours: hours > 0,
    hours,
    mins,
    isZero: false
  };
});

const formattedStudyDuration = computed(() => {
  const m = totalStudyMinutes.value;
  if (m <= 0) return '0 分钟';
  const hours = Math.floor(m / 60);
  const mins = m % 60;
  if (hours > 0 && mins > 0) return `${hours}小时 ${mins}分钟`;
  if (hours > 0) return `${hours}小时`;
  return `${mins}分钟`;
});

// 动态计算学科时长分布 (打卡实时联动更新)
const subjectDistribution = computed(() => {
  const minutesBySubject = {};

  // 默认学科基准列表
  const defaultSubjects = ['数学', '语文', '英语', '其他'];
  const presentSubjectNames = Array.from(new Set(tasks.value.map(t => t.subject_name).filter(Boolean)));
  const orderedSubjectNames = presentSubjectNames.length > 0
    ? presentSubjectNames.slice(0, 4)
    : defaultSubjects;

  orderedSubjectNames.forEach(name => {
    minutesBySubject[name] = 0;
  });

  tasks.value.forEach(t => {
    if (t.is_completed && t.subject_name) {
      const key = getSubjectKey(t.subject_name);
      const mins = SUBJECT_BASELINE_MINUTES[key] || 15;
      if (minutesBySubject[t.subject_name] !== undefined) {
        minutesBySubject[t.subject_name] += mins;
      } else {
        minutesBySubject['其他'] = (minutesBySubject['其他'] || 0) + mins;
      }
    }
  });

  // 进度条满格基准值 (以最大分钟数或 60 分钟作为参考)
  const maxMins = Math.max(...Object.values(minutesBySubject), 60);

  return orderedSubjectNames.map(name => {
    const key = getSubjectKey(name);
    const mins = minutesBySubject[name] || 0;
    const color = SUBJECT_COLORS[key] || SUBJECT_COLORS.other;
    const percentage = maxMins > 0 ? Math.min(100, Math.round((mins / maxMins) * 100)) : 0;
    return {
      name,
      color,
      minutes: mins,
      percentage,
      durationText: `${mins} min`
    };
  });
});

// 加载今日作业与统计
const fetchTodayHomework = async () => {
  loading.value = true;
  todayLoadError.value = false;
  try {
    const res = await homeworkApi.getList(todayStr);
    const data = res.data;
    
    // 合并当日作业和周末顺延作业
    let allItems = [...(data.items || [])];
    if (data.weekend_rollover && Array.isArray(data.weekend_rollover.items)) {
      allItems = [...allItems, ...data.weekend_rollover.items];
    }
    tasks.value = allItems;
    totalCount.value = data.total || 0;
    completedCount.value = data.completed || 0;
    completionRate.value = data.rate || 0;
    streakDays.value = data.streak || 0;
  } catch (err) {
    console.error('获取今日作业失败:', err);
    todayLoadError.value = true;
  } finally {
    loading.value = false;
  }
};

// 加载学科
const fetchSubjects = async () => {
  try {
    const res = await settingsApi.getSubjects();
    subjects.value = res.data || [];
  } catch (e) {
    console.error('加载学科失败:', e);
  }
};

// 加载待复习错题数
const fetchReviewQueue = async () => {
  try {
    const res = await mistakeApi.getReviewQueue();
    reviewQueueCount.value = Array.isArray(res.data) ? res.data.length : 0;
  } catch (e) {
    console.error('加载待复习错题数失败:', e);
  }
};

// 切换作业打卡状态
const toggleTaskCheck = async (task) => {
  if (taskToggling.value) return;
  taskToggling.value = task.id;
  const targetCompleted = !task.is_completed;

  try {
    await homeworkApi.update(task.id, {
      is_completed: targetCompleted,
      content: task.content,
      subject_id: task.subject_id
    });

    task.is_completed = targetCompleted;
    if (targetCompleted) {
      completedCount.value += 1;
    } else {
      completedCount.value = Math.max(0, completedCount.value - 1);
    }
    completionRate.value = totalCount.value > 0 ? Math.round((completedCount.value / totalCount.value) * 100) : 0;

    // 若打卡完成，弹出祝贺弹窗
    if (targetCompleted) {
      isAllDone.value = completedCount.value === totalCount.value && totalCount.value > 0;
      showCelebrateModal.value = true;
    }
  } catch (err) {
    showToast('更新状态失败，请重试');
    task.is_completed = !targetCompleted; // 还原
  } finally {
    taskToggling.value = null;
  }
};

// 录入作业完成回调
const handleHomeworkAdded = () => {
  fetchTodayHomework();
};

// 庆祝弹窗关闭回调
const onCelebrateConfirm = () => {
  // 保持当前页
};

// 打开专注计时器
const openPomodoro = () => {
  pomodoroRef.value?.open();
};

// 跳转错题复习
const goToMistakesReview = () => {
  router.push('/mistakes?tab=review');
};

const onGlobalAction = (event) => {
  if (event.detail === 'homework') showAddModal.value = true;
  if (event.detail === 'focus') openPomodoro();
};

onMounted(() => {
  loadPomodoroMinutes();
  fetchTodayHomework();
  fetchSubjects();
  fetchReviewQueue();
  window.addEventListener('study_trace_pomodoro_completed', loadPomodoroMinutes);
  window.addEventListener('zhixueji:action', onGlobalAction);
});

onUnmounted(() => {
  window.removeEventListener('study_trace_pomodoro_completed', loadPomodoroMinutes);
  window.removeEventListener('zhixueji:action', onGlobalAction);
});
</script>

<style scoped>
/* 根容器：边距由 14px 收敛为 12px，底部留足悬浮胶囊与 Tabbar 避让空间，绝不遮挡末尾内容 */
.today-view {
  flex: 1;
  background-color: var(--st-bg-page);
  padding: var(--st-space-5) var(--st-space-5) calc(64px + env(safe-area-inset-bottom, 0px) + 60px);
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  position: relative;
}

/* 1. 顶部问候区 (Image 2) */
.greeting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  padding: 0 var(--st-space-1) var(--st-space-4);
}

.greeting-title {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
  letter-spacing: 0;
  line-height: 1.25;
  margin: 0 0 var(--st-space-1);
}

.greeting-date {
  font-size: var(--st-font-sm);
  color: var(--st-text-muted);
  font-weight: 500;
}

.greeting-illustration {
  width: 92px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.student-study-illustration {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 4px 12px rgba(37, 99, 235, 0.08));
}

/* 2. 数据概览网格 (Image 3) */
.overview-grid {
  display: block;
  margin-bottom: var(--st-space-6);
}

.donut-card {
  margin: 0;
  min-height: 112px;
  padding: var(--st-space-5);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  text-align: left;
  width: 100%;
  font: inherit;
  cursor: pointer;
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

.card-label {
  display: block;
  font-size: var(--st-font-lg);
  font-weight: 600;
  color: var(--st-text-primary);
}

.progress-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--st-space-2);
  min-width: 0;
}

.progress-caption {
  font-size: var(--st-font-sm);
  color: var(--st-text-secondary);
  line-height: var(--st-leading-normal);
}

.donut-container {
  position: relative;
  width: 82px;
  height: 82px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-bg {
  fill: none;
  stroke: var(--st-primary-light);
}

.donut-fill {
  fill: none;
  stroke: var(--st-primary);
  stroke: url(#donut-gradient);
  transition: stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.donut-inner-text {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-percent {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.donut-fraction {
  font-size: var(--st-font-xs);
  font-weight: 500;
  color: var(--st-text-muted);
  margin-top: var(--st-space-1);
}

.stats-column {
  display: none;
  flex-direction: column;
  gap: 10px;
}

.mini-stat-card {
  margin: 0;
  padding: 10px 12px;
  flex: 1;
  display: flex;
  align-items: center;
  cursor: pointer;
  width: 100%;
  text-align: left;
  font: inherit;
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
  transition: transform 0.15s ease;
}

.mini-stat-card:active {
  transform: scale(0.98);
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.stat-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-fire {
  background: var(--st-warning-light);
}

.stat-icon-time {
  background: var(--st-primary-light);
}

.stat-svg-icon {
  width: 24px;
  height: 24px;
}

.stat-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.stat-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.stat-label {
  font-size: var(--st-font-sm);
  color: var(--st-text-regular);
  font-weight: 500;
}

.stat-chevron {
  color: var(--st-text-muted);
  font-size: var(--st-font-xs);
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 1px;
  flex-wrap: wrap;
  margin-top: 1px;
}

.stat-num {
  font-size: 22px;
  font-weight: 800;
  color: var(--st-text-primary);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-unit {
  font-size: var(--st-font-sm);
  font-weight: 500;
  color: var(--st-text-regular);
  margin-left: 1px;
  margin-right: 5px;
}

/* 3. 今日任务整体卡片系统 (Image 4 规范) */
.today-tasks-section {
  margin-bottom: 16px;
}

.section-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 8px;
}

.section-title {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
}

.view-all-btn {
  background: none;
  border: none;
  color: var(--st-primary);
  font-size: var(--st-font-sm);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: 4px;
}

/* 核心：将今日任务收纳进统一白底卡片 */
.tasks-grouped-card {
  margin: 0;
  padding: 2px 14px;
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

.empty-tasks-box {
  text-align: center;
  padding: 24px 12px;
}

.tasks-loading-box,
.tasks-state-box {
  padding: var(--st-space-6) var(--st-space-4);
}

.tasks-state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.tasks-state-icon {
  margin-bottom: var(--st-space-3);
  color: var(--st-warning-dark);
  font-size: 30px;
}

.empty-focus-icon { margin: 0 auto var(--st-space-3); color: var(--st-primary); font-size: 30px; }
.empty-focus-button { min-height: 42px; margin-top: var(--st-space-4); padding: 0 var(--st-space-5); border: 0; border-radius: var(--st-radius-full); background: var(--st-primary); color: #fff; font-size: var(--st-font-md); font-weight: 600; }

.empty-icon-wrap {
  font-size: 32px;
  margin-bottom: 6px;
}

.empty-title {
  font-size: var(--st-font-md);
  font-weight: 700;
  color: var(--st-text-primary);
  margin-bottom: 3px;
}

.empty-subtitle {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.tasks-rows-list {
  display: flex;
  flex-direction: column;
  max-height: 196px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-right: 2px;
}

.tasks-rows-list::-webkit-scrollbar {
  width: 3px;
}

.tasks-rows-list::-webkit-scrollbar-thumb {
  background: var(--st-border-bold, #cbd5e1);
  border-radius: 9999px;
}

.tasks-rows-list::-webkit-scrollbar-track {
  background: transparent;
}

/* 单条任务行：高度紧凑，带微细分割线，字号相对小巧 (Image 4) */
.task-row-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--st-border);
  cursor: pointer;
  transition: background 0.15s ease;
}

.task-row-item.is-last {
  border-bottom: none;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.today-view :deep(.task-left .st-subject-badge) {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  flex-shrink: 0;
}

.today-view :deep(.task-left .st-subject-badge svg) {
  width: 19px;
  height: 19px;
}

.task-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.task-subject-title {
  font-size: var(--st-font-md);
  font-weight: 600;
  color: var(--st-text-primary);
  line-height: 1.25;
}

.task-content-text {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-content-text.is-done {
  color: var(--st-text-muted);
}

.checkin-toggle-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Image 4：18px 浅灰细腻空心圆圈 */
.uncompleted-circle {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--st-border-bold);
  background: var(--st-bg-card);
  transition: all 0.15s ease;
}

.checkin-toggle-btn:active .uncompleted-circle {
  border-color: var(--st-primary);
  transform: scale(0.92);
}

/* Image 4：绿底白勾小圆点 + 翠绿文字 已完成 */
.completed-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--st-success-dark);
  font-size: var(--st-font-xs);
  font-weight: 600;
  padding: 2px 4px;
}

.completed-check-dot {
  width: 15px;
  height: 15px;
}

/* 折叠展开胶囊 */
/* 4. 今日错题复习入口横幅 */
.mistake-review-banner {
  margin: 0 0 16px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--st-gradient-review);
  border: 1px solid var(--st-purple-light);
  border-radius: var(--st-radius-lg);
  cursor: pointer;
  width: 100%;
  font: inherit;
  text-align: left;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.banner-target-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--st-purple);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.25);
}

.banner-target-icon svg {
  width: 20px;
  height: 20px;
}

.banner-title {
  font-size: var(--st-font-md);
  font-weight: 700;
  color: var(--st-text-primary);
}

.banner-subtitle {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin-top: 1px;
}

.banner-action-btn {
  background: var(--st-primary);
  color: #ffffff;
  font-size: var(--st-font-xs);
  font-weight: 600;
  border: none;
  padding: 6px 13px;
  border-radius: var(--st-radius-full);
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

/* 5. 学习时长分布卡片 */
.study-distribution-card {
  margin: 0 0 20px;
  padding: 14px;
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

.dist-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.dist-title {
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
}

.dist-total {
  font-size: var(--st-font-sm);
  font-weight: 600;
  color: var(--st-text-secondary);
}

.dist-bars-list {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.dist-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dist-subject {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 44px;
  flex-shrink: 0;
}

.dist-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dist-subject-name {
  font-size: var(--st-font-sm);
  color: var(--st-text-regular);
  font-weight: 600;
}

.dist-bar-track {
  flex: 1;
  height: 8px;
  background: var(--st-bg-subtle);
  border-radius: 9999px;
  overflow: hidden;
}

.dist-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.dist-duration {
  width: 50px;
  text-align: right;
  font-size: var(--st-font-xs);
  color: var(--st-text-muted);
  font-weight: 600;
  flex-shrink: 0;
}

/* 6. 底部双悬浮快速录入操作胶囊 (精细复刻配图浅蓝质感胶囊 + 严密防漂移定位) */
.floating-quick-actions {
  position: fixed;
  /* 与作业/错题/数据页一致：底部常驻磨砂横条，不再透出页面内容 */
  bottom: calc(50px + env(safe-area-inset-bottom, 0px));
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
  justify-content: center;
  gap: 12px;
  z-index: 40;
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
}

/* 录入由应用壳的全局加号统一提供，避免首页与各业务页重复争抢注意力。 */
.floating-quick-actions { display: none; }

.quick-fab-btn {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 46px;
  padding: 0 20px;
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #93c5fd;
  border-radius: 9999px;
  font-size: 15px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.12);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.quick-fab-btn:active {
  transform: scale(0.96);
  background: #dbeafe;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.fab-svg-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
</style>
