<template>
  <van-popup
    :show="modelValue"
    position="bottom"
    round
    closeable
    :style="{ maxHeight: '90vh', minHeight: '65vh' }"
    class="hw-detail-popup"
    @update:show="val => emit('update:modelValue', val)"
  >
    <div class="hw-detail-container" v-if="homework">
      <!-- 1. 顶栏导航条 (iOS 规范顶栏) -->
      <div class="hw-detail-header">
        <button class="header-back-btn" @click="close" aria-label="关闭">
          <van-icon name="arrow-left" size="18" />
        </button>
        <span class="header-title">作业详情</span>
        <button class="header-more-btn" @click="showActionMenu = true" aria-label="更多操作">
          <van-icon name="ellipsis" size="20" />
        </button>
      </div>

      <div class="hw-detail-body st-scroll-y">
        <!-- 2. 学科与状态行 -->
        <div class="subject-status-row">
          <div class="subject-info">
            <SubjectBadge :name="homework.subject_name" size="md" />
            <span class="subject-name-text">{{ homework.subject_name }}</span>
          </div>
          <div
            class="detail-status-pill"
            :class="{ 'is-done': homework.is_completed }"
          >
            <van-icon v-if="homework.is_completed" name="success" size="12" />
            <span>{{ homework.is_completed ? '已完成' : '未完成' }}</span>
          </div>
        </div>

        <!-- 3. 大号主任务标题 -->
        <h2 class="task-headline">{{ homework.content }}</h2>

        <!-- 4. 时间元信息栏 (布置时间 & 截止/完成时间) -->
        <div class="time-meta-grid">
          <div class="time-meta-item">
            <van-icon name="calendar-o" class="meta-icon" />
            <span class="meta-label">布置时间</span>
            <span class="meta-val">{{ formatDateTime(homework.created_at, homework.date) }}</span>
          </div>
          <div class="time-meta-item">
            <van-icon name="clock-o" class="meta-icon" />
            <span class="meta-label">{{ homework.is_completed ? '打卡时间' : '建议截止' }}</span>
            <span class="meta-val">
              {{ homework.is_completed && homework.completed_at ? formatDateTime(homework.completed_at) : (homework.date ? `${homework.date} 22:00` : '当日 22:00') }}
            </span>
          </div>
        </div>

        <!-- 5. 作业内容详情卡片 -->
        <div class="st-card content-detail-card">
          <div class="card-section-title">
            <van-icon name="notes-o" class="section-icon" />
            <span>作业内容</span>
          </div>
          <div class="content-text-box">
            {{ homework.content }}
          </div>

          <!-- 配图附件预览 (若有拍照上传/OCR底图) -->
          <div class="image-preview-wrapper" v-if="homework.source_image_path">
            <div class="image-preview-card" @click="previewImage(getImageUrl(homework.source_image_path))">
              <img :src="getImageUrl(homework.source_image_path)" alt="作业题目配图" class="preview-img" />
              <div class="image-zoom-overlay">
                <van-icon name="search" size="18" />
                <span>点击查看原图</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 6. 完成记录卡片 -->
        <div class="st-card record-card">
          <div class="card-section-title">
            <van-icon name="records-o" class="section-icon" />
            <span>完成记录</span>
          </div>

          <!-- 未完成状态：空状态 + 大号打卡完成主按钮 -->
          <div v-if="!homework.is_completed" class="uncompleted-state-box">
            <div class="empty-clipboard-icon">
              <svg viewBox="0 0 48 48" fill="none" class="empty-svg">
                <rect x="10" y="8" width="28" height="34" rx="4" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2" />
                <path d="M18 8V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2" stroke="#94a3b8" stroke-width="2" />
                <line x1="16" y1="18" x2="32" y2="18" stroke="#e2e8f0" stroke-width="2" stroke-linecap="round" />
                <line x1="16" y1="26" x2="28" y2="26" stroke="#e2e8f0" stroke-width="2" stroke-linecap="round" />
              </svg>
            </div>
            <p class="empty-record-text">暂无完成记录</p>

            <button class="primary-checkin-btn" @click="handleToggle">
              <van-icon name="passed" size="18" />
              <span>打卡完成</span>
            </button>
          </div>

          <!-- 已完成状态：打卡成果微展 + 撤销按钮 -->
          <div v-else class="completed-state-box">
            <div class="completed-success-badge">
              <van-icon name="success" size="18" color="#ffffff" />
            </div>
            <div class="completed-info">
              <p class="completed-title">已打卡完成</p>
              <p class="completed-time">
                {{ homework.completed_at ? `记录于 ${formatDateTime(homework.completed_at)}` : '今日已打卡' }}
              </p>
            </div>
            <button class="cancel-checkin-btn" @click="handleToggle">
              撤销打卡
            </button>
          </div>
        </div>

        <!-- 7. 提醒设置卡片 -->
        <div class="st-card reminder-card">
          <div class="reminder-row">
            <div class="reminder-left">
              <van-icon name="bell" class="reminder-icon" />
              <span class="reminder-title">作业提醒</span>
            </div>
            <div class="reminder-right">
              <span class="reminder-status-text">每晚 20:30</span>
              <van-switch v-model="reminderEnabled" size="20px" active-color="#2563eb" />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部更多操作 ActionSheet (编辑/转错题/删除) -->
      <van-action-sheet
        v-model:show="showActionMenu"
        :actions="actionItems"
        cancel-text="取消"
        close-on-click-action
        @select="onActionSelect"
      />
    </div>
  </van-popup>
</template>

<script setup>
import { ref, computed } from 'vue';
import { showImagePreview, showToast, showConfirmDialog } from 'vant';
import SubjectBadge from './SubjectBadge.vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  homework: {
    type: Object,
    default: null
  }
});

const emit = defineEmits([
  'update:modelValue',
  'toggle-complete',
  'edit',
  'to-mistake',
  'delete'
]);

const showActionMenu = ref(false);
const reminderEnabled = ref(true);

const actionItems = [
  { name: '编辑作业', icon: 'edit', color: '#0f172a' },
  { name: '一键转入错题本', icon: 'notes-o', color: '#2563eb' },
  { name: '删除作业', icon: 'delete-o', color: '#ef4444' }
];

const close = () => {
  emit('update:modelValue', false);
};

const handleToggle = () => {
  if (props.homework) {
    emit('toggle-complete', props.homework);
  }
};

const onActionSelect = (action) => {
  if (!props.homework) return;
  if (action.name === '编辑作业') {
    emit('edit', props.homework);
    close();
  } else if (action.name === '一键转入错题本') {
    emit('to-mistake', props.homework);
  } else if (action.name === '删除作业') {
    emit('delete', props.homework);
    close();
  }
};

const getImageUrl = (path) => {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  if (path.startsWith('/')) return path;
  return `/${path}`;
};

const previewImage = (url) => {
  if (url) {
    showImagePreview({
      images: [url],
      closeable: true
    });
  }
};

const formatDateTime = (dtStr, fallbackDate) => {
  if (!dtStr && fallbackDate) return `${fallbackDate} 16:00`;
  if (!dtStr) return '--:--';
  try {
    const d = new Date(dtStr);
    if (isNaN(d.getTime())) return dtStr;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  } catch (e) {
    return dtStr;
  }
};
</script>

<style scoped>
:deep(.van-popup.hw-detail-popup) {
  border-top-left-radius: 24px;
  border-top-right-radius: 24px;
  background-color: #f8fafc;
  overflow: hidden;
}

.hw-detail-container {
  display: flex;
  flex-direction: column;
  height: 85vh;
  background: #f8fafc;
}

/* 1. 顶栏导航条 */
.hw-detail-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  background: #ffffff;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.06);
}

.header-back-btn,
.header-more-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #f1f5f9;
  color: #334155;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}

.header-back-btn:active,
.header-more-btn:active {
  transform: scale(0.92);
  background: #e2e8f0;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.3px;
}

/* 2. 详情内容滚动区 */
.hw-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px 36px;
  -webkit-overflow-scrolling: touch;
}

/* 学科与状态行 */
.subject-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.subject-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subject-name-text {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.detail-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  background: #f1f5f9;
  color: #64748b;
}

.detail-status-pill.is-done {
  background: #ecfdf5;
  color: #10b981;
}

/* 主标题 */
.task-headline {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.4;
  margin: 0 0 16px 0;
  letter-spacing: -0.3px;
}

/* 时间元信息 */
.time-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 18px;
}

.time-meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.meta-icon {
  color: #64748b;
  font-size: 14px;
}

.meta-label {
  font-size: 12px;
  color: #94a3b8;
}

.meta-val {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-left: auto;
}

/* 作业内容卡片 */
.content-detail-card,
.record-card,
.reminder-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

.card-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 12px;
}

.section-icon {
  color: #2563eb;
  font-size: 16px;
}

.content-text-box {
  font-size: 14px;
  line-height: 1.6;
  color: #334155;
  background: #f8fafc;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #edf2f7;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 图片附件预览 */
.image-preview-wrapper {
  margin-top: 12px;
}

.image-preview-card {
  position: relative;
  width: 100%;
  max-height: 180px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  cursor: pointer;
}

.preview-img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  display: block;
}

.image-zoom-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 12px;
  background: linear-gradient(transparent, rgba(15, 23, 42, 0.7));
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
}

/* 完成记录 */
.uncompleted-state-box {
  text-align: center;
  padding: 16px 0 6px;
}

.empty-clipboard-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.empty-svg {
  width: 48px;
  height: 48px;
}

.empty-record-text {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 16px;
}

.primary-checkin-btn {
  width: 100%;
  height: 46px;
  border-radius: 9999px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.3);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.primary-checkin-btn:active {
  transform: scale(0.98);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
}

.completed-state-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px;
}

.completed-success-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.completed-info {
  flex: 1;
}

.completed-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 2px;
}

.completed-time {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.cancel-checkin-btn {
  padding: 6px 14px;
  border-radius: 9999px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cancel-checkin-btn:active {
  background: #f1f5f9;
  transform: scale(0.96);
}

/* 提醒设置 */
.reminder-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reminder-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reminder-icon {
  font-size: 16px;
  color: #f59e0b;
}

.reminder-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.reminder-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.reminder-status-text {
  font-size: 13px;
  color: #64748b;
}
</style>
