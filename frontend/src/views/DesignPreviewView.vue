<template>
  <div class="preview-container">
    <!-- 顶部环境与模式切换栏 -->
    <div class="demo-top-bar">
      <div class="demo-badge">
        <span class="pulse-dot"></span>
        <span>UI/UX 交互预览 Demo</span>
      </div>
      <div class="screen-switch-tabs">
        <button 
          class="switch-tab-btn" 
          :class="{ active: currentScreen === 'homework' }"
          @click="currentScreen = 'homework'"
        >
          <van-icon name="passed" /> 作业打卡流
        </button>
        <button 
          class="switch-tab-btn" 
          :class="{ active: currentScreen === 'mistake' }"
          @click="currentScreen = 'mistake'"
        >
          <van-icon name="records-o" /> 错题复习流
        </button>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- 屏 1：作业打卡流 (Homework Check-in Flow)                          -->
    <!-- ================================================================= -->
    <div v-if="currentScreen === 'homework'" class="screen-content">
      <!-- 顶栏：打卡连击 + 日期概览 + 家长入口 -->
      <div class="top-nav-bar">
        <div class="streak-badge">
          <van-icon name="fire" color="#f97316" size="16" />
          <span>连续打卡 <b>{{ streakCount }}</b> 天</span>
        </div>
        <div class="parent-entry-btn" title="家长管理入口" @click="showPinSheet = true">
          <van-icon name="setting-o" size="18" />
        </div>
      </div>

      <!-- 顶部 7 日横向胶囊周历条 (Week Strip) -->
      <div class="week-strip-box">
        <div 
          v-for="(day, idx) in weekDays" 
          :key="idx" 
          class="week-day-pill"
          :class="{ active: selectedDayIndex === idx, today: day.isToday }"
          @click="selectDay(idx)"
        >
          <span class="day-label">{{ day.label }}</span>
          <span class="day-number">{{ day.dateNumber }}</span>
          <span class="day-dot" :class="{ completed: day.isAllDone }"></span>
        </div>
      </div>

      <!-- 今日进度概览卡片 (含 100% 达成成就动效) -->
      <div class="st-card progress-summary-card">
        <div class="progress-header">
          <div class="st-section-header" style="margin-bottom: 0;">
            <span class="st-icon-badge st-icon-badge--primary">
              <van-icon name="chart-trending-o" />
            </span>
            <span class="section-title">{{ currentDayTitle }} 作业进度</span>
          </div>
          <span class="progress-stat-text">
            <b>{{ completedCount }}</b> / {{ homeworkList.length }} 已完成
          </span>
        </div>

        <div class="progress-bar-wrapper">
          <van-progress 
            :percentage="progressPercentage" 
            :color="progressPercentage === 100 ? 'var(--st-success)' : 'var(--st-primary)'"
            :show-pivot="false"
            stroke-width="8"
          />
        </div>

        <!-- 100% 达成时的微反馈 -->
        <transition name="van-fade">
          <div v-if="progressPercentage === 100" class="all-done-banner">
            <div class="st-icon-badge st-icon-badge--success" style="width: 22px; height: 22px;">
              <van-icon name="passed" />
            </div>
            <span>太棒了！今日全部作业均已如期完成</span>
          </div>
        </transition>
      </div>

      <!-- 作业列表提示与左右滑动手势感应区 -->
      <div 
        class="homework-list-wrapper"
        @touchstart="handleTouchStart"
        @touchend="handleTouchEnd"
      >
        <div class="list-section-header">
          <span class="list-title">待办作业 ({{ homeworkList.length }} 项)</span>
          <span class="swipe-hint">
            <van-icon name="exchange" /> 左滑卡片呼出操作
          </span>
        </div>

        <div class="homework-cards">
          <!-- 采用 van-swipe-cell 实现大厂标准左滑快捷抽屉 -->
          <van-swipe-cell 
            v-for="item in homeworkList" 
            :key="item.id"
            class="hw-swipe-cell"
          >
            <!-- 卡片正面：极致极简 -->
            <div 
              class="st-card hw-card-face"
              :class="{ 'is-done': item.completed }"
              @click="toggleHomework(item)"
            >
              <!-- 大号圆形打勾交互区 -->
              <div 
                class="hw-check-circle"
                :class="{ checked: item.completed, 'st-animate-check': item.justToggled }"
              >
                <van-icon v-if="item.completed" name="success" size="14" color="#ffffff" />
              </div>

              <!-- 中间内容 -->
              <div class="hw-content">
                <div class="hw-meta-row">
                  <span class="st-icon-badge" :class="getSubjectBadgeClass(item.subject)">
                    {{ item.subject }}
                  </span>
                  <span class="hw-due-time">
                    <van-icon name="clock-o" /> {{ item.dueTime }}
                  </span>
                </div>
                <div class="hw-title" :class="{ strike: item.completed }">
                  {{ item.title }}
                </div>
              </div>

              <!-- 状态微指示 -->
              <div class="hw-status-tag" :class="{ done: item.completed }">
                {{ item.completed ? '已打卡' : '待完成' }}
              </div>
            </div>

            <!-- 左滑展开的右侧操作抽屉 -->
            <template #right>
              <div class="swipe-actions-box">
                <button class="swipe-action-btn btn-mistake" @click.stop="quickMarkMistake(item)">
                  <van-icon name="plus" size="16" />
                  <span>转错题</span>
                </button>
                <button class="swipe-action-btn btn-delete" @click.stop="deleteHomework(item)">
                  <van-icon name="delete-o" size="16" />
                  <span>删除</span>
                </button>
              </div>
            </template>
          </van-swipe-cell>
        </div>
      </div>

      <!-- 底部悬浮吸底按钮 -->
      <div class="floating-bottom-bar st-frosted-bar">
        <van-button 
          round 
          block 
          type="primary" 
          icon="plus" 
          class="add-hw-btn"
          @click="showAddHomeworkSheet = true"
        >
          新增今日作业
        </van-button>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- 屏 2：错题复习流 (Mistake Ebbinghaus Review Flow)                   -->
    <!-- ================================================================= -->
    <div v-else class="screen-content">
      <!-- 科目筛选胶囊横条 (Chips) -->
      <div class="chips-scroll-bar">
        <span 
          v-for="sub in subjects" 
          :key="sub.name"
          class="st-chip"
          :class="{ active: selectedSubject === sub.name }"
          @click="selectedSubject = sub.name"
        >
          {{ sub.name }} ({{ sub.count }})
        </span>
      </div>

      <!-- 艾宾浩斯今日临界待复习 -->
      <div class="st-card ebbinghaus-banner-card">
        <div class="st-section-header" style="margin-bottom: 6px;">
          <span class="st-icon-badge st-icon-badge--purple">
            <van-icon name="replay" />
          </span>
          <span class="section-title">艾宾浩斯智能临界复习</span>
          <span class="header-action" style="color: var(--st-purple);">
            {{ pendingReviewList.length }} 道待攻克
          </span>
        </div>
        <p class="ebbinghaus-desc">
          基于德国心理学家遗忘曲线算法，以下错题已抵达记忆临界遗忘点，复习效果提升 80%：
        </p>
      </div>

      <!-- 错题卡片列表 -->
      <div class="mistake-cards-list">
        <div 
          v-for="item in pendingReviewList" 
          :key="item.id"
          class="st-card mistake-card"
        >
          <div class="mistake-card-header">
            <div class="subject-and-stage">
              <span class="st-icon-badge" :class="getSubjectBadgeClass(item.subject)">
                {{ item.subject }}
              </span>
              <span class="stage-pill">
                <van-icon name="underway-o" /> 第 {{ item.reviewCount + 1 }} 轮复习
              </span>
            </div>
            <span class="retention-pill">
              记忆保留度 {{ item.retentionRate }}%
            </span>
          </div>

          <!-- 题干正文 -->
          <div class="mistake-question-text">
            {{ item.question }}
          </div>

          <!-- 错题图片略缩图 (点击支持灯箱无痕放大) -->
          <div v-if="item.hasImage" class="mistake-thumb-box" @click="previewImage">
            <img src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400&q=80" alt="题干配图" />
            <span class="img-preview-tag">
              <van-icon name="search" /> 点击放大原图
            </span>
          </div>

          <!-- 核心交互：标准 Vant 矢量按钮复习反馈 -->
          <div class="mistake-actions-row">
            <van-button 
              size="small" 
              plain 
              type="danger" 
              icon="cross"
              class="review-act-btn"
              @click="handleReview(item, false)"
            >
              又忘了
            </van-button>
            <van-button 
              size="small" 
              type="success" 
              icon="passed"
              class="review-act-btn"
              @click="handleReview(item, true)"
            >
              掌握啦
            </van-button>
          </div>
        </div>
      </div>

      <!-- 底部悬浮录入按钮 -->
      <div class="floating-bottom-bar st-frosted-bar">
        <van-button 
          round 
          block 
          type="primary" 
          icon="scan" 
          class="add-hw-btn"
          @click="showAddMistakeSheet = true"
        >
          录入与拍照识别错题
        </van-button>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- 移动端底部半屏抽屉 (Bottom Sheet) 示范                             -->
    <!-- ================================================================= -->

    <!-- 1. 新增作业底部半屏抽屉 -->
    <van-popup 
      v-model:show="showAddHomeworkSheet" 
      position="bottom" 
      round 
      class="bottom-sheet-modal"
    >
      <div class="bottom-sheet-content">
        <div class="sheet-grabber"></div>
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="plus" />
          </span>
          <span class="section-title">添加待办作业</span>
        </div>

        <div class="sheet-form">
          <div class="form-group">
            <label class="form-label">选择学科</label>
            <div class="sheet-subject-chips">
              <span 
                v-for="sub in ['数学', '英语', '语文', '物理', '化学']" 
                :key="sub"
                class="st-chip"
                :class="{ active: newHwSubject === sub }"
                @click="newHwSubject = sub"
              >
                {{ sub }}
              </span>
            </div>
          </div>

          <div class="form-group" style="margin-top: 14px;">
            <label class="form-label">作业内容或练习册页码</label>
            <van-field 
              v-model="newHwTitle" 
              placeholder="例如：数学课本 P42 习题 1~6 题"
              class="sheet-input-field"
            />
          </div>

          <div class="form-group" style="margin-top: 14px;">
            <label class="form-label">预计用时</label>
            <div class="sheet-subject-chips">
              <span 
                v-for="t in ['15分钟', '25分钟', '40分钟', '60分钟']" 
                :key="t"
                class="st-chip"
                :class="{ active: newHwTime === t }"
                @click="newHwTime = t"
              >
                {{ t }}
              </span>
            </div>
          </div>

          <van-button 
            type="primary" 
            block 
            round 
            style="margin-top: 20px; font-weight: 600;"
            @click="submitNewHomework"
          >
            保存并加入今日打卡
          </van-button>
        </div>
      </div>
    </van-popup>

    <!-- 2. PIN 码解锁底部抽屉 -->
    <van-popup 
      v-model:show="showPinSheet" 
      position="bottom" 
      round 
      class="bottom-sheet-modal"
    >
      <div class="bottom-sheet-content" style="text-align: center;">
        <div class="sheet-grabber"></div>
        <div class="st-icon-badge st-icon-badge--primary" style="width: 42px; height: 42px; font-size: 20px; margin: 0 auto 12px;">
          <van-icon name="lock" />
        </div>
        <h3 style="font-size: 17px; font-weight: 600; color: var(--st-text-primary); margin-bottom: 6px;">
          家长身份安全验证
        </h3>
        <p style="font-size: 13px; color: var(--st-text-secondary); margin-bottom: 20px;">
          设置与成绩管理已开启专属 PIN 保护，请输入 4~6 位安全码
        </p>
        <van-field 
          v-model="inputPin" 
          type="password" 
          maxlength="6"
          placeholder="请输入家长 PIN 码 (默认 1234)"
          class="sheet-input-field"
          style="text-align: center; font-size: 18px; letter-spacing: 6px;"
        />
        <van-button 
          type="primary" 
          block 
          round 
          style="margin-top: 18px; font-weight: 600;"
          @click="verifyPin"
        >
          立即解锁
        </van-button>
      </div>
    </van-popup>

    <!-- 3. 录入错题底部抽屉 -->
    <van-popup 
      v-model:show="showAddMistakeSheet" 
      position="bottom" 
      round 
      class="bottom-sheet-modal"
    >
      <div class="bottom-sheet-content">
        <div class="sheet-grabber"></div>
        <div class="st-section-header">
          <span class="st-icon-badge st-icon-badge--primary">
            <van-icon name="scan" />
          </span>
          <span class="section-title">录入新错题</span>
        </div>
        <p style="font-size: 13px; color: var(--st-text-secondary); margin-bottom: 16px;">
          支持拍照识别（RapidOCR）或手动打字录入：
        </p>
        <div style="display: flex; gap: 12px;">
          <van-button 
            type="primary" 
            plain 
            icon="photograph" 
            block 
            round
            @click="simulateOcr"
          >
            拍照一键提取题干
          </van-button>
          <van-button 
            type="default" 
            icon="edit" 
            block 
            round
            @click="showAddMistakeSheet = false"
          >
            手动键盘录入
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { showToast, showImagePreview } from 'vant';

// 当前处于哪个演示屏
const currentScreen = ref('homework');

// ==========================================
// 屏 1：作业打卡数据与交互逻辑
// ==========================================
const streakCount = ref(7);
const selectedDayIndex = ref(3); // 默认选中周四/今天
const showPinSheet = ref(false);
const inputPin = ref('');
const showAddHomeworkSheet = ref(false);
const newHwSubject = ref('数学');
const newHwTitle = ref('');
const newHwTime = ref('25分钟');

const weekDays = ref([
  { label: '周一', dateNumber: '11', isToday: false, isAllDone: true },
  { label: '周二', dateNumber: '12', isToday: false, isAllDone: true },
  { label: '周三', dateNumber: '13', isToday: false, isAllDone: true },
  { label: '周四', dateNumber: '14', isToday: true, isAllDone: false },
  { label: '周五', dateNumber: '15', isToday: false, isAllDone: false },
  { label: '周六', dateNumber: '16', isToday: false, isAllDone: false },
  { label: '周日', dateNumber: '17', isToday: false, isAllDone: false },
]);

const homeworkList = ref([
  { id: 1, subject: '数学', title: '《初中数学中考真题》二次函数压轴题 2 题', dueTime: '20:30 前完成', completed: true, justToggled: false },
  { id: 2, subject: '英语', title: 'Module 4 完形填空精练 + 核心高频词汇背诵打卡', dueTime: '21:00 前完成', completed: true, justToggled: false },
  { id: 3, subject: '物理', title: '探究凸透镜成像规律实验报告订正与分析', dueTime: '21:30 前完成', completed: false, justToggled: false },
  { id: 4, subject: '语文', title: '古诗文背诵默写《小石潭记》整篇', dueTime: '22:00 前完成', completed: false, justToggled: false },
]);

const currentDayTitle = computed(() => {
  return weekDays.value[selectedDayIndex.value]?.label || '今日';
});

const completedCount = computed(() => {
  return homeworkList.value.filter(item => item.completed).length;
});

const progressPercentage = computed(() => {
  if (homeworkList.value.length === 0) return 0;
  return Math.round((completedCount.value / homeworkList.value.length) * 100);
});

// 单项打卡交互（含 150ms 弹性动画与成就激励）
const toggleHomework = (item) => {
  item.completed = !item.completed;
  item.justToggled = true;
  setTimeout(() => {
    item.justToggled = false;
  }, 250);

  if (progressPercentage.value === 100) {
    showToast({
      message: '今日打卡全达成！太棒了',
      icon: 'passed',
      duration: 1500
    });
    weekDays.value[selectedDayIndex.value].isAllDone = true;
  }
};

// 左滑操作：转错题
const quickMarkMistake = (item) => {
  showToast({
    message: `已将「${item.title.substring(0, 8)}...」记入错题本`,
    icon: 'success'
  });
};

// 左滑操作：删除
const deleteHomework = (item) => {
  homeworkList.value = homeworkList.value.filter(i => i.id !== item.id);
  showToast({ message: '已删除该项作业', position: 'bottom' });
};

// 日期切换
const selectDay = (idx) => {
  selectedDayIndex.value = idx;
};

// 触摸手势左右轻滑翻日
let touchStartX = 0;
const handleTouchStart = (e) => {
  touchStartX = e.touches[0].clientX;
};

const handleTouchEnd = (e) => {
  const touchEndX = e.changedTouches[0].clientX;
  const diffX = touchEndX - touchStartX;
  if (diffX > 60) {
    // 向右滑：前一天
    if (selectedDayIndex.value > 0) {
      selectedDayIndex.value--;
      showToast({ message: `切换至 ${weekDays.value[selectedDayIndex.value].label}`, position: 'top' });
    }
  } else if (diffX < -60) {
    // 向左滑：后一天
    if (selectedDayIndex.value < weekDays.value.length - 1) {
      selectedDayIndex.value++;
      showToast({ message: `切换至 ${weekDays.value[selectedDayIndex.value].label}`, position: 'top' });
    }
  }
};

// 添加新作业
const submitNewHomework = () => {
  if (!newHwTitle.value.trim()) {
    showToast('请输入作业内容');
    return;
  }
  homeworkList.value.push({
    id: Date.now(),
    subject: newHwSubject.value,
    title: newHwTitle.value.trim(),
    dueTime: '今日待完成',
    completed: false,
    justToggled: false
  });
  newHwTitle.value = '';
  showAddHomeworkSheet.value = false;
  showToast({ message: '添加成功', icon: 'success' });
};

// ==========================================
// 屏 2：错题本数据与复习逻辑
// ==========================================
const selectedSubject = ref('全部');
const showAddMistakeSheet = ref(false);

const subjects = ref([
  { name: '全部', count: 12 },
  { name: '数学', count: 5 },
  { name: '英语', count: 4 },
  { name: '物理', count: 3 },
]);

const pendingReviewList = ref([
  {
    id: 101,
    subject: '数学',
    question: '已知二次函数 y = ax² + bx + c 的图像开口向上，且经过点 (-1, 0) 和 (3, 0)，若点 P(m, n) 在其图像上，求 m 的取值范围...',
    hasImage: true,
    reviewCount: 2,
    retentionRate: 58
  },
  {
    id: 102,
    subject: '物理',
    question: '在用光具座探究凸透镜成像规律时，将蜡烛置于 2 倍焦距外，光屏上得到倒立缩小的实像。若在凸透镜前加一块远视眼镜片，光屏应如何移动？',
    hasImage: false,
    reviewCount: 1,
    retentionRate: 42
  }
]);

const handleReview = (item, isMastered) => {
  if (isMastered) {
    showToast({ message: '掌握啦！记忆周期自动顺延', icon: 'passed' });
  } else {
    showToast({ message: '已重置艾宾浩斯复习周期，明天将再次提醒', icon: 'replay' });
  }
  pendingReviewList.value = pendingReviewList.value.filter(i => i.id !== item.id);
};

const previewImage = () => {
  showImagePreview([
    'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&q=80'
  ]);
};

const simulateOcr = () => {
  showToast({ message: 'RapidOCR 识别模拟中...', icon: 'scan' });
  setTimeout(() => {
    showAddMistakeSheet.value = false;
    showToast({ message: '识别成功，已提取题干并录入！', icon: 'success' });
  }, 1000);
};

// PIN 解锁验证
const verifyPin = () => {
  if (inputPin.value === '1234' || inputPin.value === '') {
    showToast({ message: 'PIN 验证通过，已进入管理权限', icon: 'success' });
    showPinSheet.value = false;
    inputPin.value = '';
  } else {
    showToast('PIN 错误，请重试');
  }
};

// 学科标签样式辅助
const getSubjectBadgeClass = (subject) => {
  switch (subject) {
    case '数学': return 'st-icon-badge--primary';
    case '物理': return 'st-icon-badge--info';
    case '英语': return 'st-icon-badge--purple';
    case '化学': return 'st-icon-badge--warning';
    case '语文': return 'st-icon-badge--success';
    default: return 'st-icon-badge--neutral';
  }
};
</script>

<style scoped>
.preview-container {
  min-height: 100vh;
  background-color: var(--st-bg-page);
  padding-bottom: 84px;
}

/* 顶部演示模式控制条 */
.demo-top-bar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 10px 16px;
  border-bottom: 1px solid var(--st-border-bold);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.demo-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--st-primary);
  letter-spacing: 0.5px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--st-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}

.screen-switch-tabs {
  display: flex;
  background-color: var(--st-bg-subtle);
  border-radius: var(--st-radius-md);
  padding: 3px;
  gap: 4px;
}

.switch-tab-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--st-text-secondary);
  border-radius: var(--st-radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.switch-tab-btn.active {
  background-color: #ffffff;
  color: var(--st-text-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

/* 主内容容器 */
.screen-content {
  padding: 14px 16px;
}

/* 顶栏信息 */
.top-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.streak-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-primary);
  background: var(--st-bg-card);
  padding: 4px 12px;
  border-radius: var(--st-radius-full);
  border: 1px solid var(--st-border-bold);
  box-shadow: var(--st-shadow-card);
}

.parent-entry-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--st-bg-card);
  border: 1px solid var(--st-border-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--st-text-secondary);
  box-shadow: var(--st-shadow-card);
  cursor: pointer;
}

/* 顶部 7 日横向胶囊日历条 */
.week-strip-box {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  margin-bottom: 16px;
}

.week-day-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 2px;
  background-color: var(--st-bg-card);
  border: 1px solid var(--st-border);
  border-radius: var(--st-radius-md);
  box-shadow: var(--st-shadow-card);
  cursor: pointer;
  transition: all 0.15s ease;
}

.week-day-pill.active {
  background-color: var(--st-primary);
  border-color: var(--st-primary);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
}

.week-day-pill .day-label {
  font-size: 11px;
  color: var(--st-text-muted);
  margin-bottom: 2px;
}

.week-day-pill.active .day-label {
  color: rgba(255, 255, 255, 0.8);
}

.week-day-pill .day-number {
  font-size: 14px;
  font-weight: 600;
  color: var(--st-text-primary);
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
  background-color: var(--st-success);
}

.week-day-pill.active .day-dot.completed {
  background-color: #ffffff;
}

/* 进度概览卡片 */
.progress-summary-card {
  margin-bottom: 16px;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.progress-stat-text {
  font-size: 12px;
  color: var(--st-text-secondary);
}

.progress-bar-wrapper {
  margin-bottom: 8px;
}

.all-done-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background-color: var(--st-success-light);
  border-radius: var(--st-radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--st-success-dark);
}

/* 作业列表 */
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
  color: var(--st-text-primary);
}

.swipe-hint {
  font-size: 11px;
  color: var(--st-text-muted);
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
  border-radius: var(--st-radius-lg);
  overflow: hidden;
}

.hw-card-face {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  border: 1px solid var(--st-border);
}

.hw-card-face.is-done {
  background-color: #fafbfc;
  border-color: #f1f5f9;
}

/* 圆形打勾勾交互 */
.hw-check-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--st-border-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.hw-check-circle.checked {
  background-color: var(--st-success);
  border-color: var(--st-success);
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
  color: var(--st-text-muted);
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.hw-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--st-text-primary);
  line-height: 1.4;
  word-break: break-all;
}

.hw-title.strike {
  color: var(--st-text-muted);
  text-decoration: line-through;
}

.hw-status-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--st-warning-dark);
  background-color: var(--st-warning-light);
  padding: 2px 8px;
  border-radius: var(--st-radius-full);
  flex-shrink: 0;
}

.hw-status-tag.done {
  color: var(--st-success-dark);
  background-color: var(--st-success-light);
}

/* 左滑呼出抽屉按钮 */
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
  background-color: var(--st-primary);
}

.swipe-action-btn.btn-delete {
  background-color: var(--st-danger);
}

/* 屏 2：错题复习流样式 */
.chips-scroll-bar {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 12px;
  scrollbar-width: none;
}

.chips-scroll-bar::-webkit-scrollbar {
  display: none;
}

.ebbinghaus-banner-card {
  margin-bottom: 14px;
  background-color: var(--st-purple-light);
  border-color: rgba(124, 58, 237, 0.15);
}

.ebbinghaus-desc {
  font-size: 12px;
  color: var(--st-text-secondary);
  line-height: 1.5;
  margin: 0;
}

.mistake-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mistake-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mistake-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subject-and-stage {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-pill {
  font-size: 11px;
  color: var(--st-text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.retention-pill {
  font-size: 11px;
  font-weight: 600;
  color: var(--st-purple);
  background-color: var(--st-purple-light);
  padding: 2px 8px;
  border-radius: var(--st-radius-full);
}

.mistake-question-text {
  font-size: 14px;
  line-height: 1.55;
  color: var(--st-text-primary);
}

.mistake-thumb-box {
  position: relative;
  width: 100%;
  height: 130px;
  border-radius: var(--st-radius-md);
  overflow: hidden;
  cursor: pointer;
}

.mistake-thumb-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.img-preview-tag {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background: rgba(15, 23, 42, 0.7);
  color: #ffffff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--st-radius-full);
  backdrop-filter: blur(4px);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.mistake-actions-row {
  display: flex;
  gap: 12px;
  padding-top: 6px;
  border-top: 1px solid var(--st-border);
}

.review-act-btn {
  flex: 1;
  font-weight: 600;
}

/* 底部悬浮条 */
.floating-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-width: 500px;
  margin: 0 auto;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  z-index: 40;
}

.add-hw-btn {
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}

/* 底部半屏抽屉 (Bottom Sheet) 样式 */
.bottom-sheet-modal {
  max-width: 500px;
  margin: 0 auto;
}

.bottom-sheet-content {
  padding: 16px 20px calc(24px + env(safe-area-inset-bottom));
}

.sheet-grabber {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background-color: var(--st-border-bold);
  margin: 0 auto 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--st-text-regular);
  margin-bottom: 8px;
}

.sheet-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sheet-input-field {
  background-color: var(--st-bg-subtle);
  border-radius: var(--st-radius-md);
  border: 1px solid var(--st-border);
  padding: 10px 12px;
}
</style>
