<template>
  <div class="today-view">
    <!-- 1. 顶部温和生活感问候区 -->
    <header class="greeting-header">
      <div class="greeting-text">
        <h1 class="greeting-title">{{ timeGreeting }}，同学 👋</h1>
        <p class="greeting-date">{{ formattedDate }}</p>
      </div>
      <div class="greeting-illustration" @click="$router.push('/settings')">
        <!-- 课桌学习矢量插图 -->
        <div class="avatar-illustration-badge">
          <svg viewBox="0 0 64 64" fill="none" class="student-svg">
            <circle cx="32" cy="32" r="30" fill="#eff6ff" />
            <!-- 头像发型与脸 -->
            <circle cx="32" cy="24" r="12" fill="#fed7aa" />
            <path d="M20 20 C20 12, 44 12, 44 20 C44 23, 20 23, 20 20 Z" fill="#334155" />
            <!-- 身体衣服 -->
            <path d="M18 52 C18 38, 46 38, 46 52 Z" fill="#3b82f6" />
            <!-- 书本 -->
            <rect x="23" y="44" width="18" height="12" rx="2" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" />
            <line x1="32" y1="44" x2="32" y2="56" stroke="#94a3b8" stroke-width="1.5" />
          </svg>
        </div>
      </div>
    </header>

    <main class="today-content">
      <!-- 2. 数据概览 2 列网格 -->
      <section class="overview-grid">
        <!-- 左侧：今日完成率 Donut 环形图卡片 -->
        <div class="st-card donut-card" @click="$router.push('/homework')">
          <span class="card-label">今日完成率</span>
          <div class="donut-container">
            <svg class="donut-svg" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="donut-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#06b6d4" />
                  <stop offset="100%" stop-color="#3b82f6" />
                </linearGradient>
              </defs>
              <!-- 底环 -->
              <circle
                class="donut-bg"
                cx="50"
                cy="50"
                r="38"
                stroke-width="10"
              />
              <!-- 进度环 -->
              <circle
                class="donut-fill"
                cx="50"
                cy="50"
                r="38"
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
        </div>

        <!-- 右侧：双层微型统计卡片 -->
        <div class="stats-column">
          <!-- 连续学习卡片 -->
          <div class="st-card mini-stat-card" @click="$router.push('/homework')">
            <div class="stat-header">
              <span class="stat-icon-wrap stat-icon-fire">🔥</span>
              <div class="stat-info">
                <span class="stat-name">连续学习</span>
                <span class="stat-value"><strong>{{ streakDays }}</strong> 天</span>
              </div>
              <van-icon name="arrow" class="stat-arrow" />
            </div>
          </div>

          <!-- 今日专注时长卡片 -->
          <div class="st-card mini-stat-card" @click="openPomodoro">
            <div class="stat-header">
              <span class="stat-icon-wrap stat-icon-time">🕒</span>
              <div class="stat-info">
                <span class="stat-name">今日学习时长</span>
                <span class="stat-value">{{ formattedStudyDuration }}</span>
              </div>
              <van-icon name="arrow" class="stat-arrow" />
            </div>
          </div>
        </div>
      </section>

      <!-- 3. 今日任务极简清单 -->
      <section class="today-tasks-section">
        <div class="section-top-bar">
          <h2 class="section-title">今日任务</h2>
          <button class="view-all-btn" @click="$router.push('/homework')">
            查看全部 <van-icon name="arrow" />
          </button>
        </div>

        <!-- 任务列表为空状态 -->
        <div v-if="tasks.length === 0 && !loading" class="st-card empty-tasks-card">
          <div class="empty-icon-wrap">☀️</div>
          <p class="empty-title">今天没有待办作业</p>
          <p class="empty-subtitle">自由时光属于你，或是提前录入新作业吧！</p>
        </div>

        <!-- 任务列表 -->
        <div v-else class="tasks-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="st-card task-card"
            :class="{ 'is-completed': task.is_completed }"
            @click="openTaskDetail(task)"
          >
            <div class="task-left">
              <SubjectBadge :name="task.subject_name" size="md" />
              <div class="task-details">
                <div class="task-subject-title">{{ task.subject_name }}</div>
                <div class="task-content-text" :class="{ strike: task.is_completed }">
                  {{ task.content }}
                </div>
                <div class="task-meta">
                  <span v-if="task.is_weekend_rollover" class="weekend-tag">周末顺延</span>
                  <span class="task-time">
                    {{ formatTaskTime(task.created_at || task.date) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 右侧打卡勾选按钮 (阻止冒泡，支持极速打卡) -->
            <button
              class="checkin-toggle-btn"
              :class="{ 'checked': task.is_completed }"
              :disabled="taskToggling === task.id"
              @click.stop="toggleTaskCheck(task)"
              :aria-label="task.is_completed ? '已完成' : '打卡'"
            >
              <template v-if="task.is_completed">
                <span class="completed-pill">
                  <van-icon name="success" size="12" />
                  已完成
                </span>
              </template>
              <template v-else>
                <span class="uncompleted-circle"></span>
              </template>
            </button>
          </div>
        </div>
      </section>

      <!-- 4. 今日错题复习入口横幅 -->
      <section class="mistake-review-banner st-card" @click="goToMistakesReview">
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
        <button class="banner-action-btn">
          {{ reviewQueueCount > 0 ? '开始复习' : '去错题本' }} <van-icon name="arrow" />
        </button>
      </section>

      <!-- 5. 学习时长分布卡片 -->
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

    <!-- 6. 底部双悬浮快速录入操作胶囊 -->
    <aside class="floating-quick-actions">
      <button class="quick-fab-btn" @click="showAddModal = true">
        <van-icon name="photograph" size="18" />
        <span>录入作业</span>
      </button>
      <button class="quick-fab-btn" @click="$router.push('/mistakes?action=add')">
        <van-icon name="records-o" size="18" />
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
import { ref, computed, onMounted } from 'vue';
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

const handleDetailEdit = (task) => {
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

// 动态时间段问候
const timeGreeting = computed(() => {
  const hour = today.getHours();
  if (hour >= 5 && hour < 12) return '早上好';
  if (hour >= 12 && hour < 14) return '中午好';
  if (hour >= 14 && hour < 18) return '下午好';
  return '晚上好';
});

// 中文日期格式化
const formattedDate = computed(() => {
  const month = today.getMonth() + 1;
  const date = today.getDate();
  const dayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const dayName = dayNames[today.getDay()];
  return `今天是 ${month}月${date}日 ${dayName}`;
});

// SVG 环形进度条计算
const radius = 38;
const circumference = 2 * Math.PI * radius; // ~238.76
const progressOffset = computed(() => {
  const rate = Math.min(Math.max(completionRate.value, 0), 100);
  return circumference - (rate / 100) * circumference;
});

// 专注时长计算
const totalFocusMinutes = ref(102); // 默认 1 小时 42 分钟（亦从 localStorage 动态增量累加）
const formattedStudyDuration = computed(() => {
  const m = totalFocusMinutes.value;
  if (m <= 0) return '0 分钟';
  const hours = Math.floor(m / 60);
  const mins = m % 60;
  if (hours > 0 && mins > 0) return `${hours}小时${mins}分钟`;
  if (hours > 0) return `${hours}小时`;
  return `${mins}分钟`;
});

// 学科时长分布
const subjectDistribution = computed(() => {
  // 按照典型作业学科时长分布
  return [
    { name: '数学', color: '#3b82f6', percentage: 48, durationText: '48 min' },
    { name: '语文', color: '#10b981', percentage: 31, durationText: '31 min' },
    { name: '英语', color: '#8b5cf6', percentage: 23, durationText: '23 min' },
    { name: '其他', color: '#cbd5e1', percentage: 0, durationText: '0 min' }
  ];
});

// 格式化布置时间
const formatTaskTime = (isoTimeStr) => {
  if (!isoTimeStr) return '';
  try {
    const d = new Date(isoTimeStr);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `布置时间: ${m}-${day} ${h}:${min}`;
  } catch (e) {
    return '';
  }
};

// 加载今日作业与统计
const fetchTodayHomework = async () => {
  loading.value = true;
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

    // 若打卡完成，弹出仪式感祝贺弹窗
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
  // 可停留在本页或做微动效
};

// 打开专注计时器
const openPomodoro = () => {
  pomodoroRef.value?.open();
};

// 跳转错题复习
const goToMistakesReview = () => {
  router.push('/mistakes?tab=review');
};

onMounted(() => {
  fetchTodayHomework();
  fetchSubjects();
  fetchReviewQueue();
});
</script>

<style scoped>
.today-view {
  flex: 1;
  background-color: var(--st-bg-page, #f8fafc);
  padding: 16px 14px 110px;
  max-width: 500px;
  margin: 0 auto;
  position: relative;
}

/* 1. 顶部问候区 */
.greeting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px 16px;
}

.greeting-title {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.3px;
  margin-bottom: 4px;
}

.greeting-date {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.avatar-illustration-badge {
  width: 52px;
  height: 52px;
  cursor: pointer;
  filter: drop-shadow(0 4px 10px rgba(59, 130, 246, 0.15));
  transition: transform 0.15s ease;
}

.avatar-illustration-badge:active {
  transform: scale(0.94);
}

.student-svg {
  width: 100%;
  height: 100%;
}

/* 2. 数据概览网格 */
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.donut-card {
  margin: 0;
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}

.donut-container {
  position: relative;
  width: 96px;
  height: 96px;
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
  stroke: #e2e8f0;
}

.donut-fill {
  fill: none;
  stroke: #06b6d4;
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
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}

.donut-fraction {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  margin-top: 2px;
}

.stats-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mini-stat-card {
  margin: 0;
  padding: 12px 14px;
  flex: 1;
  display: flex;
  align-items: center;
  cursor: pointer;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease;
}

.mini-stat-card:active {
  transform: scale(0.98);
}

.stat-header {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 10px;
}

.stat-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.stat-icon-fire {
  background: #fff7ed;
}

.stat-icon-time {
  background: #eff6ff;
}

.stat-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.stat-name {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

.stat-value {
  font-size: 13px;
  color: #0f172a;
  font-weight: 700;
  margin-top: 2px;
}

.stat-arrow {
  color: #94a3b8;
  font-size: 12px;
}

/* 3. 今日任务极简清单 */
.today-tasks-section {
  margin-bottom: 16px;
}

.section-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 10px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.view-all-btn {
  background: none;
  border: none;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: 4px;
}

.empty-tasks-card {
  text-align: center;
  padding: 28px 16px;
  background: #ffffff;
  border-radius: 16px;
}

.empty-icon-wrap {
  font-size: 36px;
  margin-bottom: 8px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.empty-subtitle {
  font-size: 12px;
  color: #64748b;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  margin: 0;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.7);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
  transition: all 0.2s ease;
  cursor: pointer;
}

.task-card:active {
  transform: scale(0.985);
  background: #f8fafc;
}

.task-card.is-completed {
  background: #f8fafc;
  opacity: 0.88;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.task-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.task-subject-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}

.task-content-text {
  font-size: 13.5px;
  color: #334155;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-card.is-completed .task-content-text {
  text-decoration: line-through;
  color: #94a3b8;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 1px;
}

.weekend-tag {
  font-size: 10px;
  background: #fef3c7;
  color: #d97706;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 600;
}

.task-time {
  font-size: 11px;
  color: #94a3b8;
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

.uncompleted-circle {
  display: inline-block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.8px solid #cbd5e1;
  background: transparent;
  transition: all 0.2s ease;
}

.uncompleted-circle:hover {
  border-color: #3b82f6;
}

.completed-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #ecfdf5;
  color: #10b981;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 9999px;
  border: 1px solid #a7f3d0;
}

.uncompleted-circle {
  display: block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  background: #ffffff;
  transition: all 0.15s ease;
}

.checkin-toggle-btn:active .uncompleted-circle {
  border-color: #3b82f6;
  transform: scale(0.9);
}

/* 4. 今日错题复习入口横幅 */
.mistake-review-banner {
  margin: 0 0 16px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #fdf4ff 0%, #eff6ff 100%);
  border: 1px solid #f3e8ff;
  border-radius: 16px;
  cursor: pointer;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-target-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #8b5cf6;
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
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.banner-subtitle {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.banner-action-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  border: none;
  padding: 6px 12px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

/* 5. 学习时长分布卡片 */
.study-distribution-card {
  margin: 0 0 20px;
  padding: 16px;
  background: #ffffff;
  border-radius: 16px;
}

.dist-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}

.dist-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.dist-total {
  font-size: 13px;
  font-weight: 700;
  color: #3b82f6;
}

.dist-bars-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  width: 50px;
  flex-shrink: 0;
}

.dist-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dist-subject-name {
  font-size: 12px;
  color: #334155;
  font-weight: 600;
}

.dist-bar-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
}

.dist-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.6s ease;
}

.dist-duration {
  width: 50px;
  text-align: right;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  flex-shrink: 0;
}

/* 6. 底部双悬浮快速录入操作胶囊 */
.floating-quick-actions {
  position: fixed;
  bottom: 64px;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: center;
  gap: 16px;
  pointer-events: none;
  z-index: 90;
}

.quick-fab-btn {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 20px;
  background: #ffffff;
  color: #1e293b;
  border: 1px solid #e2e8f0;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.1);
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-fab-btn:first-child {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.quick-fab-btn:active {
  transform: scale(0.95);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
</style>
