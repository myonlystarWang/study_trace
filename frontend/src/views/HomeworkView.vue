<template>
  <div class="homework-view">
    <!-- 顶部日期与导航 -->
    <div class="header-bar">
      <div class="date-nav">
        <button class="nav-btn" @click="changeDate(-1)">❮</button>
        <span class="date-text" @click="showCalendar = true">
          {{ isToday ? '今日作业' : currentDate }}
          <span class="cal-icon" title="打开月历打卡">📅</span>
        </span>
        <button class="nav-btn" :disabled="isToday" @click="changeDate(1)">❯</button>
      </div>
      <div class="header-right">
        <div class="streak-badge" v-if="streak > 0">
          🔥 连续 <b>{{ streak }}</b> 天
        </div>
        <button class="lock-entry-btn" title="家长管理入口" @click="$router.push('/settings')">
          🔒
        </button>
      </div>
    </div>

    <!-- 完成度进度条（红黄绿状态） -->
    <div class="progress-card">
      <div class="progress-info">
        <span class="info-title">完成进度 ({{ completedCount }}/{{ totalCount }})</span>
        <span class="info-rate" :style="{ color: statusColor }">{{ rate }}%</span>
      </div>
      <van-progress
        :percentage="rate"
        :color="statusColor"
        stroke-width="10"
        :show-pivot="false"
      />
    </div>

    <!-- 学科快捷标签栏 -->
    <div class="subject-tabs">
      <div
        class="tab-chip"
        :class="{ active: selectedSubject === null }"
        @click="selectedSubject = null"
      >
        全部
      </div>
      <div
        v-for="sub in subjects"
        :key="sub.id"
        class="tab-chip"
        :class="{ active: selectedSubject === sub.id }"
        @click="selectedSubject = sub.id"
      >
        {{ sub.name }}
      </div>
    </div>

    <!-- 作业清单 -->
    <van-pull-refresh v-model="refreshing" @refresh="fetchHomework">
      <div class="hw-list" v-if="filteredItems.length > 0">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="hw-card"
          :class="{ completed: item.is_completed }"
        >
          <!-- 大打勾触控区 -->
          <div class="check-box" @click="toggleComplete(item)">
            <div class="check-circle" :class="{ checked: item.is_completed }">
              <span v-if="item.is_completed">✓</span>
            </div>
          </div>

          <!-- 作业详情 -->
          <div class="hw-body">
            <div class="hw-meta">
              <span class="sub-tag">{{ item.subject_name }}</span>
              <span class="time-text" v-if="item.completed_at">已完成</span>
            </div>
            <div class="hw-text" :class="{ strike: item.is_completed }">
              {{ item.content }}
            </div>
            <div class="hw-actions">
              <button class="action-btn mistake-btn" @click.stop="handleToMistake(item)">
                ＋ 记为错题
              </button>
              <button class="action-btn del-btn" @click.stop="handleDelete(item)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else>
        <van-empty description="今天暂无作业，点击下方添加吧" />
      </div>
    </van-pull-refresh>

    <!-- 底部常驻快捷录入入口 -->
    <div class="bottom-add-bar">
      <van-button type="primary" round block icon="plus" @click="showAddModal = true">
        录入新作业
      </van-button>
    </div>

    <!-- 录入作业弹窗（支持手动 / 拍照 OCR 批量录入） -->
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

    <!-- 25分钟专注番茄钟 -->
    <PomodoroTimer />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { showToast, showConfirmDialog } from 'vant';
import { homeworkApi, settingsApi } from '../api';
import QuickAddModal from '../components/QuickAddModal.vue';
import CalendarModal from '../components/CalendarModal.vue';
import PomodoroTimer from '../components/PomodoroTimer.vue';

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

const handleDateSelect = (dateStr) => {
  currentDate.value = dateStr;
  fetchHomework();
};

const isToday = computed(() => {
  return currentDate.value === new Date().toISOString().split('T')[0];
});

// 红黄绿完成度颜色映射
const statusColor = computed(() => {
  if (rate.value === 100 && totalCount.value > 0) return '#10b981'; // 绿
  if (rate.value >= 50) return '#f59e0b'; // 黄
  return '#ef4444'; // 红
});

const filteredItems = computed(() => {
  if (!selectedSubject.value) return items.value;
  return items.value.filter((i) => i.subject_id === selectedSubject.value);
});

const changeDate = (days) => {
  const d = new Date(currentDate.value);
  d.setDate(d.getDate() + days);
  currentDate.value = d.toISOString().split('T')[0];
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
  try {
    await homeworkApi.update(item.id, { is_completed: targetStatus });
    item.is_completed = targetStatus;
    if (targetStatus) {
      showToast({ message: '太棒了！又完成一项', icon: 'passed' });
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
      showToast('已删除');
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
  padding: 1rem 1rem 6rem;
  background: #f8fafc;
  min-height: 100vh;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.date-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-btn {
  border: none;
  background: white;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #475569;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  cursor: pointer;
}

.nav-btn:disabled {
  opacity: 0.3;
}

.date-text {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.cal-icon {
  font-size: 1rem;
  opacity: 0.85;
  transition: transform 0.2s ease;
}

.date-text:active .cal-icon {
  transform: scale(1.2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lock-entry-btn {
  border: none;
  background: white;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.streak-badge {
  background: #fff7ed;
  color: #ea580c;
  padding: 0.3rem 0.7rem;
  border-radius: 20px;
  font-size: 0.85rem;
  border: 1px solid #ffedd5;
  font-weight: 500;
}

.progress-card {
  background: white;
  border-radius: 16px;
  padding: 1rem 1.25rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
  margin-bottom: 1rem;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
}

.info-title {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
}

.info-rate {
  font-size: 1.2rem;
  font-weight: 800;
}

.subject-tabs {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
  scrollbar-width: none;
}

.subject-tabs::-webkit-scrollbar {
  display: none;
}

.tab-chip {
  padding: 0.35rem 0.85rem;
  background: #f1f5f9;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #475569;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-chip.active {
  background: #2563eb;
  color: white;
  font-weight: 600;
}

.hw-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hw-card {
  display: flex;
  align-items: flex-start;
  background: white;
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition: all 0.2s;
  border: 1px solid transparent;
}

.hw-card.completed {
  background: #fcfdfd;
  opacity: 0.75;
}

.check-box {
  padding: 0.2rem 0.8rem 0 0;
  cursor: pointer;
}

.check-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  color: white;
  transition: all 0.2s;
}

.check-circle.checked {
  background: #10b981;
  border-color: #10b981;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.hw-body {
  flex: 1;
}

.hw-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}

.sub-tag {
  background: #eff6ff;
  color: #2563eb;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  font-weight: 600;
}

.time-text {
  font-size: 0.75rem;
  color: #10b981;
}

.hw-text {
  font-size: 1rem;
  color: #1e293b;
  line-height: 1.5;
  margin-bottom: 0.5rem;
  word-break: break-word;
}

.hw-text.strike {
  text-decoration: line-through;
  color: #94a3b8;
}

.hw-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  border: none;
  background: none;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
}

.mistake-btn {
  color: #ea580c;
  background: #fff7ed;
  border-radius: 6px;
}

.del-btn {
  color: #94a3b8;
}

.bottom-add-bar {
  position: fixed;
  bottom: 60px;
  left: 0;
  right: 0;
  max-width: 480px;
  margin: 0 auto;
  padding: 0.75rem 1rem;
  background: linear-gradient(to top, rgba(248, 250, 252, 1) 70%, rgba(248, 250, 252, 0));
}

.modal-content {
  padding: 1.5rem;
}

.modal-content h3 {
  margin-bottom: 1rem;
  font-size: 1.15rem;
  color: #0f172a;
}
</style>
