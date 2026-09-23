<template>
  <van-popup
    :show="modelValue"
    position="bottom"
    round
    :close-on-click-overlay="true"
    :style="{ maxHeight: '90vh' }"
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
        <button class="header-close-btn" @click="close" aria-label="关闭">
          <van-icon name="cross" size="18" />
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

        <!-- 4. 时间元信息栏 -->
        <div class="time-meta-bar">
          <van-icon name="underway-o" class="time-meta-icon" size="14" />
          <span class="time-meta-text">
            {{ formatDateTime(homework.created_at, homework.date) }} 布置
            <span class="dot-separator">·</span>
            {{ homework.is_completed && homework.completed_at ? formatDateTime(homework.completed_at) + ' 打卡' : (homework.date ? homework.date + ' 22:00' : '当日 22:00') }} 截止
          </span>
        </div>

        <!-- 5. 作业内容详情卡片 -->
        <div class="st-card content-detail-card">
          <div class="card-section-title">
            <div class="section-title-left">
              <van-icon name="notes-o" class="section-icon" />
              <span>作业内容</span>
            </div>
            <button class="section-more-btn" @click.stop="showActionMenu = true" aria-label="更多操作">
              <van-icon name="ellipsis" size="16" />
            </button>
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

          <!-- 未完成状态：直接打卡 -->
          <div v-if="!homework.is_completed" class="uncompleted-state-box">
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

const actionItems = [
  { name: '编辑作业', icon: 'edit', color: 'var(--st-text-primary)' },
  { name: '一键转入错题本', icon: 'notes-o', color: 'var(--st-primary)' },
  { name: '删除作业', icon: 'delete-o', color: 'var(--st-danger)' }
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
  border-top-left-radius: var(--st-radius-xl);
  border-top-right-radius: var(--st-radius-xl);
  background-color: var(--st-bg-page);
  overflow: hidden;
}

.hw-detail-container {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  background: var(--st-bg-page);
}

/* 1. 顶栏导航条 */
.hw-detail-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--st-space-4) var(--st-space-5) var(--st-space-3);
  background: var(--st-bg-card);
  border-bottom: 1px solid var(--st-border);
}

.header-back-btn,
.header-close-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--st-radius-full);
  border: none;
  background: var(--st-bg-subtle);
  color: var(--st-text-regular);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}

.header-back-btn:active,
.header-close-btn:active {
  transform: scale(0.92);
  background: var(--st-border);
}

.header-title {
  font-size: var(--st-font-xl);
  font-weight: 600;
  color: var(--st-text-primary);
}

/* 2. 详情内容滚动区 */
.hw-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--st-space-5) var(--st-space-4) var(--st-space-5);
  -webkit-overflow-scrolling: touch;
}

/* 学科与状态行 */
.subject-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--st-space-4);
}

.subject-info {
  display: flex;
  align-items: center;
  gap: var(--st-space-3);
}

.subject-name-text {
  font-size: var(--st-font-xl);
  font-weight: 700;
  color: var(--st-text-primary);
}

.detail-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: var(--st-space-1) var(--st-space-4);
  border-radius: var(--st-radius-full);
  font-size: var(--st-font-xs);
  font-weight: 600;
  background: var(--st-bg-subtle);
  color: var(--st-text-secondary);
}

.detail-status-pill.is-done {
  background: var(--st-success-light);
  color: var(--st-success-dark);
}

/* 主标题 */
.task-headline {
  font-size: var(--st-font-xl);
  font-weight: 800;
  color: var(--st-text-primary);
  line-height: 1.4;
  margin: 0 0 var(--st-space-5);
  letter-spacing: -0.3px;
}

/* 时间元信息 */
.time-meta-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--st-space-5);
  padding: var(--st-space-2) var(--st-space-4);
  background: var(--st-bg-card);
  border-radius: var(--st-radius-full);
  border: 1px solid var(--st-border);
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
}

.time-meta-icon {
  color: var(--st-text-muted);
  flex-shrink: 0;
}

.time-meta-text {
  line-height: 1.4;
  word-break: break-all;
}

.dot-separator {
  margin: 0 var(--st-space-2);
  color: var(--st-border-bold);
}

/* 作业内容卡片 */
.content-detail-card,
.record-card {
  background: var(--st-bg-card);
  border-radius: var(--st-radius-lg);
  padding: var(--st-space-5);
  margin-bottom: var(--st-space-4);
  border: 1px solid var(--st-border);
  box-shadow: var(--st-shadow-card);
}

.card-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
  margin-bottom: var(--st-space-4);
}

.section-title-left {
  display: flex;
  align-items: center;
  gap: var(--st-space-2);
}

.section-icon {
  color: var(--st-primary);
  font-size: var(--st-font-lg);
}

.section-more-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--st-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.section-more-btn:active {
  background: var(--st-bg-subtle);
  color: var(--st-text-secondary);
}

.content-text-box {
  font-size: var(--st-font-md);
  line-height: 1.6;
  color: var(--st-text-regular);
  background: var(--st-bg-subtle);
  padding: var(--st-space-4);
  border-radius: var(--st-radius-md);
  border: 1px solid var(--st-border);
  white-space: pre-wrap;
  word-break: break-all;
}

/* 图片附件预览 */
.image-preview-wrapper {
  margin-top: var(--st-space-4);
}

.image-preview-card {
  position: relative;
  width: 100%;
  max-height: 180px;
  border-radius: var(--st-radius-md);
  overflow: hidden;
  border: 1px solid var(--st-border);
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
  padding: var(--st-space-2) var(--st-space-4);
  background: linear-gradient(transparent, rgba(15, 23, 42, 0.7));
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--st-space-2);
  font-size: var(--st-font-xs);
}

/* 完成记录 */
.uncompleted-state-box {
  text-align: center;
  padding: 4px 0 2px;
}

.primary-checkin-btn {
  width: 100%;
  height: 46px;
  border-radius: var(--st-radius-full);
  background: var(--st-gradient-primary-btn);
  color: #ffffff;
  font-size: var(--st-font-md);
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--st-space-3);
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
  background: var(--st-success);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.completed-info {
  flex: 1;
}

.completed-title {
  font-size: var(--st-font-lg);
  font-weight: 700;
  color: var(--st-text-primary);
  margin: 0 0 2px;
}

.completed-time {
  font-size: var(--st-font-xs);
  color: var(--st-text-secondary);
  margin: 0;
}

.cancel-checkin-btn {
  padding: 6px 14px;
  border-radius: var(--st-radius-full);
  border: 1px solid var(--st-border-bold);
  background: var(--st-bg-card);
  color: var(--st-text-secondary);
  font-size: var(--st-font-xs);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cancel-checkin-btn:active {
  background: var(--st-bg-subtle);
  transform: scale(0.96);
}

</style>
